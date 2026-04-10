# shared_state.py
# WARNING: The struct format strings below MUST match shared/protocol_def.h exactly.
# Any mismatch causes silent data corruption. Update both files together.

import struct
import time

# Port constants — MUST match #define values in shared/protocol_def.h
LOCAL_C_PORT       = 6000   # Python sends to C here
PYTHON_LISTEN_PORT = 6001   # Python listens here

MAX_UNITS = 256

# NetworkMessage layout (packed, no padding):
# uint8  msg_type
# uint32 sender_id
# uint64 timestamp_ms
# uint32 num_units
# [256 x UnitState]: float x, float y, int32 hp, uint32 unit_id, uint32 owner_id

HEADER_FORMAT = "!BIQI"           # B=uint8, I=uint32, Q=uint64, I=uint32
HEADER_SIZE   = struct.calcsize(HEADER_FORMAT)

UNIT_FORMAT = "!ffIII"            # float x, float y, uint32 hp, uint32 unit_id, uint32 owner_id
UNIT_SIZE   = struct.calcsize(UNIT_FORMAT)

TOTAL_SIZE = HEADER_SIZE + UNIT_SIZE * MAX_UNITS


def serialize_game_state(game_state, sender_id: int, msg_type: int = 0x01) -> bytes:
    """Serialize the full game state to a fixed-size NetworkMessage byte string."""
    ts = int(time.time() * 1000)
    units = list(game_state.all_units())[:MAX_UNITS]
    header = struct.pack(HEADER_FORMAT, msg_type, sender_id, ts, len(units))
    body = b"".join(
        struct.pack(UNIT_FORMAT, float(u.position[0]), float(u.position[1]), int(u.current_hp), int(u.unit_id if hasattr(u, 'unit_id') else 0), int(u.owner_id if hasattr(u, 'owner_id') else 0))
        for u in units
    )
    padding = bytes(UNIT_SIZE * (MAX_UNITS - len(units)))
    return header + body + padding


def deserialize_game_state(data: bytes) -> dict:
    """Deserialize a NetworkMessage byte string into a Python dict."""
    msg_type, sender_id, ts, num_units = struct.unpack_from(HEADER_FORMAT, data, 0)
    units = []
    offset = HEADER_SIZE
    for _ in range(min(num_units, MAX_UNITS)):
        x, y, hp, unit_id, owner_id = struct.unpack_from(UNIT_FORMAT, data, offset)
        units.append({"x": x, "y": y, "hp": hp, "unit_id": unit_id, "owner_id": owner_id})
        offset += UNIT_SIZE
    return {
        "msg_type":     msg_type,
        "sender_id":    sender_id,
        "timestamp_ms": ts,
        "units":        units,
    }
