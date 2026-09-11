#!/usr/bin/env python3
"""Extract P2PK 0x8C login metadata from classic PCAP files.

Secrets are hidden by default. Use --show-secret only on a trusted computer.
The parser supports classic PCAP with Ethernet or raw IPv4 link types.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import socket
import struct
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    sequence: int
    payload: bytes


def _pcap_packets(path: Path):
    data = path.read_bytes()
    if len(data) < 24:
        raise ValueError("file is too short to be a PCAP")
    magics = {
        b"\xd4\xc3\xb2\xa1": ("<", 1_000_000),
        b"\xa1\xb2\xc3\xd4": (">", 1_000_000),
        b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000),
        b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000),
    }
    if data[:4] not in magics:
        raise ValueError("unsupported capture format; export as classic PCAP")
    endian, _resolution = magics[data[:4]]
    link_type = struct.unpack_from(endian + "I", data, 20)[0]
    offset = 24
    while offset + 16 <= len(data):
        _seconds, _fraction, captured, _original = struct.unpack_from(
            endian + "IIII", data, offset
        )
        offset += 16
        packet = data[offset : offset + captured]
        offset += captured
        if len(packet) != captured:
            break
        yield link_type, packet


def _ipv4_packet(link_type: int, packet: bytes) -> bytes | None:
    if link_type == 101:  # DLT_RAW
        return packet if packet and packet[0] >> 4 == 4 else None
    if link_type == 1:  # Ethernet
        if len(packet) < 14:
            return None
        ether_type = struct.unpack("!H", packet[12:14])[0]
        position = 14
        if ether_type == 0x8100 and len(packet) >= 18:
            ether_type = struct.unpack("!H", packet[16:18])[0]
            position = 18
        return packet[position:] if ether_type == 0x0800 else None
    raise ValueError(f"unsupported PCAP link type {link_type}")


def _tcp_segments(path: Path):
    for link_type, packet in _pcap_packets(path):
        ip = _ipv4_packet(link_type, packet)
        if ip is None or len(ip) < 40 or ip[9] != 6:
            continue
        header_length = (ip[0] & 15) * 4
        if header_length < 20 or len(ip) < header_length + 20:
            continue
        source = socket.inet_ntoa(ip[12:16])
        destination = socket.inet_ntoa(ip[16:20])
        source_port, destination_port = struct.unpack(
            "!HH", ip[header_length : header_length + 4]
        )
        sequence = struct.unpack(
            "!I", ip[header_length + 4 : header_length + 8]
        )[0]
        tcp_length = (ip[header_length + 12] >> 4) * 4
        payload = ip[header_length + tcp_length :]
        if payload:
            yield (
                source,
                source_port,
                destination,
                destination_port,
            ), Segment(sequence, payload)


def _reassemble(segments: list[Segment]) -> bytes:
    by_sequence: dict[int, bytes] = {}
    for segment in segments:
        by_sequence.setdefault(segment.sequence, segment.payload)
    if not by_sequence:
        return b""
    first = min(by_sequence)
    end = max(sequence + len(payload) for sequence, payload in by_sequence.items())
    stream = bytearray(end - first)
    present = bytearray(end - first)
    for sequence in sorted(by_sequence):
        start = sequence - first
        for index, value in enumerate(by_sequence[sequence]):
            if not present[start + index]:
                stream[start + index] = value
                present[start + index] = 1
    # Gaps can create false matches, but a complete 2048-byte login body is
    # accepted only if all bytes covering it were captured.
    return bytes(stream)


def extract(path: Path) -> list[dict]:
    flows: dict[tuple, list[Segment]] = defaultdict(list)
    for flow, segment in _tcp_segments(path):
        flows[flow].append(segment)

    results = []
    seen = set()
    for flow, segments in flows.items():
        stream = _reassemble(segments)
        position = 0
        while True:
            position = stream.find(b"P2PK", position)
            if position < 0:
                break
            if position + 24 > len(stream):
                break
            version, transaction, command, status, size = struct.unpack_from(
                "<3IiI", stream, position + 4
            )
            if command == 0x8C and size == 2048 and position + 24 + size <= len(stream):
                body = stream[position + 24 : position + 24 + size]
                username = body[:1024].split(b"\0", 1)[0].decode("utf-8", "replace")
                credential = body[1024:].split(b"\0", 1)[0].decode("ascii", "replace")
                if len(credential) == 32:
                    identity = (flow, username, credential)
                    if identity not in seen:
                        seen.add(identity)
                        results.append(
                            {
                                "flow": flow,
                                "version": version,
                                "transaction": transaction,
                                "status_field": status,
                                "username": username,
                                "credential": credential,
                                "fingerprint": hashlib.sha256(
                                    credential.encode("ascii")
                                ).hexdigest()[:12],
                            }
                        )
            position += 4
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcap", type=Path)
    parser.add_argument(
        "--show-secret",
        action="store_true",
        help="print the full credential (treat output as sensitive)",
    )
    args = parser.parse_args()
    try:
        results = extract(args.pcap)
    except (OSError, ValueError, struct.error) as exc:
        print(f"ERROR: {exc}")
        return 1
    if not results:
        print("No complete P2PK 0x8C login was found.")
        return 2
    for index, result in enumerate(results, 1):
        source, source_port, destination, destination_port = result["flow"]
        print(f"Login {index}")
        print(f"  Flow: {source}:{source_port} -> {destination}:{destination_port}")
        print(f"  Username: {result['username']}")
        print(f"  Credential SHA-256 fingerprint: {result['fingerprint']}")
        if args.show_secret:
            print(f"  Derived credential: {result['credential']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

