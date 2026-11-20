"""Discord Rich Presence over Discord's local IPC pipe (no extra packages).

The game calls ``DiscordPresence.set(activity)`` every frame with a plain dict.
A background thread connects to the Discord desktop app when it is running,
sends the activity only when it changed and never faster than Discord's rate
limit, and silently retries when Discord is closed or restarted. If anything
goes wrong the game simply carries on without presence.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import threading
import time
import uuid
from typing import Callable, Optional

OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2

MIN_INTERVAL = 4.0      # Discord allows 5 activity updates per 20 seconds
RETRY_INTERVAL = 15.0   # how often to look for a (re)started Discord app


def _pipe_paths():
    if sys.platform == "win32":
        return [rf"\\?\pipe\discord-ipc-{i}" for i in range(10)]
    base = (os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR")
            or os.environ.get("TMP") or os.environ.get("TEMP") or "/tmp")
    dirs = [base, os.path.join(base, "app", "com.discordapp.Discord"),
            os.path.join(base, "snap.discord")]
    return [os.path.join(d, f"discord-ipc-{i}") for d in dirs for i in range(10)]


class _PipeTransport:
    """Blocking byte stream to the Discord client (named pipe or unix socket)."""

    def __init__(self):
        last = None
        for path in _pipe_paths():
            try:
                if sys.platform == "win32":
                    self._f = open(path, "r+b", buffering=0)
                    self._sock = None
                else:
                    import socket
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(5)
                    s.connect(path)
                    self._sock = s
                    self._f = None
                return
            except OSError as exc:
                last = exc
        raise last or OSError("Discord niet gevonden")

    def write(self, data: bytes) -> None:
        if self._sock:
            self._sock.sendall(data)
        else:
            self._f.write(data)

    def read(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf)) if self._sock else self._f.read(n - len(buf))
            if not chunk:
                raise OSError("verbinding met Discord verbroken")
            buf += chunk
        return buf

    def close(self) -> None:
        try:
            (self._sock or self._f).close()
        except OSError:
            pass


class DiscordPresence:
    def __init__(self, client_id: str, enabled: Callable[[], bool] = lambda: True,
                 transport_factory=_PipeTransport, start_thread: bool = True):
        self.client_id = (client_id or "").strip()
        self.enabled = enabled
        self._factory = transport_factory
        self._conn = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = False
        self._wanted: Optional[dict] = None
        self._sent: Optional[dict] = "unset"  # type: ignore[assignment]
        self._last_send = 0.0
        self._last_try = -RETRY_INTERVAL
        self.connected = False
        self._thread = None
        if self.client_id and start_thread:
            self._thread = threading.Thread(target=self._run, name="discord-rpc", daemon=True)
            self._thread.start()

    @property
    def active(self) -> bool:
        return bool(self.client_id)

    # ---------------------------------------------------------- game thread
    def set(self, activity: Optional[dict]) -> None:
        """Remember the activity to show; cheap enough to call every frame."""
        if not self.client_id:
            return
        with self._lock:
            if activity != self._wanted:
                self._wanted = activity
                self._wake.set()

    def close(self) -> None:
        """Clear the status and disconnect (called when the game exits)."""
        self._stop = True
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=1.5)
        else:
            self._shutdown()

    # ------------------------------------------------------------- protocol
    def _send(self, op: int, payload: dict) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._conn.write(struct.pack("<II", op, len(data)) + data)

    def _recv(self) -> tuple:
        op, length = struct.unpack("<II", self._conn.read(8))
        payload = json.loads(self._conn.read(length).decode("utf-8")) if length else {}
        return op, payload

    def _connect(self) -> bool:
        self._last_try = time.monotonic()
        try:
            self._conn = self._factory()
            self._send(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
            op, payload = self._recv()
            if op == OP_CLOSE or payload.get("evt") != "READY":
                raise OSError(f"Discord weigerde de verbinding: {payload}")
            self.connected = True
            self._sent = "unset"  # type: ignore[assignment]
            return True
        except (OSError, ValueError, struct.error):
            self._disconnect()
            return False

    def _disconnect(self) -> None:
        if self._conn:
            self._conn.close()
        self._conn = None
        self.connected = False

    def _set_activity(self, activity: Optional[dict]) -> bool:
        try:
            self._send(OP_FRAME, {
                "cmd": "SET_ACTIVITY",
                "args": {"pid": os.getpid(), "activity": activity},
                "nonce": uuid.uuid4().hex,
            })
            op, payload = self._recv()
            if op == OP_CLOSE:
                raise OSError("Discord sloot de verbinding")
            self._last_send = time.monotonic()
            self._sent = activity
            return True
        except (OSError, ValueError, struct.error):
            self._disconnect()
            return False

    def step(self) -> None:
        """One round of the worker loop (also used directly by the tests)."""
        with self._lock:
            wanted = self._wanted if self.enabled() else None
            self._wake.clear()
        if not self.connected:
            if wanted is None or time.monotonic() - self._last_try < RETRY_INTERVAL:
                return
            if not self._connect():
                return
        if wanted != self._sent and time.monotonic() - self._last_send >= MIN_INTERVAL:
            self._set_activity(wanted)

    def _shutdown(self) -> None:
        if self.connected:
            self._set_activity(None)
        self._disconnect()

    def _run(self) -> None:
        while not self._stop:
            try:
                self.step()
            except Exception:  # never let presence take the game down
                self._disconnect()
            self._wake.wait(1.0)
        try:
            self._shutdown()
        except Exception:
            pass
