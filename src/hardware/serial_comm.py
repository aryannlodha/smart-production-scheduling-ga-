"""
ESP32 serial communication handler.

Manages the serial connection between Python (scheduling engine)
and the ESP32 microcontroller (physical interface).

Protocol: Newline-delimited JSON messages over USB serial.

The ESP32 sends events (button presses) to Python.
Python sends status updates and commands to the ESP32.

When no ESP32 is connected, the system operates in software-only mode.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


@dataclass
class SerialMessage:
    """A message exchanged between Python and ESP32."""
    type: str           # e.g. "BREAKDOWN", "STATUS_UPDATE", "START", "RESET"
    data: Dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp or time.time(),
        })

    @classmethod
    def from_json(cls, json_str: str) -> "SerialMessage":
        d = json.loads(json_str.strip())
        return cls(
            type=d.get("type", "UNKNOWN"),
            data=d.get("data", {}),
            timestamp=d.get("timestamp", 0.0),
        )


# Message type constants
class MessageType:
    # ESP32 → Python
    BREAKDOWN = "BREAKDOWN"       # Button press: machine breakdown
    START = "START"               # Start button pressed
    RESET = "RESET"               # Reset button pressed
    STATUS_REQUEST = "STATUS_REQ" # ESP32 requests current status
    HEARTBEAT = "HEARTBEAT"       # Keep-alive

    # Python → ESP32
    STATUS_UPDATE = "STATUS_UPDATE"   # Machine status update
    SCHEDULE_UPDATE = "SCHEDULE_UPD"  # Schedule has changed
    MACHINE_STATE = "MACHINE_STATE"   # Individual machine state
    DISPLAY_TEXT = "DISPLAY_TEXT"      # Text for OLED display
    ACK = "ACK"                       # Acknowledge received message


class ESP32Handler:
    """Manages serial communication with the ESP32.

    Usage:
        handler = ESP32Handler()
        handler.on_message(callback_function)
        handler.connect("COM3")   # or skip for software-only mode

        handler.send(SerialMessage(type="STATUS_UPDATE", data={...}))
        handler.disconnect()

    Software-only mode:
        If connect() is never called or fails, the handler operates
        in software-only mode.  send() calls are logged but not
        transmitted.  on_message callbacks can still be triggered
        manually via simulate_receive().
    """

    def __init__(self):
        self._serial = None
        self._state = ConnectionState.DISCONNECTED
        self._port: Optional[str] = None
        self._baud_rate = 115200
        self._callbacks: List[Callable[[SerialMessage], None]] = []
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        self._last_message: Optional[SerialMessage] = None
        self._message_log: List[SerialMessage] = []
        self._max_log = 100

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def port(self) -> Optional[str]:
        return self._port

    @property
    def last_message(self) -> Optional[SerialMessage]:
        return self._last_message

    @property
    def message_log(self) -> List[SerialMessage]:
        return list(self._message_log)

    def on_message(self, callback: Callable[[SerialMessage], None]) -> None:
        """Register a callback for incoming messages."""
        self._callbacks.append(callback)

    def connect(
        self,
        port: str,
        baud_rate: int = 115200,
        timeout: float = 2.0,
    ) -> bool:
        """Attempt to connect to the ESP32 via serial.

        Returns True if successful, False otherwise.
        Does not raise exceptions — logs errors and enters ERROR state.
        """
        self._port = port
        self._baud_rate = baud_rate
        self._state = ConnectionState.CONNECTING

        try:
            import serial
            self._serial = serial.Serial(
                port=port,
                baudrate=baud_rate,
                timeout=timeout,
            )
            time.sleep(2)  # Wait for ESP32 to reset after connection
            self._state = ConnectionState.CONNECTED
            self._running = True

            # Start read thread
            self._read_thread = threading.Thread(
                target=self._read_loop, daemon=True
            )
            self._read_thread.start()

            logger.info(f"Connected to ESP32 on {port} at {baud_rate} baud")
            return True

        except ImportError:
            logger.warning(
                "PySerial not installed.  Running in software-only mode. "
                "Install with: pip install pyserial"
            )
            self._state = ConnectionState.DISCONNECTED
            return False

        except Exception as e:
            logger.error(f"Failed to connect to {port}: {e}")
            self._state = ConnectionState.ERROR
            return False

    def disconnect(self) -> None:
        """Disconnect from the ESP32."""
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception as e:
                logger.error(f"Error closing serial: {e}")
        self._state = ConnectionState.DISCONNECTED
        self._serial = None
        logger.info("Disconnected from ESP32")

    def send(self, message: SerialMessage) -> bool:
        """Send a message to the ESP32.

        Returns True if sent successfully.
        In software-only mode, logs the message and returns False.
        """
        message.timestamp = time.time()
        self._log_message(message)

        if not self.is_connected or self._serial is None:
            logger.debug(
                f"[SW-ONLY] Would send: {message.to_json()}"
            )
            return False

        try:
            line = message.to_json() + "\n"
            self._serial.write(line.encode("utf-8"))
            self._serial.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self._state = ConnectionState.ERROR
            return False

    def send_machine_status(
        self,
        machine_states: Dict[str, str],
        display_text: str = "",
    ) -> None:
        """Convenience: send machine status update to ESP32.

        Args:
            machine_states: e.g. {"M1": "IDLE", "M2": "BUSY", "M3": "DOWN"}
            display_text: Text to show on OLED display.
        """
        self.send(SerialMessage(
            type=MessageType.STATUS_UPDATE,
            data={
                "machines": machine_states,
                "display": display_text,
            },
        ))

    def simulate_receive(self, message: SerialMessage) -> None:
        """Simulate receiving a message (for software-only testing)."""
        self._last_message = message
        self._log_message(message)
        for cb in self._callbacks:
            try:
                cb(message)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _read_loop(self) -> None:
        """Background thread: read lines from serial and dispatch."""
        while self._running and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting > 0:
                    line = self._serial.readline().decode(
                        "utf-8", errors="replace"
                    ).strip()
                    if line:
                        try:
                            msg = SerialMessage.from_json(line)
                            self._last_message = msg
                            self._log_message(msg)
                            for cb in self._callbacks:
                                try:
                                    cb(msg)
                                except Exception as e:
                                    logger.error(f"Callback error: {e}")
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Invalid JSON from ESP32: {line}"
                            )
                else:
                    time.sleep(0.05)  # Avoid busy-waiting
            except Exception as e:
                if self._running:
                    logger.error(f"Serial read error: {e}")
                    self._state = ConnectionState.ERROR
                break

    def _log_message(self, message: SerialMessage) -> None:
        """Add message to the log, trimming old entries."""
        self._message_log.append(message)
        if len(self._message_log) > self._max_log:
            self._message_log = self._message_log[-self._max_log:]

    @staticmethod
    def list_ports() -> List[str]:
        """List available serial ports."""
        try:
            import serial.tools.list_ports
            return [p.device for p in serial.tools.list_ports.comports()]
        except ImportError:
            return []
