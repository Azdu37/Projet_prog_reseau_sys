# network_bridge.py
# V3 — Handshake + échange atomique Python ↔ SHM (sans thread listener)
#
# Nouveauté V3 :
#   is_ready() : retourne True quand la SHM indique both_ready==1,
#                c'est-à-dire quand le processus C a terminé son handshake
#                avec tous les pairs distants.
#   exchange_state() reste inchangé et gère l'état de jeu.

import ctypes
import os
import time

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
libc.mmap.argtypes      = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                            ctypes.c_int, ctypes.c_int, ctypes.c_long]
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

# ── Structures Ctypes (DOIT correspondre EXACTEMENT à protocol.h) ────────────
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
    """
    DOIT correspondre exactement à GameState dans protocol.h :
      uint32  magic
      uint16  version
      uint8   unit_count
      uint8   my_peer_id
      uint32  tick
      uint8   both_ready
      uint8   python_ready
      uint8   _pad[2]
      UnitState units[256]
    """
    _fields_ = [
        ("magic",       ctypes.c_uint32),
        ("version",     ctypes.c_uint16),
        ("unit_count",  ctypes.c_uint8),
        ("my_peer_id",  ctypes.c_uint8),
        ("tick",        ctypes.c_uint32),
        ("both_ready",  ctypes.c_uint8),
        ("python_ready", ctypes.c_uint8),
        ("_pad",        ctypes.c_uint8 * 2),
        ("units",       UnitState * MAX_UNITS),
    ]

# ── CLASSE BRIDGE ─────────────────────────────────────────────────────────────
class POSIXBridge:
    def __init__(self, my_peer_id: int):
        self.my_peer_id = my_peer_id
        self._fd = -1
        self._sem_w = None
        self._sem_r = None
        self._map_addr = None
        self._state = None

    def connecter(self, tentatives=30, delai=0.2):
        fd = -1
        shm_name = os.getenv("SHM_NAME", SHM_NAME)
        sem_w = os.getenv("SEM_W", SEM_WRITE_NAME)
        sem_r = os.getenv("SEM_R", SEM_READ_NAME)

        for i in range(tentatives):
            fd = libc.shm_open(shm_name.encode(), os.O_RDWR, 0)
            if fd >= 0:
                break
            err = ctypes.get_errno()
            if i < tentatives - 1:
                print(f"[bridge] Attente du processus C (shm_open {shm_name})... {i+1}/{tentatives}")
                time.sleep(delai)
            else:
                raise OSError(err, f"shm_open({shm_name}) échoué. Le processus ./c_net tourne-t-il ?")

        size = ctypes.sizeof(GameStateC)
        map_addr = libc.mmap(None, size, _PROT_READ | _PROT_WRITE, _MAP_SHARED, fd, 0)
        self._sem_w = libc.sem_open(sem_w.encode(), 0, 0, 0)
        self._sem_r = libc.sem_open(sem_r.encode(), 0, 0, 0)

        self._fd = fd
        self._map_addr = map_addr
        self._state = ctypes.cast(map_addr, ctypes.POINTER(GameStateC)).contents
        print(f"[bridge] Connecté à la SHM (peer_id={self.my_peer_id})")

    def ecrire(self, snapshot):
        if not self._state:
            return
        libc.sem_wait(self._sem_w)
        try:
            ctypes.memmove(ctypes.byref(self._state), ctypes.byref(snapshot),
                           ctypes.sizeof(GameStateC))
        finally:
            libc.sem_post(self._sem_w)

    def lire(self):
        if not self._state:
            raise RuntimeError("SHM non connectée")
        out = GameStateC()
        libc.sem_wait(self._sem_r)
        try:
            ctypes.memmove(ctypes.byref(out), ctypes.byref(self._state),
                           ctypes.sizeof(GameStateC))
        finally:
            libc.sem_post(self._sem_r)
        return out

    def fermer(self):
        if self._map_addr:
            libc.munmap(self._map_addr, ctypes.sizeof(GameStateC))
        if self._sem_w:
            libc.sem_close(self._sem_w)
        if self._sem_r:
            libc.sem_close(self._sem_r)
        if self._fd >= 0:
            libc.close(self._fd)


# ── INSTANCE GLOBALE ──────────────────────────────────────────────────────────
_bridge = None
_experiment_enabled = os.getenv("NET_EXPERIMENT", "0") == "1"
_experiment_delay = max(0.0, float(os.getenv("NET_EXPERIMENT_STEP_DELAY", "0") or "0"))


def _exp_log(message: str) -> None:
    if _experiment_enabled:
        print(f"[NET-EXP][bridge] {message}", flush=True)


def _exp_pause(reason: str) -> None:
    if _experiment_enabled:
        _exp_log(f"Pause ignorée : {reason} (delay configuré={_experiment_delay:.2f}s)")


def init(player_id: int) -> None:
    """Appelé par main.py pour s'accrocher à la mémoire IPC POSIX du ./c_net."""
    global _bridge
    _bridge = POSIXBridge(my_peer_id=player_id)
    try:
        _bridge.connecter()
    except Exception as e:
        print(f"[bridge] Erreur de connexion IPC : {e}")
        _bridge = None


def is_ready() -> bool:
    """
    Retourne True quand le processus C a terminé son handshake avec tous
    les pairs distants (both_ready == 1 dans la SHM).

    À appeler en boucle depuis engine.py avant de lancer game_loop().
    """
    if not _bridge:
        return False
    try:
        c_state = _bridge.lire()
        return bool(c_state.both_ready)
    except Exception:
        return False


def set_python_ready(is_ready: bool = True) -> bool:
    """Annonce au processus C que le jeu Python local est prêt."""
    if not _bridge:
        return False
    try:
        c_state = _bridge.lire()
        c_state.python_ready = 1 if is_ready else 0
        _bridge.ecrire(c_state)
        return True
    except Exception:
        return False


def request_ownership(unit) -> bool:
    """Marque une unité pour demander sa propriété au prochain exchange_state."""
    if not _bridge:
        return False
    unit.pending_ownership_request = True
    _exp_log(f"Demande de propriété préparée pour unité {unit.unit_id}")
    return True


def _spawn_remote_projectile_visual(engine, shooter, event_seq, target_id):
    if event_seq == 0 or shooter.is_local or shooter.type not in ('C', 'S'):
        return
    if getattr(shooter, '_last_remote_projectile_seq', 0) == event_seq:
        return
    target = engine.find_unit(target_id)
    if target and target.team != shooter.team:
        engine.game_map.spawn_visual_projectile(shooter, target)
    shooter._last_remote_projectile_seq = event_seq


def exchange_state(engine) -> None:
    """
    Échange atomique avec la SHM — appelé chaque tick du game loop.

    1. Lit la SHM (mises à jour réseau écrites par le processus C)
    2. Applique les updates distantes aux unités Python
    3. Écrit l'état Python dans la SHM pour que C l'envoie en UDP
    """
    if not _bridge:
        return

    my_peer = _bridge.my_peer_id

    try:
        c_state = _bridge.lire()
    except Exception:
        return

    units = list(engine.all_units())[:MAX_UNITS]

    # ── PHASE 1 : Lire les mises à jour du réseau depuis la SHM ──────────
    for unit in units:
        uid = unit.unit_id
        if uid >= MAX_UNITS:
            continue

        slot = c_state.units[uid]

        if slot.hp_max == 0:
            continue

        old_owner = unit.owner_id
        unit.owner_id = slot.owner_peer
        unit.is_local = (unit.owner_id == my_peer)
        projectile_seq = int(slot._pad[0])
        projectile_target_id = int(slot._pad[1])

        if unit.is_local:
            unit._network_synced = True
            if old_owner != my_peer:
                print(f"[bridge] Propriété ACQUISE pour unité {uid}")
                _exp_log(f"Point 2/3 : unité {uid} reçue avec état x={slot.x:.1f} y={slot.y:.1f} hp={slot.hp}")
                unit.position = (slot.x, slot.y)
                unit.current_hp = slot.hp
                unit.is_alive = (slot.alive != 0)
                if not unit.is_alive:
                    unit.state = "dead"
                _exp_pause(f"après acquisition de propriété unité {uid}")

            if slot.hp < unit.current_hp and slot.hp >= 0:
                unit.current_hp = slot.hp
                unit.get_hit = 0.2
                if unit.current_hp <= 0:
                    unit.current_hp = 0
                    unit.is_alive = False
                    unit.state = "dead"
                    unit.target = None
        else:
            if old_owner == my_peer:
                print(f"[bridge] Propriété PERDUE pour unité {uid}")
                _exp_log(f"Unité {uid} redevient distante, suivi en lecture seule")

            unit.position = (slot.x, slot.y)

            if slot.hp < unit.current_hp and slot.hp > 0:
                unit.current_hp = slot.hp
                unit.get_hit = 0.2

            if (slot.alive == 0 or slot.hp <= 0) and slot.hp_max > 0 and unit.current_hp > 0:
                if getattr(unit, '_network_synced', False):
                    unit.current_hp = 0
                    unit.is_alive = False
                    unit.state = "dead"
                    unit.target = None

            if slot.hp > 0:
                unit._network_synced = True

        _spawn_remote_projectile_visual(engine, unit, projectile_seq, projectile_target_id)

    # ── PHASE 2 : Écrire l'état Python dans la SHM pour le C ──────────────
    c_state.magic      = PROTOCOL_MAGIC
    c_state.version    = PROTOCOL_VERSION
    c_state.my_peer_id = my_peer
    c_state.unit_count = len(units)
    # both_ready est piloté uniquement par le processus C.
    # python_ready reflète la disponibilité du jeu Python local.
    c_state.python_ready = 1

    for unit in units:
        uid = unit.unit_id
        if uid >= MAX_UNITS:
            continue

        slot = c_state.units[uid]

        if getattr(unit, 'pending_ownership_request', False):
            unit.pending_ownership_request = False
            if not unit.is_local:
                slot.id    = uid
                slot.dirty = 2
                _exp_log(f"Point 1 : unité {uid} marquée dirty=2 pour émission de MSG_OWN_REQUEST")
                continue

        owner = unit.owner_id

        if unit.is_local:
            slot.id         = uid
            slot.team       = 0 if unit.team == 'R' else 1
            slot.owner_peer = owner
            slot.hp_max     = int(unit.max_hp)
            slot.alive      = 1 if unit.is_alive else 0
            slot.x          = float(unit.position[0])
            slot.y          = float(unit.position[1])
            slot.hp         = int(unit.current_hp)
            slot._pad[0]    = int(getattr(unit, '_network_projectile_seq', 0)) & 0xFF
            slot._pad[1]    = int(getattr(unit, '_network_projectile_target_id', 255)) & 0xFF
            slot._pad[2]    = 0
            slot.dirty      = 1
            _exp_log(
                f"Point 5 : publication locale unité {uid} owner={owner} pos=({slot.x:.1f},{slot.y:.1f}) hp={slot.hp}"
            )
        else:
            if slot.hp_max == 0:
                slot.id         = uid
                slot.team       = 0 if unit.team == 'R' else 1
                slot.owner_peer = owner
                slot.hp_max     = int(unit.max_hp)
                slot.hp         = int(unit.current_hp)
                slot.alive      = 1 if unit.is_alive else 0
                slot.x          = float(unit.position[0])
                slot.y          = float(unit.position[1])
                slot.dirty      = 0

            python_hp = int(unit.current_hp)
            if python_hp < slot.hp:
                slot.hp    = python_hp
                slot.alive = 1 if python_hp > 0 else 0
                slot.dirty = 1
            else:
                if slot.dirty != 2:
                    slot.dirty = 0

    try:
        _bridge.ecrire(c_state)
    except Exception:
        pass


def shutdown() -> None:
    """Ferme la connexion SHM."""
    global _bridge
    if _bridge:
        try:
            set_python_ready(False)
        except Exception:
            pass
        _bridge.fermer()
        _bridge = None
