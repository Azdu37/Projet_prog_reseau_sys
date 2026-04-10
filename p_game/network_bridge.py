# network_bridge.py
# Modifié pour utiliser la mémoire partagée POSIX (ctypes) en synchro parfaite avec le C.

import ctypes
import os
import threading
import time
from typing import Callable

# ── Constantes correspondantes au protocole C ────────────────────────────────
PROTOCOL_MAGIC   = 0xBABA1234
PROTOCOL_VERSION = 1
MAX_UNITS        = 256
SHM_NAME         = "/battle_state"
SEM_WRITE_NAME   = "/battle_sem_w"
SEM_READ_NAME    = "/battle_sem_r"

# ── Définition LibC (POSIX IPC) ──────────────────────────────────────────────
libc = ctypes.CDLL(None, use_errno=True)

libc.shm_open.argtypes  = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
libc.shm_open.restype   = ctypes.c_int
libc.mmap.argtypes      = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
libc.mmap.restype       = ctypes.c_void_p
libc.munmap.argtypes    = [ctypes.c_void_p, ctypes.c_size_t]
libc.munmap.restype     = ctypes.c_int
libc.close.argtypes     = [ctypes.c_int]
libc.close.restype      = ctypes.c_int
libc.sem_open.argtypes  = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
libc.sem_open.restype   = ctypes.c_void_p
libc.sem_close.argtypes = [ctypes.c_void_p]
libc.sem_close.restype  = ctypes.c_int
libc.sem_wait.argtypes  = [ctypes.c_void_p]
libc.sem_wait.restype   = ctypes.c_int
libc.sem_post.argtypes  = [ctypes.c_void_p]
libc.sem_post.restype   = ctypes.c_int

_PROT_READ  = 0x1
_PROT_WRITE = 0x2
_MAP_SHARED = 0x01
_SEM_FAILED = ctypes.c_void_p(-1).value
_MAP_FAILED = ctypes.c_void_p(-1).value

# ── Structures Ctypes ────────────────────────────────────────────────────────
class UnitState(ctypes.Structure):
    _fields_ = [
        ("id",         ctypes.c_uint8),
        ("team",       ctypes.c_uint8),
        ("owner_peer", ctypes.c_uint8),
        ("alive",      ctypes.c_uint8),
        ("dirty",      ctypes.c_uint8),
        ("_pad",       ctypes.c_uint8 * 3),
        ("x",          ctypes.c_float),
        ("y",          ctypes.c_float),
        ("hp",         ctypes.c_uint16),
        ("hp_max",     ctypes.c_uint16),
    ]

class GameStateC(ctypes.Structure):
    _fields_ = [
        ("magic",      ctypes.c_uint32),
        ("version",    ctypes.c_uint16),
        ("unit_count", ctypes.c_uint8),
        ("my_peer_id", ctypes.c_uint8),
        ("tick",       ctypes.c_uint32),
        ("_pad",       ctypes.c_uint8 * 4),
        ("units",      UnitState * MAX_UNITS),
    ]

# ── CLASSE BRIDGE ─────────────────────────────────────────────────────────────
class POSIXBridge:
    def __init__(self, my_peer_id: int):
        self.my_peer_id = my_peer_id
        self._fd = -1
        self._sem_w = None
        self._sem_r = None
        self._map_addr = None
        self._state: GameStateC | None = None

    def connecter(self, tentatives=30, delai=0.2):
        fd = -1
        for i in range(tentatives):
            fd = libc.shm_open(SHM_NAME.encode(), os.O_RDWR, 0)
            if fd >= 0: break
            err = ctypes.get_errno()
            if i < tentatives - 1:
                print(f"[bridge] Attente du processus C (shm_open)... {i+1}/{tentatives}")
                time.sleep(delai)
            else:
                raise OSError(err, f"shm_open({SHM_NAME}) échoué. Le C ./c_net tourne-t-il ?")

        size = ctypes.sizeof(GameStateC)
        map_addr = libc.mmap(None, size, _PROT_READ | _PROT_WRITE, _MAP_SHARED, fd, 0)
        self._sem_w = libc.sem_open(SEM_WRITE_NAME.encode(), 0, 0, 0)
        self._sem_r = libc.sem_open(SEM_READ_NAME.encode(), 0, 0, 0)
        
        self._fd = fd
        self._map_addr = map_addr
        self._state = ctypes.cast(map_addr, ctypes.POINTER(GameStateC)).contents
        print(f"[bridge] Connecté avec succès à la mémoire partagée (peer_id={self.my_peer_id})")

    def ecrire(self, snapshot: GameStateC):
        if not self._state: return
        libc.sem_wait(self._sem_w)
        try:
            ctypes.memmove(ctypes.byref(self._state), ctypes.byref(snapshot), ctypes.sizeof(GameStateC))
        finally:
            libc.sem_post(self._sem_w)

    def lire(self) -> GameStateC:
        if not self._state: raise RuntimeError()
        out = GameStateC()
        libc.sem_wait(self._sem_r)
        try:
            ctypes.memmove(ctypes.byref(out), ctypes.byref(self._state), ctypes.sizeof(GameStateC))
        finally:
            libc.sem_post(self._sem_r)
        return out

    def fermer(self):
        if self._map_addr: libc.munmap(self._map_addr, ctypes.sizeof(GameStateC))
        if self._sem_w: libc.sem_close(self._sem_w)
        if self._sem_r: libc.sem_close(self._sem_r)
        if self._fd >= 0: libc.close(self._fd)


# ── INSTANCE GLOBALE ET API CONFORTE ──────────────────────────────────────────

_bridge: POSIXBridge | None = None
_running: bool = False

def init(player_id: int, **kwargs) -> None:
    """Appelé par main.py pour s'accrocher à la mémoire IPC POSIX du ./c_net."""
    global _bridge
    _bridge = POSIXBridge(my_peer_id=player_id)
    try:
        _bridge.connecter()
    except Exception as e:
        print(f"Erreur de connexion IPC : {e}")
        _bridge = None

def push_local_update(game_state) -> None:
    """Convertit l'état Python en struct C et l'écrit dans la SHM."""
    if not _bridge: return

    try:
        c_state = _bridge.lire()
    except Exception:
        c_state = GameStateC()

    c_state.magic = PROTOCOL_MAGIC
    c_state.version = PROTOCOL_VERSION
    c_state.my_peer_id = _bridge.my_peer_id
    
    units = list(game_state.all_units())[:MAX_UNITS]
    c_state.unit_count = len(units)

    for i, u in enumerate(units):
        uid = int(u.unit_id if hasattr(u, 'unit_id') else i)
        owner = int(u.owner_id if hasattr(u, 'owner_id') else _bridge.my_peer_id)
        
        # UNIQUEMENT si on est propriétaire, on écrase les données dans la RAM !
        # Ou si l'unité est encore vide (init).
        if owner == _bridge.my_peer_id or c_state.units[i].hp_max == 0:
            c_state.units[i].id = uid
            c_state.units[i].team = owner
            c_state.units[i].owner_peer = owner
            c_state.units[i].x = float(u.position[0])
            c_state.units[i].y = float(u.position[1])
            c_state.units[i].hp = int(u.current_hp)
            c_state.units[i].hp_max = int(getattr(u, 'max_hp', 100))
            c_state.units[i].alive = 1 if c_state.units[i].hp > 0 else 0
            c_state.units[i].dirty = 1
        else:
            # L'unité appartient au réseau, on la relit de la SHM, on ne la modifie pas !
            # Et son dirty restera à 0 pour ne pas la re-broadcaster
            c_state.units[i].dirty = 0

    _bridge.ecrire(c_state)


def start_listener(apply_callback: Callable) -> None:
    """Lit très régulièrement la mémoire C pour informer le jeu Python des nouveautés UDP."""
    global _running
    if not _bridge: return
    _running = True

    def _loop():
        while _running:
            try:
                recv = _bridge.lire()
                
                # Reformate en dictionnaire pour apply_remote_update() du jeu originel
                remote_units = []
                for i in range(recv.unit_count):
                    u = recv.units[i]
                    if u.owner_peer != _bridge.my_peer_id:
                        remote_units.append({
                            "unit_id": u.id,
                            "owner_id": u.owner_peer,
                            "x": u.x,
                            "y": u.y,
                            "hp": u.hp
                        })
                
                if remote_units:
                    msg = {
                        "msg_type": 1,
                        "sender_id": -1,
                        "timestamp_ms": int(time.time()*1000),
                        "units": remote_units
                    }
                    apply_callback(msg)

                time.sleep(0.016) # ~60 Hz
            except Exception as e:
                # La SHM a été fermée / c_net stoppé ?
                break

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def shutdown() -> None:
    global _running
    _running = False
    if _bridge:
        _bridge.fermer()
