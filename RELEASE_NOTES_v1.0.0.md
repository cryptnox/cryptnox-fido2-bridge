# Release v1.0.0

**First release** of Cryptnox FIDO2 Bridge - rebranded and enhanced version of fido2-hid-bridge.

## Added

- **Cryptnox branding** and identity throughout the project
- New systemd service file (`cryptnox-fido2-bridge.service`)
- Enhanced startup information display
- Comprehensive README with Cryptnox-specific documentation
- Updated package metadata and project information
- Command-line options:
  - `--version` flag to display version information
  - `--quiet` / `-q` flag to suppress startup info output

## Changed

- **Rebranded** from `fido2-hid-bridge` to `cryptnox-fido2-bridge`
- Updated package name in `pyproject.toml`
- Simplified and improved startup messages
- Enhanced README with Cryptnox-specific installation and usage instructions
- Improved command-line interface help text and descriptions

## Features (Inherited from Base Project)

This release includes all features from the original fido2-hid-bridge:
- Virtual USB-HID device creation using Linux UHID facility
- Full CTAP1 and CTAP2 (FIDO2) protocol support
- PC/SC smartcard integration
- Command-line interface with `--debug` option (inherited from base project)
- Error handling and graceful shutdown
- Connection management and PC/SC context cleanup

## Technical Details

- **Python**: 3.9+
- **Dependencies**: 
  - `fido2` (with PC/SC extras) ^2.0.0
  - `pyscard` >= 2.0.0
  - `uhid` ^0.0.1
- **Platform**: Linux (Ubuntu 20.04+, Debian 11+, or similar)
- **License**: MIT

## Installation

```bash
pip install git+https://github.com/Cryptnox/cryptnox-fido2-bridge.git@v1.0.0
```

## Credits

Based on [fido2-hid-bridge](https://github.com/BryanJacobs/fido2-hid-bridge) by Bryan Jacobs.
