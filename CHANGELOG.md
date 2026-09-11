# Changelog

## 0.1.1 - 2026-09-11

- Send P2PK login and PTZ requests through the verified IOTLink `0x13` DATA
  envelope used by the successful direct-camera probes.
- Retain support for receiving both `0x13` and `0x2B` response envelopes.

## 0.1.0 - 2026-09-11

- Initial HACS-compatible release.
- UI setup with authentication-only validation.
- Multi-camera configuration using camera-specific ESEE UIDs and credentials.
- Four bounded PTZ button entities and `eseecloud_ptz.move` action.
- Physically verified 5323-W6-L2 profile.
- Experimental captured 5323-W6-Q profile.
- Classic-PCAP credential extractor with secrets hidden by default.
