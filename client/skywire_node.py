#!/usr/bin/env python3
"""
Skywire Node Client

Always-on audio playback client for Skywire audio routing system.
Designed for reliable, headless operation on audio endpoints.

Features:
- Automatic reconnection with exponential backoff
- WebSocket keepalive (ping/pong)
- PipeWire/PulseAudio playback
- Volume control
- Statistics and health reporting

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

import argparse
import asyncio
import json
import logging
import os
import random
import signal
import socket
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("ERROR: websockets not installed. Run: pip install websockets")
    sys.exit(1)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("skywire-node")

# Constants
DEFAULT_SERVER = "ws://localhost:8765/audio"
DEFAULT_SAMPLE_RATE = 48000
RECONNECT_MIN_DELAY = 1.0
RECONNECT_MAX_DELAY = 60.0
PING_INTERVAL = 20
PING_TIMEOUT = 10
MAX_MESSAGE_SIZE = 50 * 1024 * 1024


@dataclass
class NodeStats:
    """Node statistics."""
    connects: int = 0
    disconnects: int = 0
    audio_chunks: int = 0
    bytes_received: int = 0
    playback_errors: int = 0
    last_audio: Optional[datetime] = None
    started: datetime = field(default_factory=datetime.now)


class SkywireNode:
    """Skywire audio node client."""

    def __init__(
        self,
        server_url: str,
        node_id: str,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        playback_method: str = "auto"
    ):
        self.server_url = server_url
        self.node_id = node_id
        self.sample_rate = sample_rate
        self.playback_method = playback_method

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_delay = RECONNECT_MIN_DELAY

        # State
        self.volume = 100
        self.muted = False

        # Statistics
        self.stats = NodeStats()

        # Detect playback method
        self._playback_cmd = self._detect_playback_method()

    def _detect_playback_method(self) -> List[str]:
        """Detect available audio playback method."""
        if self.playback_method != "auto":
            method = self.playback_method
        else:
            # Auto-detect
            if self._cmd_exists("pw-cat"):
                method = "pipewire"
            elif self._cmd_exists("paplay"):
                method = "pulseaudio"
            elif self._cmd_exists("aplay"):
                method = "alsa"
            else:
                logger.warning("No audio playback command found!")
                method = "pipewire"  # Default, may fail

        if method == "pipewire":
            return ["pw-cat", "--playback", "--rate", str(self.sample_rate),
                    "--channels", "1", "--format", "s16", "-"]
        elif method == "pulseaudio":
            return ["paplay", "--raw", f"--rate={self.sample_rate}",
                    "--channels=1", "--format=s16le"]
        elif method == "alsa":
            return ["aplay", "-q", "-f", "S16_LE", "-r", str(self.sample_rate),
                    "-c", "1", "-"]
        else:
            return ["pw-cat", "--playback", "--rate", str(self.sample_rate),
                    "--channels", "1", "--format", "s16", "-"]

    @staticmethod
    def _cmd_exists(cmd: str) -> bool:
        """Check if a command exists."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @property
    def connection_url(self) -> str:
        """Build full connection URL."""
        sep = "&" if "?" in self.server_url else "?"
        return f"{self.server_url}{sep}node_id={self.node_id}&sample_rate={self.sample_rate}&format=pcm_s16le"

    async def run(self):
        """Main run loop with automatic reconnection."""
        self._running = True

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown)

        logger.info(f"Skywire Node '{self.node_id}' starting")
        logger.info(f"Server: {self.server_url}")
        logger.info(f"Sample rate: {self.sample_rate}Hz")
        logger.info(f"Playback: {' '.join(self._playback_cmd[:2])}")

        while self._running:
            try:
                await self._connect_and_run()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection error: {e}")

            if self._running:
                await self._reconnect_backoff()

        logger.info("Skywire Node stopped")
        self._log_stats()

    async def _connect_and_run(self):
        """Connect to server and handle messages."""
        url = self.connection_url
        logger.info(f"Connecting to {url}")

        async with websockets.connect(
            url,
            max_size=MAX_MESSAGE_SIZE,
            ping_interval=PING_INTERVAL,
            ping_timeout=PING_TIMEOUT,
            close_timeout=5
        ) as ws:
            self.ws = ws
            self.stats.connects += 1
            self._reconnect_delay = RECONNECT_MIN_DELAY

            # Receive welcome
            welcome = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(welcome)
            logger.info(f"Connected: {data.get('type', 'unknown')}")

            # Send capabilities
            await ws.send(json.dumps({
                "type": "device_list",
                "input_devices": [],
                "output_devices": [{"id": "0", "name": "Default", "channels": 2}],
                "active_input": "none",
                "active_output": "0"
            }))

            logger.info("Ready for audio")

            # Message loop
            async for message in ws:
                if isinstance(message, bytes):
                    await self._handle_audio(message)
                else:
                    await self._handle_control(json.loads(message))

    async def _handle_audio(self, audio_data: bytes):
        """Handle received audio data."""
        self.stats.audio_chunks += 1
        self.stats.bytes_received += len(audio_data)
        self.stats.last_audio = datetime.now()

        if self.muted:
            logger.debug(f"Muted, skipping {len(audio_data)} bytes")
            return

        logger.info(f"Playing {len(audio_data)} bytes")
        self._play_audio(audio_data)

    async def _handle_control(self, data: dict):
        """Handle control message."""
        msg_type = data.get("type")

        if msg_type == "set_volume":
            self.volume = data.get("volume", 100)
            logger.info(f"Volume set to {self.volume}")

        elif msg_type == "set_mute":
            self.muted = data.get("muted", False)
            logger.info(f"Mute set to {self.muted}")

        elif msg_type == "ping":
            await self.ws.send(json.dumps({"type": "pong"}))

        else:
            logger.debug(f"Unknown control message: {msg_type}")

    def _play_audio(self, audio_data: bytes):
        """Play audio through system audio."""
        try:
            proc = subprocess.Popen(
                self._playback_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            proc.stdin.write(audio_data)
            proc.stdin.close()

            def check_result():
                rc = proc.wait()
                if rc != 0:
                    err = proc.stderr.read().decode().strip()
                    logger.error(f"Playback failed ({rc}): {err}")
                    self.stats.playback_errors += 1
                else:
                    logger.debug("Playback complete")

            threading.Thread(target=check_result, daemon=True).start()

        except FileNotFoundError:
            logger.error(f"Playback command not found: {self._playback_cmd[0]}")
            self.stats.playback_errors += 1
        except Exception as e:
            logger.error(f"Playback error: {e}")
            self.stats.playback_errors += 1

    async def _reconnect_backoff(self):
        """Wait with exponential backoff before reconnecting."""
        jitter = self._reconnect_delay * 0.2 * (random.random() * 2 - 1)
        delay = self._reconnect_delay + jitter

        logger.info(f"Reconnecting in {delay:.1f}s...")
        await asyncio.sleep(delay)

        self._reconnect_delay = min(
            self._reconnect_delay * 2,
            RECONNECT_MAX_DELAY
        )

    def _shutdown(self):
        """Handle shutdown signal."""
        logger.info("Shutdown signal received")
        self._running = False
        if self.ws:
            asyncio.create_task(self.ws.close())

    def _log_stats(self):
        """Log session statistics."""
        logger.info("Session statistics:")
        logger.info(f"  Connections: {self.stats.connects}")
        logger.info(f"  Disconnects: {self.stats.disconnects}")
        logger.info(f"  Audio chunks: {self.stats.audio_chunks}")
        logger.info(f"  Bytes received: {self.stats.bytes_received:,}")
        logger.info(f"  Playback errors: {self.stats.playback_errors}")


def get_hostname() -> str:
    """Get system hostname."""
    return socket.gethostname()


def main():
    parser = argparse.ArgumentParser(
        description="Skywire Node - Audio Playback Client"
    )
    parser.add_argument(
        "--server", "-s",
        default=DEFAULT_SERVER,
        help=f"Skywire server URL (default: {DEFAULT_SERVER})"
    )
    parser.add_argument(
        "--node-id", "-n",
        default=get_hostname(),
        help=f"Node identifier (default: {get_hostname()})"
    )
    parser.add_argument(
        "--sample-rate", "-r",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"Audio sample rate (default: {DEFAULT_SAMPLE_RATE})"
    )
    parser.add_argument(
        "--playback", "-p",
        choices=["auto", "pipewire", "pulseaudio", "alsa"],
        default="auto",
        help="Playback method (default: auto)"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    node = SkywireNode(
        server_url=args.server,
        node_id=args.node_id,
        sample_rate=args.sample_rate,
        playback_method=args.playback
    )

    asyncio.run(node.run())


if __name__ == "__main__":
    main()
