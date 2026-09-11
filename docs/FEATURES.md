# Feature and protocol status

This project targets selected EseeCloud/Juan Wi-Fi PTZ cameras that do not
provide ONVIF. It uses the camera's local proprietary protocol for login and
PTZ control, and uses go2rtc for the media path.

## Current compatibility

| Capability | Availability | Verification |
| --- | --- | --- |
| Local device login | Available | P2PK login accepted with a device-specific derived credential. |
| Live camera view | Available | Camera `/livestream/12` is supplied to go2rtc as an RTSP source. |
| WebRTC in Home Assistant | Available | Home Assistant's go2rtc integration proxies the configured stream. |
| PTZ up, down, left, right | Available | Physically tested on `5323-W6-L2` and `5323-W6-Q`. |
| Stop after movement | Available | Sent after every bounded movement and retried on the failure path. |
| Camera light | Planned | Proprietary command not yet captured and verified. |
| Siren | Planned | Proprietary command not yet captured and verified. |
| Two-way audio | Planned | Audio transport, codec, and half/full-duplex behavior not yet verified. |
| NVR pairing | Not required | Direct local camera control works without an NVR or ONVIF. |

## Media path

The integration does not implement a second video decoder. It exposes the
configured RTSP URL as a Home Assistant camera entity, allowing the existing
go2rtc service to provide MSE/WebRTC playback:

```text
EseeCloud /livestream/12 -> go2rtc -> Home Assistant WebRTC -> dashboard
```

This keeps the proprietary control protocol separate from the media relay and
avoids requiring ONVIF.

## Planned protocol work

Light, siren, and audio support require captures from an authorized app session
while each feature is used. Each command must be identified by camera UID,
firmware, request envelope, acknowledgement, and safe timeout behavior before
it is added to the integration. A feature is not considered supported merely
because a button appears in the vendor application.

When implementing a new command:

1. Capture one feature action and its acknowledgement.
2. Reassemble and document the full request and response layout.
3. Add a protocol unit test without real credentials or PCAP files.
4. Add a bounded Home Assistant service with a safe default timeout.
5. Test on both verified camera profiles before changing the feature table.

## Security boundaries

- Never commit derived credentials, PCAP files, real LAN addresses, or source
  URLs containing credentials.
- Keep camera TCP port `10000` private and do not expose it to the internet.
- Treat the derived credential as a password-equivalent secret.
- Do not add unverified light, siren, or audio commands to production entities.
