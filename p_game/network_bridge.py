# network_bridge.py
# V1 — Bridge Python ↔ SHM en best-effort (sans thread listener)
#
# Principe :
#   exchange_state() est appelé à chaque tick du game loop.
#   1. Lit la SHM (contient les mises à jour réseau écrites par C)
#   2. Applique les updates distantes aux unités Python
#   3. Écrit l'état local Python dans la SHM pour que C l'envoie
#
# Objectif V1 : partager l'état au mieux, sans garantie forte de cohérence.

import ctypes
import os
import time

# ── Constantes correspondantes au protocole C ────────────────────────────────
PROTOCOL_MAGIC   = 0xBABA1234
PROTOCOL_VERSION = 1
MAX_UNITS        = 512
SHM_NAME         = "/battle_state"
SEM_WRITE_NAME   = "/battle_sem_w"
SEM_READ_NAME    = "/battle_sem_r"

# ── Définition LibC (POSIX IPC) ──────────────────────────────────────────────
POSIX_AVAILABLE = os.name != "nt"
libc = ctypes.CDLL(None, use_errno=True) if POSIX_AVAILABLE else None

if libc is not None:
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

# ── Structures Ctypes (DOIT correspondre EXACTEMENT à shared/protocol.h) ────
class UnitState(ctypes.Structure):
    _fields_ = [
        ("id",         ctypes.c_uint16),
        ("team",       ctypes.c_uint8),
        ("owner_peer", ctypes.c_uint8),
        ("alive",      ctypes.c_uint8),
        ("dirty",      ctypes.c_uint8),
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
        ("unit_count", ctypes.c_uint16),
        ("my_peer_id", ctypes.c_uint8),
        ("_pad0",      ctypes.c_uint8 * 3),
        ("tick",       ctypes.c_uint32),
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
        self._state = None

    def connecter(self, tentatives=30, delai=0.2):
        if libc is None:
            raise RuntimeError("IPC POSIX indisponible sur Windows natif : lancez le mode distribué sous WSL/Linux.")

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

        if map_addr == _MAP_FAILED:
            err = ctypes.get_errno()
            libc.close(fd)
            raise OSError(err, "mmap de la SHM échoué")
        if self._sem_w == _SEM_FAILED or self._sem_r == _SEM_FAILED:
            err = ctypes.get_errno()
            libc.munmap(map_addr, size)
            libc.close(fd)
            raise OSError(err, "sem_open échoué")
        
        self._fd = fd
        self._map_addr = map_addr
        self._state = ctypes.cast(map_addr, ctypes.POINTER(GameStateC)).contents
        print(f"[bridge] Connecté à la SHM (peer_id={self.my_peer_id})")

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
        libc.sem_wait(self._sem_w)
        try:
            ctypes.memmove(ctypes.byref(out), ctypes.byref(self._state), ctypes.sizeof(GameStateC))
        finally:
            libc.sem_post(self._sem_w)
        return out

    def fermer(self):
        if self._map_addr: libc.munmap(self._map_addr, ctypes.sizeof(GameStateC))
        if self._sem_w: libc.sem_close(self._sem_w)
        if self._sem_r: libc.sem_close(self._sem_r)
        if self._fd >= 0: libc.close(self._fd)


# ── INSTANCE GLOBALE ──────────────────────────────────────────────────────────
_bridge = None
_warned_unit_cap = False
_v1_logged_events = set()
_pending_remote_dirty = {}
_V1_DIRTY_REPEAT_TICKS = 8

def init(player_id: int) -> bool:
    """Appelé par main.py pour s'accrocher à la mémoire IPC POSIX du ./c_net."""
    global _bridge
    _bridge = POSIXBridge(my_peer_id=player_id)
    try:
        _bridge.connecter()
        return True
    except Exception as e:
        print(f"[bridge] Erreur de connexion IPC : {e}")
        _bridge = None
        return False


def _set_unit_position(engine, unit, new_pos):
    if not unit.is_alive:
        _remove_unit_from_map(engine, unit)
        return

    game_map = getattr(engine, "game_map", None)
    if tuple(unit.position) == tuple(new_pos):
        if game_map is not None and unit not in game_map.map.values():
            game_map.map[tuple(new_pos)] = unit
        return

    if game_map is not None and hasattr(game_map, "maj_unit_posi"):
        game_map.maj_unit_posi(unit, tuple(new_pos))
    else:
        unit.position = tuple(new_pos)


def _slot_has_position(slot):
    return slot.x != 0.0 or slot.y != 0.0


def _log_v1_once(key, message):
    if key in _v1_logged_events:
        return
    _v1_logged_events.add(key)
    print(message)


def _write_unit_slot(slot, unit, owner, dirty):
    slot.id = unit.unit_id
    slot.team = owner
    slot.owner_peer = owner
    slot.hp_max = int(unit.max_hp)
    slot.alive = 1 if unit.is_alive else 0
    slot.x = float(unit.position[0])
    slot.y = float(unit.position[1])
    slot.hp = int(max(0, unit.current_hp))
    slot.dirty = 1 if dirty else 0


def _activate_remote_unit(engine, unit, slot):
    if slot.alive == 0 or slot.hp == 0:
        return False

    unit.v1_remote_seen = True
    unit.is_alive = True
    if unit.state == "dead":
        unit.state = "idle"
    unit.current_hp = min(int(slot.hp), int(unit.max_hp))

    if _slot_has_position(slot):
        _set_unit_position(engine, unit, (slot.x, slot.y))

    _log_v1_once(
        ("placement", unit.unit_id),
        f"[V1] Placement best-effort recu: unite distante #{unit.unit_id} "
        f"team={unit.team} pos=({slot.x:.1f},{slot.y:.1f}) hp={slot.hp}/{slot.hp_max}."
    )
    return True


def _remove_unit_from_map(engine, unit):
    game_map = getattr(engine, "game_map", None)
    if game_map is None:
        return
    if hasattr(game_map, "remove_unit_instance"):
        game_map.remove_unit_instance(unit)
    else:
        game_map.map.pop(unit.position, None)


def _mark_unit_dead(engine, unit):
    if hasattr(unit, "die"):
        unit.die()
    else:
        unit.current_hp = 0
        unit.is_alive = False
        unit.state = "dead"
        unit.target = None
        unit.direction = (0, 0)
    _remove_unit_from_map(engine, unit)


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

    global _warned_unit_cap
    all_units = list(engine.all_units())
    units = all_units[:MAX_UNITS]
    if len(all_units) > MAX_UNITS and not _warned_unit_cap:
        print(f"[bridge] Attention : {len(all_units)} unités, seules les {MAX_UNITS} premières sont synchronisées.")
        _warned_unit_cap = True
    
    # ── PHASE 1 : Lire les mises à jour du réseau depuis la SHM ──────────
    for unit in units:
        uid = unit.unit_id
        if uid >= MAX_UNITS:
            continue
        if unit.current_hp <= 0 and unit.is_alive:
            _mark_unit_dead(engine, unit)

        slot = c_state.units[uid]
        
        # Slot pas encore initialisé → ignorer complètement
        if slot.hp_max == 0:
            continue
        
        owner = unit.owner_id  # 0=R, 1=B
        if owner == my_peer:
            # ── NOTRE unité ──
            # Accepter uniquement les baisses de HP (dégâts infligés par l'adversaire)
            # slot.hp > 0 évite de lire un slot non initialisé
            if slot.hp > 0 and slot.hp < unit.current_hp:
                unit.current_hp = slot.hp
                unit.get_hit = 0.2
                if unit.current_hp <= 0:
                    _mark_unit_dead(engine, unit)
            elif slot.hp == 0 and slot.alive == 0 and unit.is_alive:
                _log_v1_once(
                    ("local-zombie", uid),
                    f"[V1 incoherence] Unite locale #{uid} annoncee morte par le reseau, "
                    "mais encore vivante ici: zombie observable avant V2."
                )
            # V1 volontairement imparfaite : un autre peer peut annoncer la mort
            # de notre unité, mais sans transfert de propriété cette mort n'est
            # pas considérée comme authoritative. La même unité peut donc rester
            # vivante ici et morte ailleurs (cas "zombie" attendu en V1).
        else:
            # ── UNITÉ DISTANTE ──
            if not getattr(unit, "v1_remote_seen", True):
                _activate_remote_unit(engine, unit, slot)
                continue

            if not unit.is_alive:
                if slot.alive == 1 and slot.hp > 0:
                    _log_v1_once(
                        ("remote-dead-here", uid),
                        f"[V1 incoherence] Unite distante #{uid} morte localement, "
                        "mais encore vivante chez son peer: divergence/zombie visible."
                    )
                continue

            # Mettre à jour la position (l'adversaire la contrôle)
            # Ne pas appliquer (0,0) qui signifie "pas encore reçu du réseau"
            if _slot_has_position(slot):
                _set_unit_position(engine, unit, (slot.x, slot.y))
            
            # Mettre à jour HP : accepter seulement les baisses (slot.hp > 0 pour éviter init à 0)
            if slot.hp > 0 and slot.hp < unit.current_hp:
                unit.current_hp = slot.hp
                unit.get_hit = 0.2
            elif slot.hp > unit.current_hp:
                _log_v1_once(
                    ("remote-hp-diverged", uid),
                    f"[V1 incoherence] Unite distante #{uid}: hp local={unit.current_hp}, "
                    f"hp reseau={slot.hp}. Pas de reconciliation en V1."
                )
            elif slot.alive == 0 and slot.hp == 0:
                _log_v1_once(
                    ("remote-zombie", uid),
                    f"[V1 incoherence] Unite distante #{uid} annoncee morte par le reseau, "
                    "mais gardee vivante localement: zombie attendu en V1."
                )
            
            # V1 volontairement imparfaite : on ne supprime pas une unité distante
            # uniquement parce que le réseau annonce sa mort. Un paquet perdu,
            # retardé ou écrasé peut laisser un peer avec une unité morte et
            # l'autre avec une unité encore active.

    # ── PHASE 2 : Écrire l'état Python dans la SHM pour le C ──────────────
    c_state.magic = PROTOCOL_MAGIC
    c_state.version = PROTOCOL_VERSION
    c_state.my_peer_id = my_peer
    c_state.unit_count = len(units)
    c_state.tick = int(getattr(engine, "current_turn", 0))

    for unit in units:
        uid = unit.unit_id
        if uid >= MAX_UNITS:
            continue

        slot = c_state.units[uid]
        owner = unit.owner_id  # 0=R, 1=B

        if owner == my_peer:
            # V1: chaque peer pousse en continu ses propres troupes.
            _write_unit_slot(slot, unit, owner, dirty=True)
        else:
            # V1: on ne possède jamais l'unité distante. On ne diffuse que les
            # dégâts observés localement, répétés sur quelques ticks pour que le C
            # ait le temps de les envoyer avant que le flag dirty retombe.
            current_shm_hp = slot.hp
            python_hp = int(unit.current_hp)

            remote_seen = getattr(unit, "v1_remote_seen", True)
            if remote_seen and current_shm_hp > 0 and python_hp < current_shm_hp:
                _pending_remote_dirty[uid] = _V1_DIRTY_REPEAT_TICKS
                unit.v1_last_remote_hp_sent = python_hp
                _log_v1_once(
                    ("remote-damage-sent", uid, python_hp),
                    f"[V1] Degat local sur unite distante #{uid}: hp={python_hp}. "
                    "Annonce best-effort envoyee sans propriete reseau."
                )

            pending = _pending_remote_dirty.get(uid, 0)
            if pending > 0:
                _write_unit_slot(slot, unit, owner, dirty=True)
                _pending_remote_dirty[uid] = pending - 1
            else:
                slot.dirty = 0

    try:
        _bridge.ecrire(c_state)
    except Exception:
        pass


def shutdown() -> None:
    """Ferme la connexion SHM."""
    if _bridge:
        _bridge.fermer()
