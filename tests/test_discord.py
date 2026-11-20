"""Discord Rich Presence client, tested against a fake Discord IPC endpoint."""
import json
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import discord_rpc  # noqa: E402
from game.discord_rpc import DiscordPresence  # noqa: E402


class FakeDiscord:
    """Speaks Discord's framing: <op:uint32><len:uint32><json>."""

    instances = []

    def __init__(self, refuse=False):
        self.frames = []          # (op, payload) received from the game
        self._out = b""
        self.closed = False
        self.refuse = refuse
        FakeDiscord.instances.append(self)

    def write(self, data):
        op, length = struct.unpack("<II", data[:8])
        payload = json.loads(data[8:8 + length])
        self.frames.append((op, payload))
        if op == discord_rpc.OP_HANDSHAKE:
            reply = (2, {"code": 4000, "message": "Invalid Client ID"}) if self.refuse else \
                (1, {"cmd": "DISPATCH", "evt": "READY", "data": {"v": 1}})
        else:
            reply = (1, {"cmd": payload["cmd"], "nonce": payload["nonce"], "data": {}})
        body = json.dumps(reply[1]).encode()
        self._out += struct.pack("<II", reply[0], len(body)) + body

    def read(self, n):
        chunk, self._out = self._out[:n], self._out[n:]
        return chunk

    def close(self):
        self.closed = True

    def activities(self):
        return [p["args"]["activity"] for op, p in self.frames
                if op == discord_rpc.OP_FRAME and p.get("cmd") == "SET_ACTIVITY"]


ACT_A = {"details": "Dossier 1-1: Test", "state": "Loopt door de gang"}
ACT_B = {"details": "Dossier 1-1: Test", "state": "Duwt een dossier"}


class DiscordPresenceTest(unittest.TestCase):
    def setUp(self):
        FakeDiscord.instances.clear()
        self._interval = discord_rpc.MIN_INTERVAL
        self._retry = discord_rpc.RETRY_INTERVAL
        discord_rpc.MIN_INTERVAL = 0
        discord_rpc.RETRY_INTERVAL = 0
        self.enabled = True

    def tearDown(self):
        discord_rpc.MIN_INTERVAL = self._interval
        discord_rpc.RETRY_INTERVAL = self._retry

    def make(self, factory=FakeDiscord, client_id="1234567890"):
        return DiscordPresence(client_id, enabled=lambda: self.enabled,
                               transport_factory=factory, start_thread=False)

    def test_handshake_and_activity(self):
        p = self.make()
        p.set(ACT_A)
        p.step()
        fake = FakeDiscord.instances[0]
        self.assertEqual(fake.frames[0], (0, {"v": 1, "client_id": "1234567890"}))
        self.assertEqual(fake.activities(), [ACT_A])
        self.assertEqual(fake.frames[1][1]["args"]["pid"], os.getpid())

    def test_only_sends_changes(self):
        p = self.make()
        p.set(ACT_A)
        p.step()
        p.set(ACT_A)
        p.step()
        p.step()
        p.set(ACT_B)
        p.step()
        self.assertEqual(FakeDiscord.instances[0].activities(), [ACT_A, ACT_B])

    def test_rate_limit_keeps_latest(self):
        discord_rpc.MIN_INTERVAL = 3600
        p = self.make()
        p.set(ACT_A)
        p.step()
        p.set(ACT_B)
        p.step()          # too soon: held back
        fake = FakeDiscord.instances[0]
        self.assertEqual(fake.activities(), [ACT_A])
        p._last_send -= 3600
        p.step()          # the latest wanted status goes out once allowed
        self.assertEqual(fake.activities(), [ACT_A, ACT_B])

    def test_disabling_clears_status(self):
        p = self.make()
        p.set(ACT_A)
        p.step()
        self.enabled = False
        p.step()
        self.assertEqual(FakeDiscord.instances[0].activities(), [ACT_A, None])

    def test_close_clears_status_and_disconnects(self):
        p = self.make()
        p.set(ACT_A)
        p.step()
        p.close()
        fake = FakeDiscord.instances[0]
        self.assertEqual(fake.activities(), [ACT_A, None])
        self.assertTrue(fake.closed)

    def test_discord_not_running_is_harmless(self):
        def no_discord():
            raise OSError("pipe not found")
        p = self.make(factory=no_discord)
        p.set(ACT_A)
        p.step()
        self.assertFalse(p.connected)
        p.close()

    def test_reconnects_after_discord_restart(self):
        p = self.make()
        p.set(ACT_A)
        p.step()
        FakeDiscord.instances[0].read = lambda n: b""   # Discord quits
        p.set(ACT_B)
        p.step()
        self.assertFalse(p.connected)
        p.step()                                        # Discord is back
        self.assertTrue(p.connected)
        self.assertEqual(FakeDiscord.instances[1].activities(), [ACT_B])

    def test_refused_client_id(self):
        p = self.make(factory=lambda: FakeDiscord(refuse=True))
        p.set(ACT_A)
        p.step()
        self.assertFalse(p.connected)
        self.assertEqual(FakeDiscord.instances[0].activities(), [])

    def test_without_client_id_does_nothing(self):
        p = self.make(client_id="")
        self.assertFalse(p.active)
        p.set(ACT_A)
        p.step()
        self.assertEqual(FakeDiscord.instances, [])


if __name__ == "__main__":
    unittest.main()
