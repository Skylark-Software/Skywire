"""
STT Bridge Plugin

Forwards mic audio from nodes to external STT services.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

import asyncio
import json
import logging
from typing import Optional, Set, Dict
from aiohttp import web, WSMsgType
import base64

from .base import SinkPlugin

logger = logging.getLogger(__name__)


class STTBridgePlugin(SinkPlugin):
    """
    Bridge plugin for forwarding mic audio to STT services.

    Receives audio from connected nodes and forwards to external
    STT systems (like ThoughtMaker's STT module).
    """

    PLUGIN_ID = "stt_bridge"

    def __init__(self):
        super().__init__("stt_bridge", "STT Bridge")
        self.info.description = "Forwards mic audio to STT services"
        self.info.config = {
            "source_nodes": [],    # Which nodes to capture from (empty = all)
            "forward_format": "pcm_s16le",
            "sample_rate": 16000,
        }
        self._stt_connections: Dict[str, web.WebSocketResponse] = {}
        self._active_source: Optional[str] = None  # Currently active mic source

    async def start(self):
        """Start the STT bridge."""
        self.source_filter = set(self.info.config.get("source_nodes", []))
        self.logger.info("STT Bridge started")

    async def stop(self):
        """Stop the STT bridge."""
        for ws in list(self._stt_connections.values()):
            await ws.close()
        self._stt_connections.clear()
        self.logger.info("STT Bridge stopped")

    async def receive_audio(self, audio_data: bytes, source_id: str):
        """Receive audio from a node and forward to STT services."""
        # Check if we should process this source
        if self.source_filter and source_id not in self.source_filter:
            return

        # Check if this is the active source (for single-source mode)
        if self._active_source and source_id != self._active_source:
            return

        # Forward to all connected STT services
        for conn_id, ws in list(self._stt_connections.items()):
            if ws.closed:
                del self._stt_connections[conn_id]
                continue

            try:
                # Send as binary
                await ws.send_bytes(audio_data)
            except Exception as e:
                self.logger.error(f"Failed to forward to STT: {e}")
                del self._stt_connections[conn_id]

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection from STT service."""
        ws = web.WebSocketResponse(max_msg_size=10 * 1024 * 1024)
        await ws.prepare(request)

        service_name = request.query.get('name', 'STT')
        conn_id = id(ws)
        self._stt_connections[conn_id] = ws

        self.logger.info(f"STT service connected: {service_name}")

        await ws.send_json({
            "type": "connected",
            "plugin": self.id,
            "sample_rate": self.info.config.get("sample_rate", 16000),
            "format": self.info.config.get("forward_format", "pcm_s16le"),
            "source_nodes": list(self.source_filter)
        })

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_message(data)
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            self.logger.error(f"STT bridge error: {e}")
        finally:
            del self._stt_connections[conn_id]
            self.logger.info(f"STT service disconnected: {service_name}")

        return ws

    async def _handle_message(self, data: dict):
        """Handle control messages from STT service."""
        msg_type = data.get("type")

        if msg_type == "set_source":
            # Set active mic source
            self._active_source = data.get("node_id")
            self.logger.info(f"Active mic source: {self._active_source or 'all'}")

        elif msg_type == "set_sources":
            # Update source filter
            self.source_filter = set(data.get("nodes", []))
            self.logger.info(f"STT sources updated: {self.source_filter or 'all'}")

    def set_active_source(self, node_id: Optional[str]):
        """Set the active mic source."""
        self._active_source = node_id

    def get_status(self):
        status = super().get_status()
        status["stt_connections"] = len(self._stt_connections)
        status["source_nodes"] = list(self.source_filter)
        status["active_source"] = self._active_source
        return status
