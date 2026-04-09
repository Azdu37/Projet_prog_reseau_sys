# network_bridge.py
import socket
import threading
from typing import Callable
from shared_state import (
    serialize_game_state, deserialize_game_state,
    LOCAL_C_PORT, PYTHON_LISTEN_PORT
)

_send_sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_player_id: int = 0
_running: bool = False


def init(player_id: int, **kwargs) -> None:
    """Must be called once before any other function."""
    global _player_id
    _player_id = player_id
    # Bind to localhost for IPC from C process
    try:
        _listen_sock.bind(("127.0.0.1", PYTHON_LISTEN_PORT))
    except OSError as e:
        print(f"[NETWORK] Could not bind to {PYTHON_LISTEN_PORT}: {e}")


def push_local_update(game_state) -> None:
    """Call this after every meaningful local state change."""
    if _player_id is None:
        return
    payload = serialize_game_state(game_state, _player_id)
    try:
        _send_sock.sendto(payload, ("127.0.0.1", LOCAL_C_PORT))
    except OSError as e:
        # C process might not be ready yet or closed
        pass


def start_listener(apply_callback: Callable) -> None:
    """Start background daemon thread that applies remote updates."""
    global _running
    _running = True

    def _loop():
        while _running:
            try:
                data, _ = _listen_sock.recvfrom(65535)
                state = deserialize_game_state(data)
                apply_callback(state)
            except OSError:
                break  # socket closed on shutdown

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def shutdown() -> None:
    global _running
    _running = False
    _send_sock.close()
    _listen_sock.close()
