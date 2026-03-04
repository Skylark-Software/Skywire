#!/usr/bin/env python3
"""
Skywire - Distributed Audio Routing System

Entry point for running the Skywire server.
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from .server import SkywireServer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("skywire")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Skywire - Distributed Audio Routing System"
    )
    parser.add_argument(
        "--host", "-H",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8765,
        help="WebSocket/Web port (default: 8765)"
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to config file (YAML)"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config if provided
    config = None
    if args.config and args.config.exists():
        import yaml
        with open(args.config) as f:
            config = yaml.safe_load(f)

    # Create server
    server = SkywireServer(
        host=args.host,
        websocket_port=args.port,
        config=config
    )

    # Handle shutdown
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Start server
    await server.start()

    logger.info("Skywire is running. Press Ctrl+C to stop.")

    # Wait for shutdown
    await shutdown_event.wait()
    await server.stop()


def run():
    """Entry point for console script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
