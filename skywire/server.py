"""
Skywire Server - Main server class

Runs WebSocket server for nodes and sources, plus web dashboard.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Set, Any
from aiohttp import web, WSMsgType
import weakref

from .router import AudioRouter
from .plugins.manager import PluginManager
from .plugins.tts_bridge import TTSBridgePlugin
from .plugins.stt_bridge import STTBridgePlugin

logger = logging.getLogger(__name__)


class SkywireServer:
    """Main Skywire server - coordinates nodes, sources, and routing."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        websocket_port: int = 8765,
        web_port: int = 8080,
        config: Optional[Dict] = None
    ):
        self.host = host
        self.websocket_port = websocket_port
        self.web_port = web_port
        self.config = config or {}

        # Connection tracking
        self._nodes: Dict[str, 'NodeConnection'] = {}
        self._sources: Dict[str, 'SourceConnection'] = {}

        # Audio router
        self.router = AudioRouter(self)

        # Plugin manager
        self.plugins = PluginManager(self)
        self._register_builtin_plugins()

        # Web app
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

        # State
        self._running = False
        self._start_time: Optional[datetime] = None

    @property
    def nodes(self) -> Dict[str, 'NodeConnection']:
        """Get connected nodes."""
        return self._nodes

    @property
    def sources(self) -> Dict[str, 'SourceConnection']:
        """Get connected sources."""
        return self._sources

    async def start(self):
        """Start the server."""
        logger.info(f"Starting Skywire server...")
        self._running = True
        self._start_time = datetime.now()

        # Create web application
        self._app = web.Application()
        self._setup_routes()

        # Start server
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        # WebSocket + Web on same port for simplicity
        self._site = web.TCPSite(self._runner, self.host, self.websocket_port)
        await self._site.start()

        # Start plugins
        await self.plugins.start_all()

        logger.info(f"Skywire server running on http://{self.host}:{self.websocket_port}")
        logger.info(f"  WebSocket: ws://{self.host}:{self.websocket_port}/audio")
        logger.info(f"  Dashboard: http://{self.host}:{self.websocket_port}/")
        logger.info(f"  API: http://{self.host}:{self.websocket_port}/api/")
        logger.info(f"  Plugins: {len(self.plugins.plugins)} registered")

    async def stop(self):
        """Stop the server."""
        logger.info("Stopping Skywire server...")
        self._running = False

        # Stop plugins
        await self.plugins.stop_all()

        # Close all connections
        for node in list(self._nodes.values()):
            await node.close()
        for source in list(self._sources.values()):
            await source.close()

        # Stop web server
        if self._runner:
            await self._runner.cleanup()

        logger.info("Skywire server stopped")

    def _register_builtin_plugins(self):
        """Register built-in plugins."""
        # TTS Bridge - receives TTS audio from external systems
        tts_bridge = TTSBridgePlugin()
        self.plugins.register(tts_bridge)

        # STT Bridge - forwards mic audio to STT services
        stt_bridge = STTBridgePlugin()
        self.plugins.register(stt_bridge)

    def _setup_routes(self):
        """Setup HTTP and WebSocket routes."""
        app = self._app

        # WebSocket endpoints
        app.router.add_get('/audio', self._handle_node_ws)
        app.router.add_get('/source', self._handle_source_ws)

        # Plugin WebSocket endpoints
        app.router.add_get('/plugin/tts', self._handle_tts_bridge_ws)
        app.router.add_get('/plugin/stt', self._handle_stt_bridge_ws)

        # API endpoints
        app.router.add_get('/api/nodes', self._api_get_nodes)
        app.router.add_get('/api/sources', self._api_get_sources)
        app.router.add_get('/api/routing', self._api_get_routing)
        app.router.add_post('/api/routing', self._api_set_routing)
        app.router.add_post('/api/node/{node_id}/volume', self._api_set_volume)
        app.router.add_post('/api/play', self._api_play_audio)
        app.router.add_get('/health', self._api_health)

        # Plugin API endpoints
        app.router.add_get('/api/plugins', self._api_get_plugins)
        app.router.add_post('/api/plugin/{plugin_id}/enable', self._api_enable_plugin)
        app.router.add_post('/api/plugin/{plugin_id}/disable', self._api_disable_plugin)
        app.router.add_get('/api/plugin/{plugin_id}/status', self._api_plugin_status)

        # Web dashboard (CSS/JS is inline, no static files needed)
        app.router.add_get('/', self._handle_dashboard)

    # ─────────────────────────────────────────────────────────────
    # WebSocket Handlers
    # ─────────────────────────────────────────────────────────────

    async def _handle_node_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection from audio node."""
        ws = web.WebSocketResponse(max_msg_size=10 * 1024 * 1024)
        await ws.prepare(request)

        # Parse query params
        node_id = request.query.get('node_id', 'unknown')
        sample_rate = int(request.query.get('sample_rate', 48000))
        audio_format = request.query.get('format', 'pcm_s16le')

        logger.info(f"Node connecting: {node_id} (rate={sample_rate}, format={audio_format})")

        # Create node connection
        node = NodeConnection(
            node_id=node_id,
            ws=ws,
            sample_rate=sample_rate,
            audio_format=audio_format,
            server=self
        )
        self._nodes[node_id] = node

        # Send welcome
        await ws.send_json({
            "type": "connected",
            "node_id": node_id,
            "server_time": datetime.now().isoformat(),
            "version": "0.1.0"
        })

        logger.info(f"Node connected: {node_id}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await node.handle_message(json.loads(msg.data))
                elif msg.type == WSMsgType.BINARY:
                    # Audio from node (mic input)
                    await node.handle_audio(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"Node {node_id} WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"Node {node_id} error: {e}")
        finally:
            del self._nodes[node_id]
            logger.info(f"Node disconnected: {node_id}")

        return ws

    async def _handle_source_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection from audio source."""
        ws = web.WebSocketResponse(max_msg_size=50 * 1024 * 1024)
        await ws.prepare(request)

        source_id = request.query.get('source_id', 'unknown')
        source_name = request.query.get('name', source_id)

        logger.info(f"Source connecting: {source_id} ({source_name})")

        source = SourceConnection(
            source_id=source_id,
            name=source_name,
            ws=ws,
            server=self
        )
        self._sources[source_id] = source

        await ws.send_json({
            "type": "connected",
            "source_id": source_id,
            "nodes": list(self._nodes.keys())
        })

        logger.info(f"Source connected: {source_id}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get('type') == 'audio':
                        # Audio with routing info
                        await source.handle_audio_message(data)
                elif msg.type == WSMsgType.BINARY:
                    # Raw audio - route to default targets
                    await source.handle_audio(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"Source {source_id} WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"Source {source_id} error: {e}")
        finally:
            del self._sources[source_id]
            logger.info(f"Source disconnected: {source_id}")

        return ws

    # ─────────────────────────────────────────────────────────────
    # API Handlers
    # ─────────────────────────────────────────────────────────────

    async def _api_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "ok",
            "uptime": str(datetime.now() - self._start_time) if self._start_time else "0",
            "nodes": len(self._nodes),
            "sources": len(self._sources),
            "node_ids": list(self._nodes.keys()),
            "source_ids": list(self._sources.keys())
        })

    async def _api_get_nodes(self, request: web.Request) -> web.Response:
        """Get list of connected nodes."""
        nodes = []
        for node_id, node in self._nodes.items():
            nodes.append({
                "id": node_id,
                "sample_rate": node.sample_rate,
                "format": node.audio_format,
                "connected_at": node.connected_at.isoformat(),
                "volume": node.volume,
                "muted": node.muted,
                "last_audio": node.last_audio.isoformat() if node.last_audio else None
            })
        return web.json_response({"nodes": nodes})

    async def _api_get_sources(self, request: web.Request) -> web.Response:
        """Get list of connected sources."""
        sources = []
        for source_id, source in self._sources.items():
            sources.append({
                "id": source_id,
                "name": source.name,
                "connected_at": source.connected_at.isoformat()
            })
        return web.json_response({"sources": sources})

    async def _api_get_routing(self, request: web.Request) -> web.Response:
        """Get current routing configuration."""
        return web.json_response(self.router.get_routing())

    async def _api_set_routing(self, request: web.Request) -> web.Response:
        """Update routing configuration."""
        data = await request.json()
        self.router.set_routing(data)
        return web.json_response({"status": "ok"})

    async def _api_set_volume(self, request: web.Request) -> web.Response:
        """Set node volume."""
        node_id = request.match_info['node_id']
        data = await request.json()

        if node_id not in self._nodes:
            return web.json_response({"error": "Node not found"}, status=404)

        node = self._nodes[node_id]
        if 'volume' in data:
            node.volume = data['volume']
            await node.send_json({"type": "set_volume", "volume": node.volume})
        if 'muted' in data:
            node.muted = data['muted']
            await node.send_json({"type": "set_mute", "muted": node.muted})

        return web.json_response({"status": "ok"})

    async def _api_play_audio(self, request: web.Request) -> web.Response:
        """Play audio to specified nodes."""
        data = await request.json()
        targets = data.get('targets', list(self._nodes.keys()))
        audio_data = data.get('audio')  # Base64 encoded

        if not audio_data:
            return web.json_response({"error": "No audio data"}, status=400)

        import base64
        audio_bytes = base64.b64decode(audio_data)

        await self.router.route_audio(audio_bytes, targets)
        return web.json_response({"status": "ok", "targets": targets})

    async def _handle_dashboard(self, request: web.Request) -> web.Response:
        """Serve the web dashboard."""
        from .web.app import render_dashboard
        html = render_dashboard(self)
        return web.Response(text=html, content_type='text/html')

    # ─────────────────────────────────────────────────────────────
    # Plugin Handlers
    # ─────────────────────────────────────────────────────────────

    async def _handle_tts_bridge_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection for TTS bridge plugin."""
        tts_plugin = self.plugins.get("tts_bridge")
        if tts_plugin:
            return await tts_plugin.handle_websocket(request)
        return web.Response(status=503, text="TTS Bridge not available")

    async def _handle_stt_bridge_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection for STT bridge plugin."""
        stt_plugin = self.plugins.get("stt_bridge")
        if stt_plugin:
            return await stt_plugin.handle_websocket(request)
        return web.Response(status=503, text="STT Bridge not available")

    async def _api_get_plugins(self, request: web.Request) -> web.Response:
        """Get list of all plugins."""
        return web.json_response({
            "plugins": self.plugins.get_status()
        })

    async def _api_enable_plugin(self, request: web.Request) -> web.Response:
        """Enable a plugin."""
        plugin_id = request.match_info['plugin_id']
        if self.plugins.enable(plugin_id):
            return web.json_response({"status": "ok", "plugin_id": plugin_id, "enabled": True})
        return web.json_response({"error": "Plugin not found"}, status=404)

    async def _api_disable_plugin(self, request: web.Request) -> web.Response:
        """Disable a plugin."""
        plugin_id = request.match_info['plugin_id']
        if self.plugins.disable(plugin_id):
            return web.json_response({"status": "ok", "plugin_id": plugin_id, "enabled": False})
        return web.json_response({"error": "Plugin not found"}, status=404)

    async def _api_plugin_status(self, request: web.Request) -> web.Response:
        """Get plugin status."""
        plugin_id = request.match_info['plugin_id']
        plugin = self.plugins.get(plugin_id)
        if plugin:
            return web.json_response(plugin.get_status())
        return web.json_response({"error": "Plugin not found"}, status=404)

    # ─────────────────────────────────────────────────────────────
    # Audio Routing
    # ─────────────────────────────────────────────────────────────

    async def send_audio_to_node(self, node_id: str, audio_data: bytes):
        """Send audio data to a specific node."""
        if node_id in self._nodes:
            await self._nodes[node_id].send_audio(audio_data)

    async def broadcast_audio(self, audio_data: bytes, targets: Optional[Set[str]] = None):
        """Broadcast audio to multiple nodes."""
        if targets is None:
            targets = set(self._nodes.keys())

        for node_id in targets:
            if node_id in self._nodes:
                await self._nodes[node_id].send_audio(audio_data)


class NodeConnection:
    """Represents a connected audio node."""

    def __init__(
        self,
        node_id: str,
        ws: web.WebSocketResponse,
        sample_rate: int,
        audio_format: str,
        server: SkywireServer
    ):
        self.node_id = node_id
        self.ws = ws
        self.sample_rate = sample_rate
        self.audio_format = audio_format
        self.server = weakref.ref(server)

        self.connected_at = datetime.now()
        self.last_audio: Optional[datetime] = None
        self.volume = 100
        self.muted = False

        # Device capabilities (populated by node)
        self.input_devices = []
        self.output_devices = []
        self.active_input = None
        self.active_output = None

    async def send_json(self, data: dict):
        """Send JSON message to node."""
        if not self.ws.closed:
            await self.ws.send_json(data)

    async def send_audio(self, audio_data: bytes):
        """Send audio data to node."""
        if not self.ws.closed and not self.muted:
            self.last_audio = datetime.now()
            await self.ws.send_bytes(audio_data)

    async def handle_message(self, data: dict):
        """Handle JSON message from node."""
        msg_type = data.get('type')

        if msg_type == 'device_list':
            self.input_devices = data.get('input_devices', [])
            self.output_devices = data.get('output_devices', [])
            self.active_input = data.get('active_input')
            self.active_output = data.get('active_output')
            logger.debug(f"Node {self.node_id} devices: {len(self.input_devices)} in, {len(self.output_devices)} out")

        elif msg_type == 'pong':
            pass  # Keepalive response

        elif msg_type == 'status':
            logger.info(f"Node {self.node_id} status: {data}")

    async def handle_audio(self, audio_data: bytes):
        """Handle audio data from node (mic input)."""
        # Forward to router for STT or other processing
        server = self.server()
        if server:
            await server.router.handle_node_audio(self.node_id, audio_data)

    async def close(self):
        """Close connection."""
        if not self.ws.closed:
            await self.ws.close()


class SourceConnection:
    """Represents a connected audio source."""

    def __init__(
        self,
        source_id: str,
        name: str,
        ws: web.WebSocketResponse,
        server: SkywireServer
    ):
        self.source_id = source_id
        self.name = name
        self.ws = ws
        self.server = weakref.ref(server)
        self.connected_at = datetime.now()

        # Default routing for this source
        self.default_targets: Set[str] = set()

    async def send_json(self, data: dict):
        """Send JSON message to source."""
        if not self.ws.closed:
            await self.ws.send_json(data)

    async def handle_audio_message(self, data: dict):
        """Handle audio message with routing info."""
        import base64

        targets = data.get('targets', list(self.default_targets))
        audio_b64 = data.get('data')

        if audio_b64:
            audio_data = base64.b64decode(audio_b64)
            server = self.server()
            if server:
                await server.router.route_audio(audio_data, set(targets), source_id=self.source_id)

    async def handle_audio(self, audio_data: bytes):
        """Handle raw audio data - route to default targets."""
        server = self.server()
        if server:
            targets = self.default_targets or set(server.nodes.keys())
            await server.router.route_audio(audio_data, targets, source_id=self.source_id)

    async def close(self):
        """Close connection."""
        if not self.ws.closed:
            await self.ws.close()
