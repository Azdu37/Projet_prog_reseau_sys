import ctypes
import os
import time

PROTOCOL_MAGIC   = 0xBABA1234
PROTOCOL_VERSION = 1
MAX_UNITS        = 256
SHM_NAME         = "/battle_state"
SEM_WRITE_NAME   = "/battle_sem_w"
SEM_READ_NAME    = "/battle_sem_r"

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

# Structure mise à jour avec pending_request_from
class UnitState(ctypes.Structure):
    _fields_ = [
        ("id",         ctypes.c_uint8),
        ("team",       ctypes.c_uint8),
        ("owner_peer", ctypes.c_uint8),
        ("alive",      ctypes.c_uint8),
        ("dirty",      ctypes.c_uint8),
        ("pending_request_from", ctypes.c_uint8),
        ("_pad",       ctypes.c_uint8 * 2),
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
        for i in range(tentatives):
            fd = libc.shm_open(SHM_NAME.encode(), os.O_RDWR, 0)
            if fd >= 0: break
            err = ctypes.get_errno()
            if i < tentatives - 1:
                time.sleep(delai)
            else:
                raise OSError(err, f"shm_open({SHM_NAME}) échoué.")

        size = ctypes.sizeof(GameStateC)
        map_addr = libc.mmap(None, size, _PROT_READ | _PROT_WRITE, _MAP_SHARED, fd, 0)
        self._sem_w = libc.sem_open(SEM_WRITE_NAME.encode(), 0, 0, 0)
        self._sem_r = libc.sem_open(SEM_READ_NAME.encode(), 0, 0, 0)
        self._fd = fd
        self._map_addr = map_addr
        self._state = ctypes.cast(map_addr, ctypes.POINTER(GameStateC)).contents

    def ecrire(self, snapshot):
        if not self._state: return
        libc.sem_wait(self._sem_w)
        try:
            ctypes.memmove(ctypes.byref(self._state), ctypes.byref(snapshot), ctypes.sizeof(GameStateC))
        finally:
            libc.sem_post(self._sem_w)

    def lire(self):
        if not self._state: raise RuntimeError("SHM non connectée")
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


_bridge = None

def init(player_id: int) -> None:
    global _bridge
    _bridge = POSIXBridge(my_peer_id=player_id)
    try:
        _bridge.connecter()
    except Exception as e:
        print(f"[bridge] Erreur: {e}")
        _bridge = None


def exchange_state(engine) -> None:
    if not _bridge: return
    my_peer = _bridge.my_peer_id

    try: c_state = _bridge.lire()
    except Exception: return

    units = list(engine.all_units())[:MAX_UNITS]
    
    # ── PHASE 1 : LECTURE DE LA SHM ──
    for unit in units:
        uid = unit.unit_id
        if uid >= MAX_UNITS: continue
        slot = c_state.units[uid]
        if slot.hp_max == 0: continue
        
        # Init de sécurité
        if getattr(unit, 'network_owner', None) is None:
            unit.network_owner = 0 if unit.team == 'R' else 1

        if unit.network_owner == my_peer:
            # L'adversaire demande la propriété ?
            req = slot.pending_request_from
            if req != 255 and req != my_peer:
                # On accorde si on n'est pas mort ou en pleine attaque
                if unit.is_alive and unit.state != "attacking":
                    unit.network_owner = req
                    slot.owner_peer = req
                    slot.pending_request_from = 255
                    slot.dirty = 1
                    unit.is_local = False
                    
            # Accepter les dégâts distants
            if slot.hp > 0 and slot.hp < unit.current_hp:
                unit.current_hp = slot.hp
                unit.get_hit = 0.2
                if unit.current_hp <= 0:
                    unit.current_hp, unit.is_alive, unit.state = 0, False, "dead"
        else:
            # UNITÉ DISTANTE : On a récupéré la propriété !
            if slot.owner_peer == my_peer:
                unit.network_owner = my_peer
                unit.is_local = True
                unit.pending_request = False
                
            # Maj position et HP
            if slot.x != 0.0 or slot.y != 0.0:
                unit.position = (slot.x, slot.y)
            if slot.hp > 0 and slot.hp < unit.current_hp:
                unit.current_hp = slot.hp
                unit.get_hit = 0.2
            if slot.alive == 0 and slot.hp_max > 0 and slot.hp == 0:
                unit.current_hp, unit.is_alive, unit.state = 0, False, "dead"

    # ── PHASE 2 : ÉCRITURE DANS LA SHM ──
    c_state.magic = PROTOCOL_MAGIC
    c_state.version = PROTOCOL_VERSION
    c_state.my_peer_id = my_peer
    c_state.unit_count = len(units)

    for unit in units:
        uid = unit.unit_id
        if uid >= MAX_UNITS: continue
        slot = c_state.units[uid]

        slot.id = uid
        slot.team = 0 if unit.team == 'R' else 1
        slot.hp_max = int(unit.max_hp)
        slot.alive = 1 if unit.is_alive else 0
        
        if unit.network_owner == my_peer:
            slot.owner_peer = my_peer
            slot.pending_request_from = 255
            # Marquer dirty si position ou HP change
            if slot.hp != int(unit.current_hp) or slot.x != float(unit.position[0]) or slot.y != float(unit.position[1]):
                slot.x, slot.y, slot.hp = float(unit.position[0]), float(unit.position[1]), int(unit.current_hp)
                slot.dirty = 1
        else:
            # Demande de propriété envoyée au C
            if getattr(unit, 'pending_request', False):
                slot.pending_request_from = my_peer
                slot.dirty = 1
                unit.pending_request = False 

    try: _bridge.ecrire(c_state)
    except Exception: pass

def shutdown() -> None:
    if _bridge: _bridge.fermer()