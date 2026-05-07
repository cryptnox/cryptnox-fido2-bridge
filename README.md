<p align="center">
  <img src="https://github.com/user-attachments/assets/6ce54a27-8fb6-48e6-9d1f-da144f43425a"/>
</p>

<h3 align="center">cryptnox-fido2-bridge</h3>
<p align="center">Linux HID to PC/SC bridge for FIDO2 smart cards</p>

<br/>
<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

`cryptnox-fido2-bridge` is a Linux-only Python bridge that creates a virtual USB-HID device, enabling browsers to use FIDO2 smart cards for **WebAuthn/FIDO2** authentication. It translates CTAP2 commands from the browser into PC/SC APDUs for the card.

---

## Supported hardware

### Smart cards

Works with Cryptnox smart cards and any other FIDO2-capable smart card over PC/SC.

| Smart card | Interface |
|------|-----------|
| [Crypto Hardware Wallet – Dual Card Set](https://shop.cryptnox.com/product/hardware-wallet-smartcard-dual/) | NFC + Contact |
| [Cryptnox FIDO2 Security Key & MIFARE DESFire](https://shop.cryptnox.com/product/cryptnox-smartcard-fido2/) | NFC + Contact |

### Smart card readers

Works with Cryptnox readers and any other standard PC/SC smart card reader:

| Reader | Type | Interface |
|--------|------|-----------|
| [Cryptnox® Smartcard Reader](https://shop.cryptnox.com/product/cryptnox-smartcard-reader/) | Contact (ID-1 + SIM) | USB-A |
| [Compact USB Mini Smartcard Reader](https://shop.cryptnox.com/product/mini-smartcard-reader/) | Contact (ID-1) | USB-A |
| [Cryptnox NFC Contactless Reader](https://shop.cryptnox.com/product/cryptnox-contactless-reader/) | Contactless (NFC/ISO 14443) | USB-C |

---

## How it works

```
┌──────────────┐     USB-HID      ┌────────────────────────┐     PC/SC     ┌─────────────┐
│   Browser    │ ◄──────────────► │  Cryptnox FIDO2 Bridge │ ◄────────────►│  Smart Card │
│   (Chrome)   │                  │    (Virtual Device)    │               │             │
└──────────────┘                  └────────────────────────┘               └─────────────┘
```

1. The bridge creates a **virtual USB-HID device** using Linux's UHID facility
2. When a browser sends a **FIDO2/CTAP2 command** via USB-HID
3. The bridge **translates** it to **PC/SC APDUs**
4. Commands are sent to your **smart card** via the card reader
5. Responses are **translated back** and sent to the browser

This enables using PC/SC smartcards in browsers that only support USB-HID authenticators.

---

## Installation

> [!IMPORTANT]
> This bridge requires **Linux** (Ubuntu 22.04+, Debian 12+, or similar) with **Python 3.12 or newer** in the 3.x line (`^3.12` in `pyproject.toml`; `.python-version` pins **3.12** for local development).

### From source

```bash
# Install dependencies
sudo apt update
sudo apt install -y pcscd pcsc-tools libpcsclite-dev swig python3.12-venv python3.12-dev build-essential libffi-dev
sudo systemctl enable --now pcscd

# Clone and install
git clone https://github.com/Cryptnox/cryptnox-fido2-bridge.git
cd cryptnox-fido2-bridge
pip install poetry
poetry install

# Run
sudo -E poetry run cryptnox-fido2-bridge
```

### Using pipx

```bash
# Install dependencies
sudo apt update
sudo apt install -y pcscd pcsc-tools libpcsclite-dev swig pipx python3.12-dev build-essential libffi-dev
sudo systemctl enable --now pcscd

# Install the bridge
pipx install git+https://github.com/Cryptnox/cryptnox-fido2-bridge.git

# Run (use full path or add ~/.local/bin to PATH)
sudo -E ~/.local/bin/cryptnox-fido2-bridge
```

### Using virtual environment

```bash
# Install dependencies
sudo apt update
sudo apt install -y pcscd pcsc-tools libpcsclite-dev swig python3.12-venv python3.12-dev build-essential libffi-dev
sudo systemctl enable --now pcscd

# Create and activate virtual environment (use 3.12 to match this repo)
python3.12 -m venv venv
source venv/bin/activate

# Install the bridge
pip install git+https://github.com/Cryptnox/cryptnox-fido2-bridge.git

# Run
sudo -E cryptnox-fido2-bridge
```

---

## Quick usage examples

> [!TIP]
> Supported browsers: **Chrome** (recommended), Chromium. Firefox and Brave have limited support due to stricter security policies.

### 1. Basic usage

1. **Connect** your smartcard reader to your computer
2. **Insert** your card (or place on NFC reader)
3. **Run** the bridge:
   ```bash
   sudo -E cryptnox-fido2-bridge
   ```
4. **Open Chrome** and navigate to a WebAuthn site:
   - https://webauthn.io/ (test site)
   - https://demo.yubico.com/webauthn-technical/registration
5. **Register** or **Authenticate** - the bridge will communicate with your card!

### 2. Command line options

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

---

## Troubleshooting

### Command not found with pipx and sudo

If you installed with `pipx` and get a "command not found" error when running with `sudo`, the system cannot find the binary in the root PATH:

```bash
# Use the full path
sudo -E ~/.local/bin/cryptnox-fido2-bridge

# Or add ~/.local/bin to your PATH (add to ~/.bashrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Command not found with Poetry and sudo

`sudo` resets `PATH`, so `poetry` is often missing. Use the full path or preserve `PATH`:

```bash
sudo -E ~/.local/bin/poetry run cryptnox-fido2-bridge

# Or
sudo -E env "PATH=$PATH" poetry run cryptnox-fido2-bridge
```

### Permission denied on /dev/uhid

If you get a permission error when running the bridge, the current user does not have access to the UHID device. You can fix this temporarily or permanently:

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

If the bridge cannot find your card, `pcscd` may not be running or the reader is not properly recognized:

```bash
# Check if pcscd is running
sudo systemctl status pcscd

# Restart pcscd
sudo systemctl restart pcscd

# Test card detection
pcsc_scan
```

### CryptnoxCR reader and CCID (PC/SC)

The **CryptnoxCR** USB contact reader (`0x05F8:0x0018`) is listed in upstream **CCID** from **[version 1.7.1](https://github.com/LudovicRousseau/CCID/releases/tag/1.7.1)** onward. That driver is what `pcscd` uses (via the `libccid` / `ifd-ccid` bundle on Debian and Ubuntu).

**What to do:**

1. Prefer **upgrading `libccid`** (and restarting `pcscd`) so `pcsc_scan` shows the reader without editing system files. Check your package version, for example:

   ```bash
   dpkg -s libccid | grep ^Version:
   ```

2. If your distribution still ships **CCID older than 1.7.1** and the reader never appears in `pcsc_scan`, either wait for a distro update or add the device to the CCID `Info.plist` (back up the file first), then restart `pcscd`:

   ```bash
   sudo cp /usr/lib/pcsc/drivers/ifd-ccid.bundle/Contents/Info.plist /usr/lib/pcsc/drivers/ifd-ccid.bundle/Contents/Info.plist.backup
   sudo sed -i -e '/<key>ifdVendorID<\/key>/,/<\/array>/{/<array>/a\		<string>0x05F8</string>
   }' -e '/<key>ifdProductID<\/key>/,/<\/array>/{/<array>/a\		<string>0x0018</string>
   }' -e '/<key>ifdFriendlyName<\/key>/,/<\/array>/{/<array>/a\		<string>CryptnoxCR Contact Reader</string>
   }' /usr/lib/pcsc/drivers/ifd-ccid.bundle/Contents/Info.plist && sudo systemctl restart pcscd.socket pcscd && pcsc_scan
   ```

`pcsc_scan` itself is only a **test tool** from `pcsc-tools`; it does not ship reader definitions. Seeing **CryptnoxCR** there means `pcscd` + CCID already know the device.

---

## Security notes

- The bridge runs locally and does not transmit data over the network
- Private keys never leave your smart card
- The virtual HID device is only accessible locally

---

## Credits

Based on [fido2-hid-bridge](https://github.com/BryanJacobs/fido2-hid-bridge) by Bryan Jacobs.

---

## License

- Based on MIT-licensed code originally by Bryan Jacobs on the [fido2-hid-bridge](https://github.com/BryanJacobs/fido2-hid-bridge) repo.
- MIT License - see [LICENSE](LICENSE) file for details.
