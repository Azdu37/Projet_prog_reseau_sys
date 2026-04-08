"""Minimal POSIX shared-memory bridge for the v1 battle snapshot."""

from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass

from shared_state import (
    MBAI_PROTOCOL_MAGIC,
    MBAI_PROTOCOL_VERSION,
    MBAI_SHM_NAME,
    MBAI_STATE_SEM_NAME,
    MbaiGameState,
    initialize_game_state,
)


O_CREAT = os.O_CREAT
O_EXCL = os.O_EXCL
O_RDWR = os.O_RDWR

PROT_READ = 0x1
PROT_WRITE = 0x2
MAP_SHARED = 0x01


libc = ctypes.CDLL(None, use_errno=True)
libc.shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
libc.shm_open.restype = ctypes.c_int
libc.ftruncate.argtypes = [ctypes.c_int, ctypes.c_long]
libc.ftruncate.restype = ctypes.c_int
libc.mmap.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_long,
]
libc.mmap.restype = ctypes.c_void_p
libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
libc.munmap.restype = ctypes.c_int
libc.close.argtypes = [ctypes.c_int]
libc.close.restype = ctypes.c_int
libc.shm_unlink.argtypes = [ctypes.c_char_p]
libc.shm_unlink.restype = ctypes.c_int
libc.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
libc.sem_open.restype = ctypes.c_void_p
libc.sem_close.argtypes = [ctypes.c_void_p]
libc.sem_close.restype = ctypes.c_int
libc.sem_wait.argtypes = [ctypes.c_void_p]
libc.sem_wait.restype = ctypes.c_int
libc.sem_post.argtypes = [ctypes.c_void_p]
libc.sem_post.restype = ctypes.c_int
libc.sem_unlink.argtypes = [ctypes.c_char_p]
libc.sem_unlink.restype = ctypes.c_int

SEM_FAILED = ctypes.c_void_p(-1).value
MAP_FAILED = ctypes.c_void_p(-1).value


def _check_zero(result: int, name: str) -> None:
    if result != 0:
        err = ctypes.get_errno()
        raise OSError(err, f"{name} failed: {os.strerror(err)}")


@dataclass
class NetworkBridge:
    local_peer_id: int = 1
    map_width: int = 210
    map_height: int = 210
    fd: int | None = None
    sem: int | None = None
    map_addr: int | None = None
    state: MbaiGameState | None = None

    def connect(self, create: bool = False) -> None:
        flags = O_RDWR
        if create:
            flags |= O_CREAT

        fd = libc.shm_open(MBAI_SHM_NAME.encode(), flags, 0o666)
        if fd < 0:
            err = ctypes.get_errno()
            raise OSError(err, f"shm_open failed: {os.strerror(err)}")

        if create:
            _check_zero(libc.ftruncate(fd, ctypes.sizeof(MbaiGameState)), "ftruncate")

        map_addr = libc.mmap(None, ctypes.sizeof(MbaiGameState), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)
        if map_addr == MAP_FAILED:
            err = ctypes.get_errno()
            libc.close(fd)
            raise OSError(err, f"mmap failed: {os.strerror(err)}")

        sem = libc.sem_open(MBAI_STATE_SEM_NAME.encode(), O_CREAT if create else 0, 0o666, 1)
        if sem == SEM_FAILED:
            err = ctypes.get_errno()
            libc.munmap(map_addr, ctypes.sizeof(MbaiGameState))
            libc.close(fd)
            raise OSError(err, f"sem_open failed: {os.strerror(err)}")

        self.fd = fd
        self.sem = sem
        self.map_addr = map_addr
        self.state = ctypes.cast(map_addr, ctypes.POINTER(MbaiGameState)).contents

        if create and self.state.magic != MBAI_PROTOCOL_MAGIC:
            fresh = initialize_game_state(self.local_peer_id, self.map_width, self.map_height)
            ctypes.memmove(map_addr, ctypes.byref(fresh), ctypes.sizeof(MbaiGameState))

    def lock(self) -> None:
        if self.sem is None:
            raise RuntimeError("bridge not connected")
        _check_zero(libc.sem_wait(self.sem), "sem_wait")

    def unlock(self) -> None:
        if self.sem is None:
            raise RuntimeError("bridge not connected")
        _check_zero(libc.sem_post(self.sem), "sem_post")

    def close(self) -> None:
        if self.sem not in (None, SEM_FAILED):
            libc.sem_close(self.sem)
        if self.map_addr not in (None, MAP_FAILED):
            libc.munmap(self.map_addr, ctypes.sizeof(MbaiGameState))
        if self.fd not in (None, -1):
            libc.close(self.fd)
        self.fd = None
        self.sem = None
        self.map_addr = None
        self.state = None

    @staticmethod
    def cleanup() -> None:
        libc.shm_unlink(MBAI_SHM_NAME.encode())
        libc.sem_unlink(MBAI_STATE_SEM_NAME.encode())


def _print_state(state: MbaiGameState) -> None:
    print(f"magic=0x{state.magic:08X} version={state.version} units={state.unit_count}")
    if state.unit_count == 0:
        print("no units")
        return

    unit = state.units[0]
    print(
        "unit0: "
        f"id={unit.unit_id} type={chr(unit.unit_type)} team={chr(unit.team_id)} "
        f"pos=({unit.x:.1f}, {unit.y:.1f}) hp={unit.hp:.1f}/{unit.max_hp:.1f} "
        f"owner={unit.network_owner_peer} alive={unit.alive}"
    )


def _write_demo(state: MbaiGameState) -> None:
    state.magic = MBAI_PROTOCOL_MAGIC
    state.version = MBAI_PROTOCOL_VERSION
    state.header_size = MbaiGameState.units.offset
    state.total_size = ctypes.sizeof(MbaiGameState)
    state.max_units = 1024
    state.map_width = 210
    state.map_height = 210
    state.local_peer_id = 2
    state.unit_count = 1

    unit = state.units[0]
    unit.unit_id = 42
    unit.x = 99.0
    unit.y = 12.5
    unit.hp = 18.0
    unit.max_hp = 22.0
    unit.unit_type = ord("C")
    unit.team_id = ord("B")
    unit.network_owner_peer = 2
    unit.alive = 1


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "read"

    if mode == "cleanup":
        NetworkBridge.cleanup()
        print("IPC objects removed.")
        return 0

    bridge = NetworkBridge()
    bridge.connect(create=(mode == "write-demo"))

    try:
        bridge.lock()
        assert bridge.state is not None

        if mode == "read":
            _print_state(bridge.state)
        elif mode == "write-demo":
            _write_demo(bridge.state)
            _print_state(bridge.state)
        else:
            print(f"unknown mode: {mode}", file=sys.stderr)
            return 1
    finally:
        try:
            bridge.unlock()
        finally:
            bridge.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
