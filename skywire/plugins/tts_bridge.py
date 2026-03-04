"""
TTS Bridge Plugin

Receives TTS audio from external systems (ThoughtMaker) and routes to nodes.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

import asyncio
import json
import logging
from typing import Optional, Set
from aiohttp import web, WSMsgType
import base64

from .base import SourcePlugin

logger = logging.getLogger(__name__)


class TTSBridgePlugin(SourcePlugin):
    """
    Bridge plugin for receiving TTS audio from external systems.

    External systems (like ThoughtMaker) connect via WebSocket and send
    TTS audio which gets routed to specified nodes.
    """

    PLUGIN_ID = "tts_bridge"

    def __init__(self):
        super().__init__("tts_bridge", "TTS Bridge")
        self.info.description = "Receives TTS audio from external systems"
        self.info.config = {
            "default_targets": [],  # Default nodes for TTS playback
        }
        self._connections: dict = {}

    async def start(self):
        """Start the TTS bridge (routes are added by server)."""
        self.logger.info("TTS Bridge started")
        self.default_targets = set(self.info.config.get("default_targets", []))

    async def stop(self):
        """Stop the TTS bridge."""
        # Close any active connections
        for ws in list(self._connections.values()):
            await ws.close()
        self._connections.clear()
        self.logger.info("TTS Bridge stopped")

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection from TTS source."""
        ws = web.WebSocketResponse(max_msg_size=50 * 1024 * 1024)
        await ws.prepare(request)

        source_name = request.query.get('name', 'TTS')
        conn_id = id(ws)
        self._connections[conn_id] = ws

        self.logger.info(f"TTS source connected: {source_name}")

        await ws.send_json({
            "type": "connected",
            "plugin": self.id,
            "targets": list(self.default_targets)
        })

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_message(data)
                elif msg.type == WSMsgType.BINARY:
                    # Raw audio - use default targets
                    await self.emit_audio(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            self.logger.error(f"TTS bridge error: {e}")
        finally:
            del self._connections[conn_id]
            self.logger.info(f"TTS source disconnected: {source_name}")

        return ws

    async def _handle_message(self, data: dict):
        """Handle JSON message with audio and routing."""
        msg_type = data.get("type")

        if msg_type == "audio":
            # Audio with routing info
            audio_b64 = data.get("data")
            targets = data.get("targets")

            if audio_b64:
                audio_data = base64.b64decode(audio_b64)
                target_set = set(targets) if targets else None
                await self.emit_audio(audio_data, target_set)

        elif msg_type == "set_targets":
            # Update default targets
            self.default_targets = set(data.get("targets", []))
            self.logger.info(f"TTS targets updated: {self.default_targets}")

    async def send_to_targets(self, audio_data: bytes, targets: Optional[Set[str]] = None):
        """Send TTS audio to specified targets."""
        await self.emit_audio(audio_data, targets)

    def get_status(self):
        status = super().get_status()
        status["connections"] = len(self._connections)
        status["default_targets"] = list(self.default_targets)
        return status
