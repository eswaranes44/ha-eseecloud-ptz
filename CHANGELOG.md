# Changelog

## 0.1.4 - 2026-09-11

- Add HACS/Home Assistant brand icon at `brand/icon.png`.
- Mark both tested camera profiles as physically verified for all four PTZ
  directions.
- Expand the feature matrix and document the current light, siren, and
  two-way-audio limitations.
- Document release versioning and validation requirements.

## 0.1.3 - 2026-09-11

- Add an optional Live View camera entity to the same integration.
- Use the configured go2rtc RTSP source so Home Assistant's native go2rtc/WebRTC
  path can render the camera without ONVIF.
- Keep proprietary EseeCloud authentication and PTZ control unchanged.
- Allow the go2rtc source URL to be changed from the integration options.

## 0.1.2 - 2026-09-11

- Restore the verified IOTLink `0x2B` DATA request envelope used by the
  successful long-login and PTZ probes.
- Document that the earlier authentication failure was caused by credentials
  being assigned to the wrong camera UID.

## 0.1.1 - 2026-09-11

- Superseded: incorrectly changed the request envelope to `0x13` while
  investigating an authentication failure.

## 0.1.0 - 2026-09-11

- Initial HACS-compatible release.
- UI setup with authentication-only validation.
- Multi-camera configuration using camera-specific ESEE UIDs and credentials.
- Four bounded PTZ button entities and `eseecloud_ptz.move` action.
- Physically verified 5323-W6-L2 profile.
- Experimental captured 5323-W6-Q profile.
- Classic-PCAP credential extractor with secrets hidden by default.
