"""Minimal Python mirror of the shared C battle snapshot."""

from __future__ import annotations

import ctypes
from typing import Dict


MBAI_PROTOCOL_MAGIC = 0x4D424149
MBAI_PROTOCOL_VERSION = 1

MBAI_SHM_NAME = "/mbai_game_state"
MBAI_STATE_SEM_NAME = "/mbai_state_sem"

MBAI_MAX_UNITS = 1024
MBAI_NO_PEER = 0xFF

MBAI_UNIT_UNKNOWN = 0
MBAI_UNIT_CROSSBOW = ord("C")
MBAI_UNIT_KNIGHT = ord("K")
MBAI_UNIT_LIGHT_CAVALRY = ord("L")
MBAI_UNIT_PIKEMAN = ord("P")
MBAI_UNIT_SKIRMISHER = ord("S")


class MbaiUnitState(ctypes.Structure):
    _fields_ = [
        ("unit_id", ctypes.c_uint32),
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("hp", ctypes.c_float),
        ("max_hp", ctypes.c_float),
        ("unit_type", ctypes.c_uint8),
        ("team_id", ctypes.c_uint8),
        ("network_owner_peer", ctypes.c_uint8),
        ("alive", ctypes.c_uint8),
    ]


class MbaiGameState(ctypes.Structure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("header_size", ctypes.c_uint32),
        ("total_size", ctypes.c_uint32),
        ("unit_count", ctypes.c_uint32),
        ("max_units", ctypes.c_uint32),
        ("map_width", ctypes.c_uint32),
        ("map_height", ctypes.c_uint32),
        ("local_peer_id", ctypes.c_uint32),
        ("units", MbaiUnitState * MBAI_MAX_UNITS),
    ]


MBAI_UNIT_STATE_SIZE = 24
MBAI_GAME_STATE_HEADER_SIZE = 36
MBAI_GAME_STATE_SIZE = 24 * MBAI_MAX_UNITS + 36


def _field_offsets(struct_type: type[ctypes.Structure]) -> Dict[str, int]:
    return {
        field_name: getattr(struct_type, field_name).offset
        for field_name, *_ in struct_type._fields_
    }


def validate_layout() -> None:
    if ctypes.sizeof(MbaiUnitState) != MBAI_UNIT_STATE_SIZE:
        raise ValueError(
            f"MbaiUnitState size mismatch: {ctypes.sizeof(MbaiUnitState)} != {MBAI_UNIT_STATE_SIZE}"
        )

    if ctypes.sizeof(MbaiGameState) != MBAI_GAME_STATE_SIZE:
        raise ValueError(
            f"MbaiGameState size mismatch: {ctypes.sizeof(MbaiGameState)} != {MBAI_GAME_STATE_SIZE}"
        )

    if MbaiGameState.units.offset != MBAI_GAME_STATE_HEADER_SIZE:
        raise ValueError(
            f"MbaiGameState header offset mismatch: {MbaiGameState.units.offset} != {MBAI_GAME_STATE_HEADER_SIZE}"
        )

    expected_unit_offsets = {
        "unit_id": 0,
        "x": 4,
        "y": 8,
        "hp": 12,
        "max_hp": 16,
        "unit_type": 20,
        "team_id": 21,
        "network_owner_peer": 22,
        "alive": 23,
    }
    if _field_offsets(MbaiUnitState) != expected_unit_offsets:
        raise ValueError(f"MbaiUnitState offsets mismatch: {_field_offsets(MbaiUnitState)!r}")

    expected_game_offsets = {
        "magic": 0,
        "version": 4,
        "header_size": 8,
        "total_size": 12,
        "unit_count": 16,
        "max_units": 20,
        "map_width": 24,
        "map_height": 28,
        "local_peer_id": 32,
        "units": 36,
    }
    if _field_offsets(MbaiGameState) != expected_game_offsets:
        raise ValueError(f"MbaiGameState offsets mismatch: {_field_offsets(MbaiGameState)!r}")


def initialize_game_state(local_peer_id: int, map_width: int, map_height: int) -> MbaiGameState:
    state = MbaiGameState()
    ctypes.memset(ctypes.byref(state), 0, ctypes.sizeof(state))
    state.magic = MBAI_PROTOCOL_MAGIC
    state.version = MBAI_PROTOCOL_VERSION
    state.header_size = MBAI_GAME_STATE_HEADER_SIZE
    state.total_size = ctypes.sizeof(MbaiGameState)
    state.unit_count = 0
    state.max_units = MBAI_MAX_UNITS
    state.map_width = map_width
    state.map_height = map_height
    state.local_peer_id = local_peer_id
    return state


def state_from_buffer(buffer: object) -> MbaiGameState:
    validate_layout()
    if len(buffer) < ctypes.sizeof(MbaiGameState):
        raise ValueError("buffer too small for MbaiGameState")
    return MbaiGameState.from_buffer(buffer)


def describe_layout() -> dict[str, object]:
    validate_layout()
    return {
        "unit_state_size": ctypes.sizeof(MbaiUnitState),
        "game_state_size": ctypes.sizeof(MbaiGameState),
        "game_state_header_size": MbaiGameState.units.offset,
        "unit_offsets": _field_offsets(MbaiUnitState),
        "game_offsets": _field_offsets(MbaiGameState),
    }


validate_layout()


__all__ = [
    "MBAI_GAME_STATE_HEADER_SIZE",
    "MBAI_GAME_STATE_SIZE",
    "MBAI_MAX_UNITS",
    "MBAI_NO_PEER",
    "MBAI_PROTOCOL_MAGIC",
    "MBAI_PROTOCOL_VERSION",
    "MBAI_SHM_NAME",
    "MBAI_STATE_SEM_NAME",
    "MBAI_UNIT_CROSSBOW",
    "MBAI_UNIT_KNIGHT",
    "MBAI_UNIT_LIGHT_CAVALRY",
    "MBAI_UNIT_PIKEMAN",
    "MBAI_UNIT_SKIRMISHER",
    "MBAI_UNIT_STATE_SIZE",
    "MBAI_UNIT_UNKNOWN",
    "MbaiGameState",
    "MbaiUnitState",
    "describe_layout",
    "initialize_game_state",
    "state_from_buffer",
    "validate_layout",
]
