import logging
import threading
import time
from enum import IntEnum
from random import randint
from typing import Optional, Callable, Dict, Tuple, List

from uhid import UHIDDevice, _ReportType, AsyncioBlockingUHID, Bus
import fido2
from fido2.pcsc import CtapDevice, CTAPHID, CtapError, CtapPcscDevice
try:
    from smartcard.pcsc.PCSCContext import PCSCContext
except:
    PCSCContext = None
from smartcard.scard import (
    SCardReleaseContext,
    SCardEstablishContext as _SCardEstablishContext,
    SCardListReaders as _SCardListReaders,
    SCardGetStatusChange as _SCardGetStatusChange,
    SCARD_SCOPE_USER as _SCARD_SCOPE_USER,
    SCARD_STATE_UNAWARE as _SCARD_STATE_UNAWARE,
    SCARD_STATE_PRESENT as _SCARD_STATE_PRESENT,
)

SECONDS_TO_WAIT_FOR_AUTHENTICATOR = 30
"""How long, in seconds, to poll for a USB authenticator before giving up."""
VID = 0x9999
"""USB vendor ID (virtual device)."""
PID = 0x9999
"""USB product ID (virtual device)."""
DEVICE_NAME = "Cryptnox FIDO2 Virtual Device"
"""Name of the virtual HID device."""

BROADCAST_CHANNEL = bytes([0xFF, 0xFF, 0xFF, 0xFF])
"""Standard CTAP-HID broadcast channel."""


class CommandType(IntEnum):
    """Catalog of CTAP-HID command type bytes."""

    PING = 0x01
    MSG = 0x03
    INIT = 0x06
    WINK = 0x08
    CBOR = 0x10
    CANCEL = 0x11
    KEEPALIVE = 0x3B
    ERROR = 0x3F


def _wrap_call_with_device_obj(
    device: UHIDDevice, call: Callable[[UHIDDevice, List[int], _ReportType], None]
) -> Callable:
    """Pass a UHIDDevice to a given callback."""
    return lambda x, y: call(device, x, y)


class CTAPHIDDevice:
    device: UHIDDevice
    """Underlying UHID device."""
    chosen_device: Optional[CtapDevice] = None
    """Mapping from channel strings to CTAP devices."""
    channels_to_state: Dict[str, Tuple[CommandType, int, int, bytes]] = {}
    """
    Mapping from channel strings to receive buffer state.

    Each value consists of:
    1. The command type in use on the channel
    2. The total length of the incoming request
    3. The sequence number of the most recently received packet (-1 for initial)
    4. The accumulated data received on the channel
    """
    reference_count = 0
    """Number of open handles to the device: clear state when it hits zero."""

    def __init__(self, require_up: bool = True):
        self.require_up = require_up
        self._up_confirmed: bool = False
        self.device = UHIDDevice(
            vid=VID,
            pid=PID,
            name=DEVICE_NAME,
            report_descriptor=[
                0x06,
                0xD0,
                0xF1,  # Usage Page (FIDO)
                0x09,
                0x01,  # Usage (CTAPHID)
                0xA1,
                0x01,  # Collection (Application)
                0x09,
                0x20,  # Usage (Data In)
                0x15,
                0x00,  # Logical min (0)
                0x26,
                0xFF,
                0x00,  # Logical max (255)
                0x75,
                0x08,  # Report Size (8)
                0x95,
                0x40,  # Report count (64 bytes per packet)
                0x81,
                0x02,  # Input(HID_Data | HID_Absolute | HID_Variable)
                0x09,
                0x21,  # Usage (Data Out)
                0x15,
                0x00,  # Logical min (0)
                0x26,
                0xFF,
                0x00,  # Logical max (255)
                0x75,
                0x08,  # Report Size (8)
                0x95,
                0x40,  # Report count (64 bytes per packet)
                0x91,
                0x02,  # Output(HID_Data | HID_Absolute | HID_Variable)
                0xC0,  # End Collection
            ],
            backend=AsyncioBlockingUHID,
            version=0,
            bus=Bus.USB,
        )

        self.device.receive_output = self.process_hid_message
        self.device.receive_close = self.process_close
        self.device.receive_open = self.process_open

    def _close_pcsc_connection(self):
        """Close the PCSC connection if it exists."""
        if self.chosen_device is not None:
            try:
                # Close the device connection
                if hasattr(self.chosen_device, 'close'):
                    logging.info("CLOSED DEVICE CONNECTION")
                    self.chosen_device.close()

                # Release the PCSC context handle (actually closes the socket)
                if PCSCContext is not None and PCSCContext.instance is not None:
                    ctx = PCSCContext.instance
                    if hasattr(ctx, 'hcontext') and ctx.hcontext is not None:
                        SCardReleaseContext(ctx.hcontext)
                        ctx.hcontext = None
                    PCSCContext.instance = None
                    logging.info("CLOSED PCSC CONNECTION")

            except Exception as e:
                logging.warning(f"Failed to close PCSC connection: {e}")
            finally:
                self.chosen_device = None

    def process_open(self):
        self.reference_count += 1

    def process_close(self):
        self.reference_count -= 1
        if self.reference_count == 0:
            # Clear all state
            self.channels_to_state = {}
            self._up_confirmed = False
            self._close_pcsc_connection()

    def process_hid_message(self, buffer: List[int], report_type: _ReportType) -> None:
        """Core method: handle incoming HID messages."""
        recvd_bytes = bytes(buffer)
        logging.debug(f"GOT MESSAGE (type {report_type}): {recvd_bytes.hex()}")

        if self.is_initial_packet(recvd_bytes):
            channel, lc, cmd, data = self.parse_initial_packet(recvd_bytes)
            channel_key = self.get_channel_key(channel)
            logging.debug(
                f"CMD {cmd.name} CHANNEL {channel_key} len {lc} (recvd {len(data)}) data {data.hex()}"
            )
            self.channels_to_state[channel_key] = cmd, lc, -1, data
            if lc == len(data):
                # Complete receive
                self.finish_receiving(channel)
        else:
            channel, seq, new_data = self.parse_subsequent_packet(recvd_bytes)
            channel_key = self.get_channel_key(channel)
            if channel_key not in self.channels_to_state:
                self.send_error(channel, 0x0B)
                return
            cmd, lc, prev_seq, existing_data = self.channels_to_state[channel_key]
            if seq != prev_seq + 1:
                self.handle_cancel(channel, b"")
                self.send_error(channel, 0x04)
                return
            remaining = lc - len(existing_data)
            data = existing_data + new_data[:remaining]
            self.channels_to_state[channel_key] = cmd, lc, seq, data
            logging.debug(f"After receive, we have {len(data)} bytes out of {lc}")
            if lc == len(data):
                self.finish_receiving(channel)

    async def start(self):
        await self.device.wait_for_start_asyncio()

    def parse_initial_packet(
        self, buffer: bytes
    ) -> Tuple[bytes, int, CommandType, bytes]:
        """Parse an incoming initial packet."""
        logging.debug(f"Initial packet {buffer.hex()}")
        channel = buffer[1:5]
        cmd_byte = buffer[5] & 0x7F
        lc = (int(buffer[6]) << 8) + buffer[7]
        data = buffer[8 : 8 + lc]
        cmd = CommandType(cmd_byte)
        return channel, lc, cmd, data

    def is_initial_packet(self, buffer: bytes) -> bool:
        """Return true if packet is the start of a new sequence."""
        if buffer[5] & 0x80 == 0:
            return False
        return True

    def assign_channel_id(self) -> List[int]:
        """Create a new, random, channel ID."""
        return [randint(0, 255), randint(0, 255), randint(0, 255), randint(0, 255)]

    def handle_init(self, channel: bytes, buffer: bytes) -> Optional[bytes]:
        """Initialize or re-initialize a channel."""
        logging.debug(f"INIT on channel {channel}")

        if channel == BROADCAST_CHANNEL:
            assert len(buffer) == 8

            new_channel = self.assign_channel_id()

            ctap = self.get_pcsc_device(new_channel)
            if ctap is None:
                return None

            return bytes(
                [x for x in buffer]
                + [x for x in new_channel]
                + [
                    0x02,  # protocol version
                    0x01,  # device version major
                    0x00,  # device version minor
                    0x00,  # device version build/point
                    ctap.capabilities,  # capabilities, from the underlying device
                ]
            )
        else:
            self.handle_cancel(channel, b"")

    def get_pcsc_device(self, channel_id: List[int]) -> Optional[CtapDevice]:
        """Grab a PC/SC device from python-fido2."""
        if self.chosen_device is None:
            start_time = time.time()
            while time.time() < start_time + SECONDS_TO_WAIT_FOR_AUTHENTICATOR:
                logging.info("Waiting for Cryptnox card... (place card on reader)")
                devices = list(CtapPcscDevice.list_devices())
                if len(devices) == 0:
                    time.sleep(0.1)
                    continue
                device = devices[0]
                self.chosen_device = device

                fido2.pcsc.logger.setLevel(0)
                fido2.pcsc.logger.disabled = False
                fido2.pcsc.logger.isEnabledFor = lambda x: True
                fido2.pcsc.logger.manager.disable = 0
                # fido2.pcsc.logger.addHandler(LogPrintHandler())
                fido2.pcsc.logger._cache = {}

                return device
            # TODO: send timeout error properly
            raise ValueError("Could not connect to a PC/SC device in time!")
            # self.send_error(channel_id, 0x05)
            # return None

        return self.chosen_device

    @staticmethod
    def _get_client_pin_sub_command(buffer: bytes) -> Optional[int]:
        """Extract subCommand from an authenticatorClientPIN (0x06) CBOR payload.

        CTAP2 canonical CBOR maps have unsigned-integer keys in ascending order,
        so key 0x01 (pinUvAuthProtocol) always precedes key 0x02 (subCommand).
        """
        if len(buffer) < 4:
            return None
        first_key = buffer[2]
        if first_key == 0x02:
            return buffer[3]
        if first_key == 0x01 and len(buffer) >= 6 and buffer[4] == 0x02:
            return buffer[5]
        return None

    def _send_keepalive(self, channel: List[int], status: int) -> None:
        packets = self.encode_response_packets(channel, CommandType.KEEPALIVE, bytes([status]))
        for pkt in packets:
            self.device.send_input(pkt)

    def _is_card_on_reader(self) -> bool:
        """Check physical card presence using a short-lived, independent SCard context."""
        try:
            hresult, hctx = _SCardEstablishContext(_SCARD_SCOPE_USER)
            if hresult != 0:
                return False
            try:
                hresult, reader_names = _SCardListReaders(hctx, [])
                if hresult != 0 or not reader_names:
                    return False
                hresult, states = _SCardGetStatusChange(
                    hctx, 0, [(reader_names[0], _SCARD_STATE_UNAWARE)]
                )
                if hresult != 0 or not states:
                    return False
                return bool(states[0][1] & _SCARD_STATE_PRESENT)
            finally:
                SCardReleaseContext(hctx)
        except Exception:
            return False

    def _wait_for_card_tap(self, channel: List[int], timeout: int = 30) -> bool:
        """
        Gate execution on a physical card tap (remove then reinsert).

        Closes the current PC/SC session, monitors the reader for card removal
        followed by reinsertion, and sends KEEPALIVE STATUS_UPNEEDED every 500 ms
        so the browser shows "Touch your security key".  Returns True on confirmation.
        """
        print(
            "\n[!] User presence required — remove the card from the reader, "
            "then reinsert it to confirm...",
            flush=True,
        )
        # Release the session so our monitoring context doesn't conflict.
        self._close_pcsc_connection()

        confirmed = threading.Event()

        def _monitor():
            removed = False
            end_time = time.time() + timeout
            while time.time() < end_time and not confirmed.is_set():
                present = self._is_card_on_reader()
                if not removed and not present:
                    removed = True
                    logging.info("Card removed — reinsert to confirm presence...")
                elif removed and present:
                    confirmed.set()
                    return
                time.sleep(0.3)

        threading.Thread(target=_monitor, daemon=True).start()

        deadline = time.time() + timeout
        while not confirmed.is_set() and time.time() < deadline:
            self._send_keepalive(channel, 0x02)  # STATUS_UPNEEDED
            confirmed.wait(timeout=0.5)

        if confirmed.is_set():
            print("[+] Card tap confirmed.", flush=True)
            return True
        print("[-] Timed out waiting for card tap.", flush=True)
        return False

    def handle_cbor(self, channel: List[int], buffer: bytes) -> Optional[bytes]:
        """Handle an incoming CBOR command."""
        # Gate user presence (UP) once per authentication transaction.
        #
        # Chrome's ClientPIN flow when a PIN is set:
        #   getPINRetries → [Chrome shows PIN dialog] → getKeyAgreement → getPinUvAuthToken
        #
        # We gate at getPINRetries (subCommand 1) — the earliest point, before Chrome
        # shows the PIN dialog — so the card tap always precedes PIN entry.
        # _up_confirmed prevents re-prompting within the same transaction.
        if self.require_up and len(buffer) > 0 and not self._up_confirmed:
            should_gate = False
            cmd_name = None

            if buffer[0] == 0x06:  # authenticatorClientPIN
                sub = self._get_client_pin_sub_command(buffer)
                if sub == 1:  # getPINRetries — Chrome has not yet shown the PIN dialog
                    should_gate = True
                    cmd_name = "authenticatorClientPIN(getPINRetries)"
            elif buffer[0] in (0x01, 0x02):
                cmd_name = {
                    0x01: "authenticatorMakeCredential",
                    0x02: "authenticatorGetAssertion",
                }.get(buffer[0], "?")
                should_gate = True

            if should_gate:
                logging.info(
                    "User-presence gate: waiting before %s — tap the card reader to continue.",
                    cmd_name,
                )
                if not self._wait_for_card_tap(channel):
                    return bytes([0x31])  # CTAP2_ERR_USER_ACTION_TIMEOUT
                self._up_confirmed = True

        # Acquire (or re-acquire) the CTAP device.  The card tap closes the PC/SC
        # session, so get_pcsc_device() reconnects transparently after reinsertion.
        ctap = self.get_pcsc_device(channel)
        if ctap is None:
            return None

        logging.debug(f"Sending CBOR to device {ctap}: {buffer.hex()}")
        try:
            res = ctap.call(cmd=CommandType.CBOR, data=buffer)
        except CtapError as e:
            logging.info(f"Got CTAP error response from device: {e}")
            res = bytes([e.code])

        # Reset after each credential command so the next authentication prompts again.
        if len(buffer) > 0 and buffer[0] in (0x01, 0x02):
            self._up_confirmed = False

        return res

    def handle_cancel(self, channel: List[int], buffer: bytes) -> Optional[bytes]:
        channel_key = self.get_channel_key(channel)
        if channel_key in self.channels_to_state:
            del self.channels_to_state[channel_key]
        return bytes()

    def handle_wink(self, channel: List[int], buffer: bytes) -> Optional[bytes]:
        """Do nothing; this can't be done over PC/SC."""
        return bytes()

    def handle_msg(self, channel: List[int], buffer: bytes) -> Optional[bytes]:
        """Process a U2F/CTAP1 message."""
        device = self.get_pcsc_device(channel)
        if device is None:
            return None
        res = device.call(CTAPHID.MSG, buffer)
        return res

    def handle_ping(self, channel: List[int], buffer: bytes) -> Optional[bytes]:
        """Handle an echo request."""
        return buffer

    def handle_keepalive(self, channel: List[int], buffer: bytes) -> Optional[bytes]:
        """Placeholder: always returns that the device is processing."""
        return bytes([1])

    def encode_response_packets(
        self,
        channel: List[int],
        cmd: CommandType,
        data: bytes,
        packet_size: int = 64,
    ) -> List[bytes]:
        """Chunk response data to be delivered over USB."""
        offset_start = 0
        seq = 0
        responses = []
        while offset_start < len(data):
            if seq == 0:
                capacity = packet_size - 7
                chunk = data[offset_start : (offset_start + capacity)]
                data_len_upper = len(data) >> 8
                data_len_lower = len(data) % 256
                response = (
                    bytes(channel)
                    + bytes([cmd | 0x80, data_len_upper, data_len_lower])
                    + chunk
                )
            else:
                capacity = packet_size - 5
                chunk = data[offset_start : (offset_start + capacity)]
                response = bytes(channel) + bytes([seq - 1]) + chunk

            padding_byte_count = packet_size - len(response)
            if padding_byte_count > 0:
                response = response + bytes([0x00] * padding_byte_count)

            responses.append(bytes(response))
            offset_start += capacity
            seq += 1

        return responses

    def get_channel_key(self, channel: List[int]) -> str:
        return bytes(channel).hex()

    def send_error(self, channel: List[int], error_type: int) -> None:
        responses = self.encode_response_packets(
            channel, CommandType.ERROR, bytes([error_type])
        )
        for response in responses:
            self.device.send_input(response)

    def finish_receiving(self, channel: List[int]) -> None:
        """When finished receiving packets, act on them."""
        channel_key = self.get_channel_key(channel)
        cmd, _, _, data = self.channels_to_state[channel_key]
        self.handle_cancel(channel, b"")

        try:
            handler = getattr(self, f"handle_{cmd.name.lower()}", None)
            if handler is not None:
                response_body = handler(channel, data)
                if response_body is None:
                    # Already dealt with
                    return
                responses = self.encode_response_packets(channel, cmd, response_body)
            else:
                self.send_error(channel, 0x01)
                return
        except Exception as e:
            logging.warning(f"Error: {e}")
            self.send_error(channel, 0x7F)
            self._close_pcsc_connection()
            return

        for response in responses:
            self.device.send_input(response)

    def parse_subsequent_packet(self, data: bytes) -> Tuple[bytes, int, bytes]:
        """Parse a non-initial packet."""
        return data[1:5], data[5], data[6:]
