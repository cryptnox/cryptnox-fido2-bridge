"""
Cryptnox FIDO2 Bridge
=====================

A bridge that enables WebAuthn/FIDO2 authentication in browsers
using Cryptnox smartcards via PC/SC interface.

This package creates a virtual USB-HID device that translates
browser FIDO2 requests to PC/SC commands for your Cryptnox card.

Usage:
    sudo cryptnox-fido2-bridge

Then open Chrome and navigate to a WebAuthn-enabled site.

Copyright (c) 2026 Cryptnox SA
Based on fido2-hid-bridge by Bryan Jacobs
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Cryptnox SA"
__email__ = "support@cryptnox.com"
__license__ = "MIT"

from .bridge import main
from .ctap_hid_device import CTAPHIDDevice

__all__ = ["main", "CTAPHIDDevice", "__version__"]
