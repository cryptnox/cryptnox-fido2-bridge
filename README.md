<p align="center">
  <img src="https://github.com/user-attachments/assets/6ce54a27-8fb6-48e6-9d1f-da144f43425a"/>
</p>

<h3 align="center">cryptnox-fido2-bridge</h3>
<p align="center">Enables **WebAuthn/FIDO2** authentication in browsers using your **Cryptnox smartcard** via PC/SC interface</p>

<br/>
<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## How It Works

This bridge creates a virtual USB-HID device that translates browser FIDO2 requests to PC/SC commands.

```
┌──────────────┐     USB-HID      ┌────────────────────────┐     PC/SC     ┌─────────────┐
│   Browser    │ ───────────────► │  Cryptnox FIDO2 Bridge │ ────────────► │  Cryptnox   │
│   (Chrome)   │                  │    (Virtual Device)    │               │    Card     │
└──────────────┘                  └────────────────────────┘               └─────────────┘
```

1. The bridge creates a **virtual USB-HID device** using Linux's UHID facility
2. When a browser sends a **FIDO2/CTAP2 command** via USB-HID
3. The bridge **translates** it to **PC/SC APDUs**
4. Commands are sent to your **Cryptnox card** via the card reader
5. Responses are **translated back** and sent to the browser

This enables using PC/SC smartcards (like Cryptnox) in browsers that only support USB-HID authenticators.

## Requirements

- **Linux** (Ubuntu 20.04+, Debian 11+, or similar)
- **Python 3.9+**
- **PC/SC compatible smartcard reader**
- **Cryptnox card** with FIDO2 applet

## Installation

### Option 1: Using pipx (Recommended)

```bash
# Install dependencies and start PC/SC daemon
sudo apt update
sudo apt install -y pcscd pcsc-tools libpcsclite-dev swig pipx python3-dev build-essential
sudo systemctl enable --now pcscd

# Install the bridge using pipx
pipx install git+https://github.com/Cryptnox/cryptnox-fido2-bridge.git

# Run (use full path or add ~/.local/bin to PATH)
sudo -E ~/.local/bin/cryptnox-fido2-bridge
```

### Option 2: Using Virtual Environment

```bash
# Install dependencies and start PC/SC daemon
sudo apt update
sudo apt install -y pcscd pcsc-tools libpcsclite-dev swig python3-venv python3-dev build-essential
sudo systemctl enable --now pcscd

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the bridge
pip install git+https://github.com/Cryptnox/cryptnox-fido2-bridge.git

# Run
sudo -E cryptnox-fido2-bridge
```

### Option 3: Install from Source (Development)

```bash
# Install dependencies
sudo apt update
sudo apt install -y pcscd pcsc-tools libpcsclite-dev swig python3-venv python3-dev build-essential
sudo systemctl enable --now pcscd

# Clone and install
git clone https://github.com/Cryptnox/cryptnox-fido2-bridge.git
cd cryptnox-fido2-bridge
pip install poetry
poetry install

# Run
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

### Command not found with pipx and sudo

If you installed with `pipx` and get "command not found" when using `sudo`:

```bash
# Use the full path
sudo -E ~/.local/bin/cryptnox-fido2-bridge

# Or add ~/.local/bin to your PATH (add to ~/.bashrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

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

## CryptnoxCR reader not recognized

If pcsc_scan doesn't detect your CryptnoxCR contact reader (shows "Waiting for the first reader..."), add it to the CCID driver:

```bash
sudo sed -i -e '/<key>ifdVendorID<\/key>/,/<\/array>/{/<array>/a\    <string>0x05F8</string>
}' -e '/<key>ifdProductID<\/key>/,/<\/array>/{/<array>/a\    <string>0x0018</string>
}' -e '/<key>ifdFriendlyName<\/key>/,/<\/array>/{/<array>/a\    <string>CryptnoxCR Contact Reader</string>
}' /usr/lib/pcsc/drivers/ifd-ccid.bundle/Contents/Info.plist && sudo systemctl restart pcscd.socket pcscd && pcsc_scan
```

## Security Notes

- The bridge runs locally and does not transmit data over the network
- Private keys never leave your Cryptnox card
- The virtual HID device is only accessible locally

## Credits

Based on [fido2-hid-bridge](https://github.com/BryanJacobs/fido2-hid-bridge) by Bryan Jacobs.

## License

- Based on MIT-licensed code originally by Bryan Jacobs on the [fido2-hid-bridge](https://github.com/BryanJacobs/fido2-hid-bridge) repo.
- MIT License - see [LICENSE](LICENSE) file for details.
