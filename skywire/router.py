"""
Skywire Audio Router

Handles routing of audio from sources to destination nodes.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .server import SkywireServer

logger = logging.getLogger(__name__)


class AudioRouter:
    """Routes audio from sources to destination nodes."""

    def __init__(self, server: 'SkywireServer'):
        self.server = server

        # Routing matrix: source_id -> set of node_ids
        self._routing: Dict[str, Set[str]] = {
            "tts": set(),      # TTS goes to configured nodes
            "music": set(),    # Music/media
            "system": set(),   # System sounds
            "default": set()   # Default routing for unknown sources
        }

        # Default targets when none specified
        self._default_targets: Set[str] = set()

        # Volume per source (0-100)
        self._source_volumes: Dict[str, int] = {}

        # Statistics
        self._stats = {
            "audio_routed": 0,
            "bytes_routed": 0,
            "last_audio": None
        }

    def get_routing(self) -> Dict[str, Any]:
        """Get current routing configuration."""
        return {
            "routing": {k: list(v) for k, v in self._routing.items()},
            "default_targets": list(self._default_targets),
            "source_volumes": self._source_volumes,
            "stats": self._stats
        }

    def set_routing(self, config: Dict[str, Any]):
        """Set routing configuration."""
        if 'routing' in config:
            for source, targets in config['routing'].items():
                self._routing[source] = set(targets)

        if 'default_targets' in config:
            self._default_targets = set(config['default_targets'])

        if 'source_volumes' in config:
            self._source_volumes.update(config['source_volumes'])

        logger.info(f"Routing updated: {len(self._routing)} sources configured")

    def set_source_targets(self, source_id: str, targets: Set[str]):
        """Set routing targets for a specific source."""
        self._routing[source_id] = targets
        logger.info(f"Source {source_id} -> {targets}")

    def add_target_to_source(self, source_id: str, node_id: str):
        """Add a target node to a source's routing."""
        if source_id not in self._routing:
            self._routing[source_id] = set()
        self._routing[source_id].add(node_id)

    def remove_target_from_source(self, source_id: str, node_id: str):
        """Remove a target node from a source's routing."""
        if source_id in self._routing:
            self._routing[source_id].discard(node_id)

    async def route_audio(
        self,
        audio_data: bytes,
        targets: Optional[Set[str]] = None,
        source_id: str = "default"
    ):
        """Route audio to target nodes."""
        # Determine targets
        if targets is None:
            targets = self._routing.get(source_id, self._default_targets)
            if not targets:
                targets = set(self.server.nodes.keys())  # All nodes

        if not targets:
            logger.warning(f"No targets for audio from {source_id}")
            return

        # Apply source volume if configured
        # TODO: Implement volume scaling

        # Send to all targets
        sent_count = 0
        for node_id in targets:
            if node_id in self.server.nodes:
                try:
                    await self.server.send_audio_to_node(node_id, audio_data)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send audio to {node_id}: {e}")

        # Update stats
        self._stats["audio_routed"] += 1
        self._stats["bytes_routed"] += len(audio_data) * sent_count
        self._stats["last_audio"] = datetime.now().isoformat()

        logger.debug(f"Routed {len(audio_data)} bytes from {source_id} to {sent_count} nodes")

    async def handle_node_audio(self, node_id: str, audio_data: bytes):
        """Handle audio received from a node (mic input)."""
        # This could be forwarded to STT or recorded
        # For now, just log it
        logger.debug(f"Received {len(audio_data)} bytes from node {node_id}")

        # TODO: Forward to STT service
        # TODO: Record/store audio
        # TODO: Route to other destinations (intercom mode?)

    async def broadcast_announcement(self, audio_data: bytes, priority: bool = False):
        """Broadcast an announcement to all nodes."""
        # TODO: Implement priority (interrupt current audio)
        await self.route_audio(audio_data, set(self.server.nodes.keys()), "announcement")

    def get_active_routes(self) -> Dict[str, list]:
        """Get currently active routes (only connected nodes)."""
        active = {}
        connected_nodes = set(self.server.nodes.keys())

        for source, targets in self._routing.items():
            active_targets = targets & connected_nodes
            if active_targets:
                active[source] = list(active_targets)

        return active
