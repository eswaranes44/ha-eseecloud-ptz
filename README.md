# EseeCloud Local PTZ for Home Assistant

Local PTZ control for selected EseeCloud/Juan cameras using the proprietary
WebSocket, ARQ, IOTLink and P2PK protocol on TCP port 10000. No EseeCloud cloud
connection is required for movement.

> Experimental reverse-engineered integration. Keep physical access to the
> camera during initial testing. A Stop command is sent after every bounded
> movement and attempted again if the normal movement sequence fails.

## Verified hardware

| Profile | Model | Authentication | Direction mapping |
| --- | --- | --- | --- |
| `5323_w6_l2` | 5323-W6-L2 | Verified | Physically verified |
| `5323_w6_q` | 5323-W6-Q | Verified | Captured; verify physically before unattended use |

The integration now creates the PTZ controls and, optionally, a **Live View**
camera entity in the same Home Assistant device. The Live View uses your
existing go2rtc RTSP stream; no ONVIF support is required.

## go2rtc/WebRTC Live View

The verified media route is:

```text
camera /livestream/12 -> go2rtc on Synology -> Home Assistant WebRTC
```

Your existing go2rtc source can remain on the Synology host:

```yaml
streams:
  eseecloud_camera:
    - "eseecloud://admin:YOUR_URL_ENCODED_CREDENTIAL@<camera-ip>:80/livestream/12"
```

If Home Assistant is using its built-in go2rtc integration, point it to the
go2rtc API on the Synology host:

```yaml
go2rtc:
  url: http://<go2rtc-host>:1984
```

When adding this EseeCloud device, enter the RTSP output of that go2rtc stream:

```text
rtsp://<go2rtc-host>:8554/eseecloud_camera
```

After restarting Home Assistant, the same EseeCloud device will contain:

- Live View camera entity
- Up, Down, Left and Right PTZ buttons
- `eseecloud_ptz.move` action

Home Assistant's go2rtc integration can provide the WebRTC proxy for camera
stream sources. The camera entity also retains the RTSP source for fallback and
recording through the normal stream integration.

Do not put the real credential in GitHub, screenshots, or public YAML. The
configuration-flow field is stored in Home Assistant's local config entry.

The old standalone arrangement is still supported: leave the go2rtc field
empty and the integration will create PTZ entities only.

## Installation

### HACS custom repository

1. Publish this folder as a GitHub repository.
2. In HACS, open **Custom repositories**.
3. Add the repository URL with category **Integration**.
4. Install **EseeCloud Local PTZ**.
5. Restart Home Assistant.

### Manual

Copy `custom_components/eseecloud_ptz` to:

```text
/config/custom_components/eseecloud_ptz
```

Restart Home Assistant.

## Add a camera

Open **Settings -> Devices & services -> Add integration**, search for
**EseeCloud Local PTZ**, then enter:

- A descriptive camera name
- Local camera IP address
- Control port (normally `10000`)
- Numeric ESEE UID
- Camera username
- The camera-specific 32-character derived credential
- The matching protocol profile
- Optional go2rtc RTSP stream URL, for example:
  `rtsp://<go2rtc-host>:8554/eseecloud_camera`

Setup performs authentication only; it does not move the camera. Four button
entities are created: Up, Down, Left and Right. Default movement duration is
0.5 seconds and can be changed under the integration's options (0.1-3.0 s).
The go2rtc stream URL can also be changed under the integration options.

## Action

The integration registers `eseecloud_ptz.move`:

```yaml
action: eseecloud_ptz.move
data:
  config_entry_id: "CONFIG_ENTRY_ID"
  direction: left
  duration: 0.5
```

Prefer the four generated button entities for normal dashboards.

## Extracting a derived credential

Nmap cannot retrieve the credential. Capture the EseeCloud Android app with
PCAPdroid while it opens the target camera, export classic PCAP, and run:

```bash
python3 tools/extract_eseecloud_credentials.py capture.pcap
```

The default output shows only a fingerprint. On a trusted computer, explicitly
request the full value:

```bash
python3 tools/extract_eseecloud_credentials.py capture.pcap --show-secret
```

PCAPs containing P2PK `0x8C` logins are sensitive and must be protected like
password files.

## Security notes

- The derived credential is unique per tested camera and is password-equivalent.
- Home Assistant stores config-entry data locally; protect `/config/.storage`
  and backups.
- Credentials are never written to integration logs or diagnostics.
- Use this integration only with cameras you own or are authorized to manage.
- Keep camera control networks private and firewall TCP port 10000 from the
  internet.

## Protocol status

Verified local chain:

```text
TCP 10000 -> WebSocket -> ARQ -> IOTLink OPEN -> P2PK 0x8C login
         -> P2PK 0x14 movement -> P2PK 0x14 Stop
```

Known acknowledgement commands are `0x8D` for login and `0x15` for PTZ.
