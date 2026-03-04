"""
Skywire Plugin Base Classes

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins."""
    SOURCE = "source"       # Produces audio (TTS, media player, etc.)
    SINK = "sink"           # Consumes audio (STT, recorder, etc.)
    PROCESSOR = "processor" # Transforms audio (effects, mixing, etc.)
    BRIDGE = "bridge"       # Connects external systems (ThoughtMaker, Home Assistant)


@dataclass
class PluginInfo:
    """Plugin metadata."""
    id: str
    name: str
    type: PluginType
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """Base class for all Skywire plugins."""

    def __init__(self, plugin_id: str, name: str, plugin_type: PluginType):
        self.info = PluginInfo(
            id=plugin_id,
            name=name,
            type=plugin_type
        )
        self._server = None
        self._running = False
        self.logger = logging.getLogger(f"skywire.plugin.{plugin_id}")

    @property
    def id(self) -> str:
        return self.info.id

    @property
    def name(self) -> str:
        return self.info.name

    @property
    def plugin_type(self) -> PluginType:
        return self.info.type

    @property
    def enabled(self) -> bool:
        return self.info.enabled

    @enabled.setter
    def enabled(self, value: bool):
        self.info.enabled = value

    def set_server(self, server):
        """Set reference to Skywire server."""
        self._server = server

    @abstractmethod
    async def start(self):
        """Start the plugin."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the plugin."""
        pass

    def get_config(self) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self.info.config

    def set_config(self, config: Dict[str, Any]):
        """Update plugin configuration."""
        self.info.config.update(config)

    def get_status(self) -> Dict[str, Any]:
        """Get plugin status."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.plugin_type.value,
            "enabled": self.enabled,
            "running": self._running
        }


class SourcePlugin(Plugin):
    """Plugin that produces audio (TTS, media, etc.)."""

    def __init__(self, plugin_id: str, name: str):
        super().__init__(plugin_id, name, PluginType.SOURCE)
        self._on_audio: Optional[Callable] = None
        self.default_targets: set = set()

    def set_audio_callback(self, callback: Callable):
        """Set callback for when audio is available."""
        self._on_audio = callback

    async def emit_audio(self, audio_data: bytes, targets: Optional[set] = None):
        """Emit audio to be routed."""
        if self._on_audio and self.enabled:
            target_set = targets if targets is not None else self.default_targets
            await self._on_audio(audio_data, target_set, self.id)


class SinkPlugin(Plugin):
    """Plugin that consumes audio (STT, recorder, etc.)."""

    def __init__(self, plugin_id: str, name: str):
        super().__init__(plugin_id, name, PluginType.SINK)
        self.source_filter: set = set()  # Which nodes/sources to accept audio from

    @abstractmethod
    async def receive_audio(self, audio_data: bytes, source_id: str):
        """Receive audio data."""
        pass


class ProcessorPlugin(Plugin):
    """Plugin that transforms audio."""

    def __init__(self, plugin_id: str, name: str):
        super().__init__(plugin_id, name, PluginType.PROCESSOR)

    @abstractmethod
    async def process_audio(self, audio_data: bytes) -> bytes:
        """Process and return transformed audio."""
        pass


class BridgePlugin(Plugin):
    """Plugin that bridges external systems."""

    def __init__(self, plugin_id: str, name: str):
        super().__init__(plugin_id, name, PluginType.BRIDGE)
