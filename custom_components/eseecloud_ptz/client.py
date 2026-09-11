"""Synchronous client for the reverse-engineered EseeCloud local PTZ protocol."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import socket
import struct
import time
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

MAGIC = bytes.fromhex("abbccdde")
CLIENT = bytes.fromhex("d9ffcc028c38eed2d199ac6026947fae")
SERVER = bytes.fromhex("96d5390d12fcbe8f4790d932ccd849f3")
ARQ_RECORD_MAGIC = bytes.fromhex("cefaeffe")


class EseeCloudError(Exception):
    """Base client error."""


class EseeCloudAuthenticationError(EseeCloudError):
    """Authentication failed."""


class EseeCloudProtocolError(EseeCloudError):
    """Peer returned malformed or unexpected protocol data."""


class Reader:
    """Deadline-aware WebSocket reader."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buf = bytearray()
        self.deadline = time.monotonic() + 8

    def exact(self, count: int) -> bytes:
        while len(self.buf) < count:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("stage deadline reached")
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("peer closed connection")
            self.buf.extend(chunk)
        value = bytes(self.buf[:count])
        del self.buf[:count]
        return value

    def frame(self) -> tuple[int, bytes]:
        first, second = self.exact(2)
        if first & 0x70 or not first & 0x80:
            raise EseeCloudProtocolError("fragmented/extended frame unsupported")
        size = second & 127
        if size == 126:
            size = struct.unpack(">H", self.exact(2))[0]
        elif size == 127:
            size = struct.unpack(">Q", self.exact(8))[0]
        if size > 65536:
            raise EseeCloudProtocolError("response exceeds 64 KiB safety limit")
        mask = self.exact(4) if second & 128 else None
        data = self.exact(size)
        if mask:
            data = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
        return first & 15, data


def _send_frame(sock: socket.socket, opcode: int, data: bytes) -> None:
    if len(data) >= 126:
        raise EseeCloudProtocolError("control frame exceeds small-frame limit")
    sock.sendall(bytes([0x80 | opcode, len(data)]) + data)


def _send_binary(sock: socket.socket, data: bytes) -> None:
    length = len(data)
    if length < 126:
        header = bytes((0x82, length))
    elif length <= 0xFFFF:
        header = b"\x82\x7e" + struct.pack(">H", length)
    else:
        header = b"\x82\x7f" + struct.pack(">Q", length)
    # Vendor compatibility: these devices accept the unmasked framing used by
    # their own clients. This is not a general-purpose WebSocket implementation.
    sock.sendall(header + data)


def _binary_reply(reader: Reader) -> bytes:
    for _ in range(16):
        opcode, data = reader.frame()
        if opcode == 2:
            return data
        if opcode == 8:
            raise ConnectionError("WebSocket closed by peer")
        if opcode == 9 and len(data) <= 125:
            _send_frame(reader.sock, 10, data)
        elif opcode != 10:
            raise EseeCloudProtocolError(f"unexpected WebSocket opcode {opcode}")
    raise EseeCloudProtocolError("too many WebSocket control frames")


def _application_reply(reader: Reader) -> bytes:
    first = _binary_reply(reader)
    if len(first) < 8 or first[:4] != ARQ_RECORD_MAGIC:
        return first
    size = struct.unpack("<I", first[4:8])[0]
    if size > 65536:
        raise EseeCloudProtocolError("ARQ record exceeds 64 KiB safety limit")
    data = bytearray(first[8:])
    while len(data) < size:
        part = _binary_reply(reader)
        if len(data) + len(part) > size:
            raise EseeCloudProtocolError("ARQ record contains excess data")
        data.extend(part)
    return bytes(data)


def _parse_iot(
    data: bytes, expected_cmd: int | None = None, expected_sid: int | None = None
) -> tuple[int, int, bytes]:
    if len(data) < 32 or data[:4] != MAGIC:
        raise EseeCloudProtocolError("invalid IOTLink packet")
    cmd, _version, _arg, sid, _reserved, result, size = struct.unpack(
        "<7I", data[4:32]
    )
    if size != len(data) - 32:
        raise EseeCloudProtocolError("IOTLink body length mismatch")
    if expected_cmd is not None and cmd != expected_cmd:
        raise EseeCloudProtocolError(
            f"expected IOTLink 0x{expected_cmd:02x}, received 0x{cmd:02x}"
        )
    if expected_sid is not None and sid != expected_sid:
        raise EseeCloudProtocolError("IOTLink SID mismatch")
    return cmd, result, data[32:]


def _receive_p2pk(reader: Reader, sid: int) -> tuple[int, bytes]:
    for _ in range(12):
        packet = _application_reply(reader)
        cmd, result, body = _parse_iot(packet, expected_sid=sid)
        if cmd in (0x13, 0x2B) and body[:4] == b"P2PK":
            return result, body
        if cmd in (0x11, 0x12, 0x13, 0x2B):
            continue
        _LOGGER.debug("Ignoring IOTLink command 0x%02x", cmd)
    raise EseeCloudProtocolError("too many non-P2PK packets")


def _validate_credential(value: str) -> None:
    if len(value) != 32:
        raise ValueError("derived credential must be exactly 32 characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("derived credential must be hexadecimal") from exc


def _p2pk_login(username: str, credential: str) -> tuple[int, bytes]:
    user = username.encode("utf-8")
    secret = credential.encode("ascii")
    if not user or len(user) > 1023:
        raise ValueError("username must contain 1 to 1023 UTF-8 bytes")
    _validate_credential(credential)
    body = user + bytes(1024 - len(user)) + secret + bytes(1024 - len(secret))
    transaction = secrets.randbits(32)
    return transaction, b"P2PK" + struct.pack(
        "<5I", 1, transaction, 0x8C, 0, len(body)
    ) + body


def _p2pk_ptz(action: int, speed: int, marker: int) -> tuple[int, bytes]:
    transaction = secrets.randbits(32)
    body = struct.pack("<4I", 0, action, speed, 0)
    return transaction, b"P2PK" + struct.pack(
        "<5I", 1, transaction, 0x14, marker, len(body)
    ) + body


def _validate_p2pk(
    reply: bytes, transaction: int, expected_command: int
) -> None:
    if len(reply) < 24 or reply[:4] != b"P2PK":
        raise EseeCloudProtocolError("invalid P2PK reply")
    _version, reply_id, command, status, size = struct.unpack("<3IiI", reply[4:24])
    if reply_id != transaction:
        raise EseeCloudProtocolError("P2PK transaction mismatch")
    if size != len(reply) - 24:
        raise EseeCloudProtocolError("P2PK body length mismatch")
    if command != expected_command:
        raise EseeCloudProtocolError(
            f"expected P2PK 0x{expected_command:02x}, received 0x{command:02x}"
        )
    if status != 0:
        if expected_command == 0x8D:
            raise EseeCloudAuthenticationError(f"camera rejected login ({status})")
        raise EseeCloudProtocolError(f"P2PK command failed ({status})")


@dataclass(frozen=True, slots=True)
class CameraConfig:
    """Connection and protocol profile."""

    host: str
    port: int
    uid: int
    username: str
    credential: str
    marker: int
    actions: dict[str, int]
    speed: int = 6


class EseeCloudClient:
    """One-operation-per-connection local camera client."""

    def __init__(self, config: CameraConfig) -> None:
        self.config = config

    def _upgrade(self, sock: socket.socket, reader: Reader) -> None:
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        request = (
            f"GET /index.html HTTP/1.1\r\nHost: {self.config.host}:{self.config.port}\r\n"
            "Connection: Upgrade\r\nUpgrade: websocket\r\n"
            f"Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: {key}\r\n"
            f"Origin: http://{self.config.host}\r\n\r\n"
        )
        sock.sendall(request.encode())
        head = bytearray()
        while not head.endswith(b"\r\n\r\n"):
            if len(head) >= 16384:
                raise EseeCloudProtocolError("HTTP headers exceed limit")
            head.extend(reader.exact(1))
        lines = head.decode("latin1").split("\r\n")
        expected = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
            ).digest()
        ).decode()
        headers = {
            key_.strip().lower(): value.strip()
            for line in lines[1:]
            if ":" in line
            for key_, value in [line.split(":", 1)]
        }
        if (
            len(lines[0].split()) < 2
            or lines[0].split()[1] != "101"
            or headers.get("sec-websocket-accept") != expected
        ):
            raise EseeCloudProtocolError("WebSocket upgrade failed")

    def _open_and_login(self) -> tuple[socket.socket, Reader, int, int]:
        sock = socket.create_connection(
            (self.config.host, self.config.port), timeout=5
        )
        try:
            reader = Reader(sock)
            self._upgrade(sock, reader)
            reader.deadline = time.monotonic() + 8
            _send_binary(
                sock, CLIENT + struct.pack("<I", self.config.uid % 0xFFFFFFFF)
            )
            if _binary_reply(reader) != SERVER:
                raise EseeCloudProtocolError("unexpected ARQ response")
            sid = secrets.randbelow(0x7FFFFFFF) + 1
            open_packet = MAGIC + struct.pack(
                "<7I", 0x14, 0x01000000, 0, sid, 0, 0, 8
            ) + struct.pack("<2I", sid, 2)
            reader.deadline = time.monotonic() + 8
            _send_binary(sock, open_packet)
            _cmd, result, _body = _parse_iot(
                _application_reply(reader), expected_cmd=0x15, expected_sid=sid
            )
            if result != 0:
                raise EseeCloudProtocolError(f"IOTLink OPEN failed ({result})")
            transaction, login = _p2pk_login(
                self.config.username, self.config.credential
            )
            reply = self._send_p2pk(sock, reader, sid, 1, login)
            _validate_p2pk(reply, transaction, 0x8D)
            return sock, reader, sid, 2
        except Exception:
            sock.close()
            raise

    @staticmethod
    def _send_p2pk(
        sock: socket.socket, reader: Reader, sid: int, sequence: int, packet: bytes
    ) -> bytes:
        outer = MAGIC + struct.pack(
            "<7I", 0x2B, 0x01000000, sequence, sid, 0, 0, len(packet)
        ) + packet
        reader.deadline = time.monotonic() + 10
        _send_binary(sock, outer)
        result, reply = _receive_p2pk(reader, sid)
        if result != 0:
            raise EseeCloudProtocolError(f"IOTLink DATA failed ({result})")
        return reply

    @staticmethod
    def _close(sock: socket.socket) -> None:
        try:
            _send_frame(sock, 8, struct.pack(">H", 1000))
        except Exception:  # Best effort only.
            pass
        sock.close()

    def authenticate(self) -> None:
        """Authenticate without sending any PTZ command."""
        sock, _reader, _sid, _sequence = self._open_and_login()
        self._close(sock)

    def move(self, direction: str, duration: float) -> None:
        """Move for a bounded period and always attempt Stop."""
        if direction not in self.config.actions:
            raise ValueError(f"unsupported direction: {direction}")
        if not 0.1 <= duration <= 3.0:
            raise ValueError("duration must be between 0.1 and 3.0 seconds")
        sock, reader, sid, sequence = self._open_and_login()
        moved = False
        stopped = False
        try:
            transaction, packet = _p2pk_ptz(
                self.config.actions[direction], self.config.speed, self.config.marker
            )
            moved = True
            reply = self._send_p2pk(sock, reader, sid, sequence, packet)
            sequence += 1
            _validate_p2pk(reply, transaction, 0x15)
            time.sleep(duration)
            transaction, packet = _p2pk_ptz(0, self.config.speed, self.config.marker)
            reply = self._send_p2pk(sock, reader, sid, sequence, packet)
            sequence += 1
            _validate_p2pk(reply, transaction, 0x15)
            stopped = True
        finally:
            if moved and not stopped:
                try:
                    transaction, packet = _p2pk_ptz(
                        0, self.config.speed, self.config.marker
                    )
                    reply = self._send_p2pk(sock, reader, sid, sequence, packet)
                    _validate_p2pk(reply, transaction, 0x15)
                except Exception:  # Emergency Stop is best effort.
                    _LOGGER.exception("Emergency PTZ Stop was not acknowledged")
            self._close(sock)

