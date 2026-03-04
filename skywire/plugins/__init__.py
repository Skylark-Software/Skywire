"""
Skywire Plugin System

Extensible plugin architecture for audio sources, sinks, and processors.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

from .base import Plugin, PluginType
from .manager import PluginManager

__all__ = ["Plugin", "PluginType", "PluginManager"]
