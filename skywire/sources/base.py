"""
Base Audio Source

Abstract base class for audio sources.
"""

from abc import ABC, abstractmethod
from typing import Set, Callable, Optional
import asyncio


class AudioSource(ABC):
    """Abstract base class for audio sources."""

    def __init__(self, source_id: str, name: str):
        self.source_id = source_id
        self.name = name
        self.enabled = True
        self.default_targets: Set[str] = set()
        self._on_audio: Optional[Callable[[bytes, Set[str]], None]] = None

    def set_audio_callback(self, callback: Callable[[bytes, Set[str]], None]):
        """Set callback for when audio is available."""
        self._on_audio = callback

    @abstractmethod
    async def start(self):
        """Start capturing/generating audio."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop capturing/generating audio."""
        pass

    async def emit_audio(self, audio_data: bytes, targets: Optional[Set[str]] = None):
        """Emit audio to be routed."""
        if self._on_audio and self.enabled:
            target_set = targets if targets is not None else self.default_targets
            await self._on_audio(audio_data, target_set)
