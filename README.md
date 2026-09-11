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

The integration controls PTZ only. Continue using go2rtc for video, for example:

```yaml
streams:
  car_porch_raw:
    - "eseecloud://admin:@192.168.1.123:80/livestream/12"
```

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

Setup performs authentication only; it does not move the camera. Four button
entities are created: Up, Down, Left and Right. Default movement duration is
0.5 seconds and can be changed under the integration's options (0.1-3.0 s).

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
