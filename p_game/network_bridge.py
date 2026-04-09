"""Bridge Python ↔ processus C via mémoire partagée POSIX.

Structure partagée : GameState (shared/protocol.h)
  PROTOCOL_MAGIC = 0xBABA1234
  SHM_NAME       = "/battle_state"
  SEM_WRITE_NAME = "/battle_sem_w"   # Python écrit  → C lit
  SEM_READ_NAME  = "/battle_sem_r"   # C écrit       → Python lit

Ordre de lancement :
  1. Compiler et lancer ./c_net dans WSL  (il crée la shm)
  2. Lancer Python                        (il s'y attache)
"""

from __future__ import annotations

import ctypes
import os
import time

# ── Constantes — doivent être identiques à shared/protocol.h ─────────────────
PROTOCOL_MAGIC   = 0xBABA1234
PROTOCOL_VERSION = 1
MAX_UNITS        = 64
SHM_NAME         = "/battle_state"
SEM_WRITE_NAME   = "/battle_sem_w"
SEM_READ_NAME    = "/battle_sem_r"
NET_PORT         = 9000

# ── Liaison avec libc (appels POSIX) ─────────────────────────────────────────
libc = ctypes.CDLL(None, use_errno=True)

libc.shm_open.argtypes  = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
libc.shm_open.restype   = ctypes.c_int
libc.mmap.argtypes      = [ctypes.c_void_p, ctypes.c_size_t,
                            ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, ctypes.c_long]
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


# ── Structures ctypes — miroir exact de shared/protocol.h ────────────────────

class UnitState(ctypes.Structure):
    """Miroir de UnitState en C — doit faire exactement 20 octets."""
    _fields_ = [
        ("id",         ctypes.c_uint8),        # 1
        ("team",       ctypes.c_uint8),        # 1  (0=A, 1=B)
        ("owner_peer", ctypes.c_uint8),        # 1
        ("alive",      ctypes.c_uint8),        # 1
        ("dirty",      ctypes.c_uint8),        # 1  (1 = à envoyer en réseau)
        ("_pad",       ctypes.c_uint8 * 3),    # 3
        ("x",          ctypes.c_float),        # 4
        ("y",          ctypes.c_float),        # 4
        ("hp",         ctypes.c_uint16),       # 2
        ("hp_max",     ctypes.c_uint16),       # 2
    ]                                          # = 20 octets


class GameState(ctypes.Structure):
    """Miroir de GameState en C — doit faire exactement 1296 octets."""
    _fields_ = [
        ("magic",      ctypes.c_uint32),       # 4
        ("version",    ctypes.c_uint16),       # 2
        ("unit_count", ctypes.c_uint8),        # 1
        ("my_peer_id", ctypes.c_uint8),        # 1
        ("tick",       ctypes.c_uint32),       # 4
        ("_pad",       ctypes.c_uint8 * 4),    # 4
        ("units",      UnitState * MAX_UNITS), # 64 * 20 = 1280
    ]                                          # = 1296 octets


def _verifier_layout() -> None:
    """Lève une erreur si les structs Python ne correspondent pas au C."""
    assert ctypes.sizeof(UnitState) == 20, \
        f"UnitState: {ctypes.sizeof(UnitState)} octets (attendu 20)"
    attendu = 16 + MAX_UNITS * 20
    assert ctypes.sizeof(GameState) == attendu, \
        f"GameState: {ctypes.sizeof(GameState)} octets (attendu {attendu})"


_verifier_layout()


# ── Classe principale ─────────────────────────────────────────────────────────

class NetworkBridge:
    """Interface Python ↔ processus C via shm POSIX.

    Le processus C (./c_net) doit être lancé en premier : il est responsable
    de créer la shm et les sémaphores.

    Exemple d'utilisation :
        bridge = NetworkBridge(my_peer_id=0)
        bridge.connecter()
        bridge.ecrire(mon_game_state)   # Python → C → UDP vers pair
        etat = bridge.lire()            # UDP pair → C → Python
        bridge.fermer()
    """

    def __init__(self, my_peer_id: int = 0):
        self.my_peer_id = my_peer_id
        self._fd        = -1
        self._sem_w     = None   # sémaphore écriture (Python→C)
        self._sem_r     = None   # sémaphore lecture  (C→Python)
        self._map_addr  = None
        self._state: GameState | None = None

    # ── Connexion ─────────────────────────────────────────────────────────────
    def connecter(self, tentatives: int = 10, delai: float = 0.5) -> None:
        """Tente de s'attacher à la shm, avec re-essais."""
        fd = -1
        for i in range(tentatives):
            fd = libc.shm_open(SHM_NAME.encode(), os.O_RDWR, 0)
            if fd >= 0:
                break
            err = ctypes.get_errno()
            if i < tentatives - 1:
                print(f"[bridge] shm pas encore prête ({i+1}/{tentatives}), attente {delai}s…")
                time.sleep(delai)
            else:
                raise OSError(err,
                    f"shm_open({SHM_NAME}) échoué : {os.strerror(err)}\n"
                    "  ➜ Lance d'abord ./c_net dans WSL !")

        size     = ctypes.sizeof(GameState)
        map_addr = libc.mmap(None, size,
                             _PROT_READ | _PROT_WRITE, _MAP_SHARED, fd, 0)
        if map_addr == _MAP_FAILED:
            err = ctypes.get_errno()
            libc.close(fd)
            raise OSError(err, f"mmap: {os.strerror(err)}")

        sem_w = libc.sem_open(SEM_WRITE_NAME.encode(), 0, 0, 0)
        if sem_w == _SEM_FAILED:
            err = ctypes.get_errno()
            libc.munmap(map_addr, size)
            libc.close(fd)
            raise OSError(err, f"sem_open write ({SEM_WRITE_NAME}): {os.strerror(err)}")

        sem_r = libc.sem_open(SEM_READ_NAME.encode(), 0, 0, 0)
        if sem_r == _SEM_FAILED:
            err = ctypes.get_errno()
            libc.sem_close(sem_w)
            libc.munmap(map_addr, size)
            libc.close(fd)
            raise OSError(err, f"sem_open read ({SEM_READ_NAME}): {os.strerror(err)}")

        self._fd       = fd
        self._map_addr = map_addr
        self._sem_w    = sem_w
        self._sem_r    = sem_r
        self._state    = ctypes.cast(map_addr, ctypes.POINTER(GameState)).contents
        print(f"[bridge] ✓ Connecté à {SHM_NAME} (peer_id={self.my_peer_id})")

    # Alias anglais pour compatibilité
    def connect(self, *args, **kwargs) -> None:
        self.connecter(*args, **kwargs)

    # ── Écriture (Python → shm → C → UDP) ────────────────────────────────────
    def ecrire(self, snapshot: GameState) -> None:
        """Copie snapshot dans la shm. Le C lira et enverra les unités dirty."""
        if self._state is None:
            raise RuntimeError("bridge non connecté")
        libc.sem_wait(self._sem_w)
        try:
            ctypes.memmove(ctypes.byref(self._state),
                           ctypes.byref(snapshot),
                           ctypes.sizeof(GameState))
        finally:
            libc.sem_post(self._sem_w)

    def write(self, snapshot: GameState) -> None:
        self.ecrire(snapshot)

    # ── Lecture (UDP → C → shm → Python) ─────────────────────────────────────
    def lire(self) -> GameState:
        """Lit la shm et retourne une copie du GameState actuel."""
        if self._state is None:
            raise RuntimeError("bridge non connecté")
        out = GameState()
        libc.sem_wait(self._sem_r)
        try:
            ctypes.memmove(ctypes.byref(out),
                           ctypes.byref(self._state),
                           ctypes.sizeof(GameState))
        finally:
            libc.sem_post(self._sem_r)
        return out

    def read(self) -> GameState:
        return self.lire()

    # ── Fermeture ─────────────────────────────────────────────────────────────
    def fermer(self) -> None:
        size = ctypes.sizeof(GameState)
        if self._sem_w not in (None, _SEM_FAILED):
            libc.sem_close(self._sem_w)
        if self._sem_r not in (None, _SEM_FAILED):
            libc.sem_close(self._sem_r)
        if self._map_addr not in (None, _MAP_FAILED):
            libc.munmap(self._map_addr, size)
        if self._fd >= 0:
            libc.close(self._fd)
        self._fd = self._map_addr = self._sem_w = self._sem_r = self._state = None
        print("[bridge] Déconnecté")

    def close(self) -> None:
        self.fermer()

    def __enter__(self):
        self.connecter()
        return self

    def __exit__(self, *_):
        self.fermer()


# ── API publique appelée par main.py (--distributed) ─────────────────────────
_bridge: NetworkBridge | None = None


def init(player_id: int | None = None, **_kwargs) -> None:
    """Initialise le bridge réseau. Appelé automatiquement par main.py."""
    global _bridge
    pid = int(player_id) if player_id is not None else 0
    _bridge = NetworkBridge(my_peer_id=pid)
    try:
        _bridge.connecter()
    except OSError as e:
        print(f"[bridge] ⚠ Connexion échouée : {e}")
        _bridge = None


def get_bridge() -> NetworkBridge | None:
    """Retourne le bridge actif, ou None si non connecté."""
    return _bridge


# ── Script de test autonome ───────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    print("=== Test Network Bridge ===\n")
    peer_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    bridge = NetworkBridge(my_peer_id=peer_id)
    try:
        bridge.connecter()
    except OSError as e:
        print(f"ERREUR : {e}")
        sys.exit(1)

    # Construit un GameState de test
    gs = GameState()
    gs.magic        = PROTOCOL_MAGIC
    gs.version      = PROTOCOL_VERSION
    gs.my_peer_id   = peer_id
    gs.unit_count   = 2
    gs.tick         = 1

    gs.units[0] = UnitState(
        id=0, team=peer_id, owner_peer=peer_id,
        alive=1, dirty=1,
        x=10.0, y=5.0, hp=100, hp_max=100
    )
    gs.units[1] = UnitState(
        id=1, team=peer_id, owner_peer=peer_id,
        alive=1, dirty=1,
        x=15.0, y=8.0, hp=60, hp_max=60
    )

    print(f"[test] Écriture de {gs.unit_count} unités (dirty=1)…")
    bridge.ecrire(gs)
    print("[test] ✓ Écrit dans la shm — le C devrait les envoyer en UDP\n")

    print("[test] Attente 3s puis lecture de la shm (mises à jour réseau)…")
    time.sleep(3)
    recv = bridge.lire()
    print(f"[test] Lu : magic=0x{recv.magic:08X} tick={recv.tick} unités={recv.unit_count}")
    for i in range(recv.unit_count):
        u = recv.units[i]
        print(f"         unité{u.id} team={u.team} peer={u.owner_peer} "
              f"pos=({u.x:.1f},{u.y:.1f}) hp={u.hp}/{u.hp_max} alive={u.alive}")

    bridge.fermer()
    print("\n=== Terminé ===")
