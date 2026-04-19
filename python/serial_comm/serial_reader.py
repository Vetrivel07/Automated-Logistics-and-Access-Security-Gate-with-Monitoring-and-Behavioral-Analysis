# OOP Serial Reader — runs as a background daemon thread.
# Reads Arduino serial output, parses JSON messages,
# and calls AccessService directly (never goes through API).
#
# Message format from Arduino:
#   <{"uid":"A3 B4 C1 D9","status":"allowed","event":"IN"}>
#
# Design:
#   - Class-based (SerialReader)
#   - Runs in its own thread via threading.Thread
#   - Reconnects automatically if Arduino disconnects
#   - Uses start/end marker parsing (same as professor's Node B)

import json
import time
import threading
import serial as pyserial

from core.config import settings
from services.access_service import AccessService


class SerialReader:

    def __init__(self) -> None:
        self._port        = settings.SERIAL_PORT
        self._baud        = settings.SERIAL_BAUD_RATE
        self._timeout     = settings.SERIAL_TIMEOUT
        self._start_mark  = settings.MSG_START_MARKER
        self._end_mark    = settings.MSG_END_MARKER
        self._reconnect   = settings.SERIAL_RECONNECT_DELAY

        self._running     = False
        self._thread: threading.Thread | None = None
        self._access_svc  = AccessService()

    # PUBLIC: start / stop
    def start(self) -> None:
        """
        Start the background reader thread.
        Thread is daemon=True so it exits when main process exits.
        """
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name="SerialReaderThread",
            daemon=True,
        )
        self._thread.start()
        print(f"[SerialReader] Thread started on {self._port}")

    def stop(self) -> None:
        """Signal the reader thread to stop gracefully."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        print("[SerialReader] Stop signal sent.")

    # PRIVATE: _run_loop
    # Main thread loop — handles connect, read, reconnect.

    def _run_loop(self) -> None:
        while self._running:
            try:
                with pyserial.Serial(
                    port=self._port,
                    baudrate=self._baud,
                    timeout=self._timeout,
                ) as ser:
                    # Arduino resets on connect — wait for boot
                    time.sleep(2)
                    print(f"[SerialReader] Connected to {self._port}")
                    self._read_loop(ser)

            except pyserial.SerialException as e:
                print(f"[SerialReader] Serial error: {e}")
                print(
                    f"[SerialReader] Retrying in {self._reconnect}s..."
                )
                time.sleep(self._reconnect)

            except Exception as e:
                print(f"[SerialReader] Unexpected error: {e}")
                time.sleep(self._reconnect)

    def _read_loop(self, ser: pyserial.Serial) -> None:
        buffer        = ""
        in_message    = False

        while self._running:
            try:
                if ser.in_waiting == 0:
                    time.sleep(0.01)  # small sleep to avoid busy-wait
                    continue

                raw = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")

                for char in raw:
                    if char == self._start_mark:
                        # Start marker detected — begin recording
                        buffer     = ""
                        in_message = True

                    elif char == self._end_mark and in_message:
                        # End marker detected — payload complete
                        in_message = False
                        self._dispatch(buffer.strip())
                        buffer = ""

                    elif in_message:
                        buffer += char

            except pyserial.SerialException:
                print("[SerialReader] Connection lost mid-read.")
                break

    # PRIVATE: _dispatch
    # Parses the JSON payload and calls AccessService.

    def _dispatch(self, payload: str) -> None:
        if not payload:
            return

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            print(f"[SerialReader] JSON parse error: {e} | raw: {payload}")
            return

        # Skip non-scan events (e.g. boot confirmation)
        if "event" not in data or "status" not in data or "uid" not in data:
            print(f"[SerialReader] Non-scan message received: {data}")
            return

        uid    = data["uid"]
        status = data["status"]
        event  = data["event"]

        print(
            f"[SerialReader] Received → "
            f"uid={uid} status={status} event={event}"
        )

        # Forward to AccessService — no API call, direct service call
        self._access_svc.process_scan(uid=uid, status=status, event=event)