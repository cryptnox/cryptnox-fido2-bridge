# Cryptnox FIDO2 Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Enables **WebAuthn/FIDO2** authentication in browsers using your **Cryptnox smartcard** via PC/SC interface.

## What It Does

This bridge creates a virtual USB-HID device that translates browser FIDO2 requests to PC/SC commands.

```
┌──────────────┐     USB-HID      ┌────────────────────────┐     PC/SC     ┌─────────────┐
│   Browser    │ ───────────────► │  Cryptnox FIDO2 Bridge │ ────────────► │  Cryptnox   │
│   (Chrome)   │                  │    (Virtual Device)    │               │    Card     │
└──────────────┘                  └────────────────────────┘               └─────────────┘
```

## Requirements

- **Linux** (Ubuntu 20.04+, Debian 11+, or similar)
- **Python 3.9+**
- **PC/SC compatible smartcard reader**
- **Cryptnox card** with FIDO2 applet

## Installation

```bash
# Install dependencies and start PC/SC daemon
sudo apt update
sudo apt install -y pcscd pcsc-tools libpcsclite-dev swig
sudo systemctl enable --now pcscd

# Install the bridge
pip install git+https://github.com/Cryptnox/cryptnox-fido2-bridge.git

# Run
sudo -E cryptnox-fido2-bridge
```

<b>Alternative: Install from source</b>

```bash
git clone https://github.com/Cryptnox/cryptnox-fido2-bridge.git
cd cryptnox-fido2-bridge
pip install poetry
poetry install
sudo -E poetry run cryptnox-fido2-bridge
```

## Usage

1. **Connect** your smartcard reader to your computer
2. **Insert** your Cryptnox card (or place on NFC reader)
3. **Run** the bridge:
   ```bash
   sudo -E cryptnox-fido2-bridge
   ```
4. **Open Chrome** and navigate to a WebAuthn site:
   - https://webauthn.io/ (test site)
   - https://demo.yubico.com/webauthn-technical/registration
5. **Register** or **Authenticate** - the bridge will communicate with your card!

### Command Line Options

```bash
# Show help
cryptnox-fido2-bridge --help

# Enable debug logging
sudo -E cryptnox-fido2-bridge --debug

# Quiet mode (no banner)
sudo -E cryptnox-fido2-bridge --quiet

# Show version
cryptnox-fido2-bridge --version
```

## Browser Compatibility

| Browser | Status | Notes |
|---------|--------|-------|
| **Chrome** | ✅ Works | Recommended |
| **Brave** | ⚠️ Limited | May block virtual HID |
| **Firefox** | ⚠️ Limited | Stricter security policy |

## Troubleshooting

### Permission denied on /dev/uhid

```bash
# Fix permissions
sudo chmod 666 /dev/uhid

# Or create udev rule (permanent fix)
sudo tee /etc/udev/rules.d/70-cryptnox-fido2.rules << 'EOF'
KERNEL=="uhid", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Card not detected

```bash
# Check if pcscd is running
sudo systemctl status pcscd

# Restart pcscd
sudo systemctl restart pcscd

# Test card detection
pcsc_scan
```

## How It Works

1. The bridge creates a **virtual USB-HID device** using Linux's UHID facility
2. When a browser sends a **FIDO2/CTAP2 command** via USB-HID
3. The bridge **translates** it to **PC/SC APDUs**
4. Commands are sent to your **Cryptnox card** via the card reader
5. Responses are **translated back** and sent to the browser

This enables using PC/SC smartcards (like Cryptnox) in browsers that only support USB-HID authenticators.

## Security Notes

- The bridge runs locally and does not transmit data over the network
- Private keys never leave your Cryptnox card
- The virtual HID device is only accessible locally

## Credits

Based on [fido2-hid-bridge](https://github.com/BryanJacobs/fido2-hid-bridge) by Bryan Jacobs.

## License

- Based on MIT-licensed code originally by Bryan Jacobs on the [fido2-hid-bridge](https://github.com/BryanJacobs/fido2-hid-bridge) repo.
- MIT License - see [LICENSE](LICENSE) file for details.
