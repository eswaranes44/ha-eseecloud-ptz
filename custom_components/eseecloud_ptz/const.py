"""Constants for EseeCloud Local PTZ."""

DOMAIN = "eseecloud_ptz"
PLATFORMS = ["button"]

CONF_UID = "uid"
CONF_DERIVED_CREDENTIAL = "derived_credential"
CONF_PROFILE = "profile"
CONF_DURATION = "duration"

DEFAULT_PORT = 10000
DEFAULT_USERNAME = "admin"
DEFAULT_DURATION = 0.5
MIN_DURATION = 0.1
MAX_DURATION = 3.0

PROFILE_W6_L2 = "5323_w6_l2"
PROFILE_W6_Q = "5323_w6_q"

# Both profiles are based on packet captures. W6-L2 directions were physically
# verified on the target camera. W6-Q defaults came from a separate capture and
# should be verified by the user before unattended use.
PROFILES = {
    PROFILE_W6_L2: {
        "marker": 0xB4000074,
        "actions": {"up": 2, "down": 3, "left": 4, "right": 5},
    },
    PROFILE_W6_Q: {
        "marker": 0x73736563,  # little-endian bytes: "cess"
        "actions": {"up": 5, "down": 2, "left": 4, "right": 3},
    },
}

SERVICE_MOVE = "move"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DIRECTION = "direction"
ATTR_DURATION = "duration"

