"""
Skywire Plugin Manager

Manages loading, lifecycle, and coordination of plugins.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type, Any
from pathlib import Path

from .base import Plugin, PluginType, SourcePlugin, SinkPlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages Skywire plugins."""

    def __init__(self, server):
        self.server = server
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_classes: Dict[str, Type[Plugin]] = {}

    @property
    def plugins(self) -> Dict[str, Plugin]:
        """Get all registered plugins."""
        return self._plugins

    def register_plugin_class(self, plugin_class: Type[Plugin]):
        """Register a plugin class for instantiation."""
        # Create temporary instance to get metadata
        temp = plugin_class.__new__(plugin_class)
        if hasattr(plugin_class, '__init__'):
            # Get default id from class
            plugin_id = getattr(plugin_class, 'PLUGIN_ID', plugin_class.__name__.lower())
            self._plugin_classes[plugin_id] = plugin_class
            logger.info(f"Registered plugin class: {plugin_id}")

    def register(self, plugin: Plugin):
        """Register a plugin instance."""
        plugin.set_server(self.server)

        # Set up audio callbacks for source plugins
        if isinstance(plugin, SourcePlugin):
            plugin.set_audio_callback(self._handle_source_audio)

        self._plugins[plugin.id] = plugin
        logger.info(f"Registered plugin: {plugin.name} ({plugin.id})")

    def unregister(self, plugin_id: str):
        """Unregister a plugin."""
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            logger.info(f"Unregistered plugin: {plugin_id}")

    def get(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self._plugins.get(plugin_id)

    def get_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of a specific type."""
        return [p for p in self._plugins.values() if p.plugin_type == plugin_type]

    def get_sources(self) -> List[SourcePlugin]:
        """Get all source plugins."""
        return [p for p in self._plugins.values() if isinstance(p, SourcePlugin)]

    def get_sinks(self) -> List[SinkPlugin]:
        """Get all sink plugins."""
        return [p for p in self._plugins.values() if isinstance(p, SinkPlugin)]

    async def start_all(self):
        """Start all enabled plugins."""
        for plugin in self._plugins.values():
            if plugin.enabled:
                try:
                    await plugin.start()
                    plugin._running = True
                    logger.info(f"Started plugin: {plugin.name}")
                except Exception as e:
                    logger.error(f"Failed to start plugin {plugin.name}: {e}")

    async def stop_all(self):
        """Stop all running plugins."""
        for plugin in self._plugins.values():
            if plugin._running:
                try:
                    await plugin.stop()
                    plugin._running = False
                    logger.info(f"Stopped plugin: {plugin.name}")
                except Exception as e:
                    logger.error(f"Failed to stop plugin {plugin.name}: {e}")

    async def _handle_source_audio(self, audio_data: bytes, targets: set, source_id: str):
        """Handle audio from a source plugin."""
        await self.server.router.route_audio(audio_data, targets, source_id)

    async def route_to_sinks(self, audio_data: bytes, source_id: str):
        """Route audio from nodes to sink plugins (e.g., STT)."""
        for sink in self.get_sinks():
            if sink.enabled and sink._running:
                # Check source filter
                if not sink.source_filter or source_id in sink.source_filter:
                    try:
                        await sink.receive_audio(audio_data, source_id)
                    except Exception as e:
                        logger.error(f"Sink {sink.name} error: {e}")

    def get_status(self) -> List[Dict[str, Any]]:
        """Get status of all plugins."""
        return [p.get_status() for p in self._plugins.values()]

    def enable(self, plugin_id: str) -> bool:
        """Enable a plugin."""
        if plugin_id in self._plugins:
            self._plugins[plugin_id].enabled = True
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        if plugin_id in self._plugins:
            self._plugins[plugin_id].enabled = False
            return True
        return False
