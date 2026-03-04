"""
Skywire - Distributed Audio Routing System

A software AV receiver for multi-room audio distribution.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

__version__ = "0.1.0"
__author__ = "Jay Brame"

from .server import SkywireServer
from .router import AudioRouter

__all__ = ["SkywireServer", "AudioRouter"]
