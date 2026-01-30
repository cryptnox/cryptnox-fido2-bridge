#!/usr/bin/env python3
"""
Cryptnox FIDO2 Bridge
=====================
Bridges PC/SC smartcards to USB-HID for WebAuthn/FIDO2 support in browsers.

Copyright (c) 2024 Cryptnox SA
Based on fido2-hid-bridge by Bryan Jacobs
License: MIT
"""

import asyncio
import logging
import argparse
import signal
import sys

from fido2_hid_bridge.ctap_hid_device import CTAPHIDDevice

__version__ = "1.0.0"

STARTUP_INFO = """
Cryptnox FIDO2 Bridge v{version}

Enables WebAuthn/FIDO2 authentication in browsers using
your Cryptnox smartcard via PC/SC interface.

Based on fido2-hid-bridge by Bryan Jacobs
Supported browsers: Chrome, Chromium
Press Ctrl+C to stop
""".format(version=__version__)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n")
    logging.info("Shutting down Cryptnox FIDO2 Bridge...")
    sys.exit(0)


async def run_device() -> None:
    """Asynchronously run the event loop."""
    device = CTAPHIDDevice()
    await device.start()


def main():
    """Main entry point for Cryptnox FIDO2 Bridge."""
    parser = argparse.ArgumentParser(
        description='Cryptnox FIDO2 Bridge - Relay USB-HID packets to PC/SC smartcard',
        allow_abbrev=False
    )
    parser.add_argument(
        '--debug', 
        action='store_const', 
        const=logging.DEBUG, 
        default=logging.INFO,
        help='Enable debug messages'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'Cryptnox FIDO2 Bridge v{__version__}'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress startup info output'
    )
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=args.debug,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Show startup info
    if not args.quiet:
        print(STARTUP_INFO)
    
    logging.info("Starting Cryptnox FIDO2 Bridge...")
    logging.info("Waiting for Cryptnox card...")
    logging.info("Open Chrome and navigate to a WebAuthn site (e.g., https://webauthn.io/)")
    
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_device())
        loop.run_forever()
    except PermissionError:
        logging.error("Permission denied accessing /dev/uhid")
        logging.error("Try running with: sudo -E cryptnox-fido2-bridge")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error: {e}")
        if args.debug == logging.DEBUG:
            raise
        sys.exit(1)

