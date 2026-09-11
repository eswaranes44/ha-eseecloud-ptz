"""Protocol construction tests."""

import importlib.util
import struct
import sys
import unittest
from pathlib import Path

MODULE = Path(__file__).parents[1] / "custom_components/eseecloud_ptz/client.py"
SPEC = importlib.util.spec_from_file_location("eseecloud_client", MODULE)
client = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = client
SPEC.loader.exec_module(client)


class ProtocolTests(unittest.TestCase):
    def test_long_login_layout(self):
        transaction, packet = client._p2pk_login("admin", "a" * 32)
        version, reply_id, command, status, size = struct.unpack("<5I", packet[4:24])
        self.assertEqual(packet[:4], b"P2PK")
        self.assertEqual(
            (version, reply_id, command, status, size),
            (1, transaction, 0x8C, 0, 2048),
        )
        self.assertEqual(packet[24:29], b"admin")
        self.assertEqual(packet[24 + 1024 : 24 + 1024 + 32], b"a" * 32)
        self.assertEqual(len(packet), 2072)

    def test_ptz_layout(self):
        transaction, packet = client._p2pk_ptz(5, 6, 0xB4000074)
        version, reply_id, command, marker, size = struct.unpack("<5I", packet[4:24])
        self.assertEqual(
            (version, reply_id, command, marker, size),
            (1, transaction, 0x14, 0xB4000074, 16),
        )
        self.assertEqual(struct.unpack("<4I", packet[24:40]), (0, 5, 6, 0))

    def test_credential_validation(self):
        client._validate_credential("0123456789abcdef0123456789abcdef")
        for bad in ("", "x" * 32, "a" * 31, "a" * 33):
            with self.assertRaises(ValueError):
                client._validate_credential(bad)


if __name__ == "__main__":
    unittest.main()
