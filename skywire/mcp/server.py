#!/usr/bin/env python3
"""
Skywire MCP Server

Model Context Protocol server exposing audio routing controls to AI models.

Usage:
    skywire-mcp --skywire-url http://localhost:8080

Or in Claude Desktop config:
    {
        "mcpServers": {
            "skywire": {
                "command": "skywire-mcp",
                "args": ["--skywire-url", "http://skywire-host:8080"]
            }
        }
    }

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp not installed. Run: pip install aiohttp", file=sys.stderr)
    sys.exit(1)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skywire-mcp")


class SkywireClient:
    """HTTP client for Skywire REST API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get(self, path: str) -> dict:
        """GET request to Skywire API."""
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def post(self, path: str, data: dict = None) -> dict:
        """POST request to Skywire API."""
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        async with session.post(url, json=data or {}) as resp:
            resp.raise_for_status()
            return await resp.json()


def create_server(skywire_url: str) -> Server:
    """Create the MCP server with Skywire tools."""

    server = Server("skywire")
    client = SkywireClient(skywire_url)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Skywire control tools."""
        return [
            Tool(
                name="skywire_list_nodes",
                description="List all connected audio nodes (speakers/endpoints) on the network. Returns node IDs, connection status, volume levels, and mute state.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="skywire_list_sources",
                description="List all audio sources (TTS, music players, etc.) connected to Skywire.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="skywire_get_routing",
                description="Get the current audio routing matrix showing which sources are routed to which nodes.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="skywire_set_routing",
                description="Route an audio source to specific nodes. Use this to control where audio plays.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source ID to route (e.g., 'tts', 'music', 'default')"
                        },
                        "nodes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of node IDs to route audio to (e.g., ['bedroom', 'kitchen'])"
                        }
                    },
                    "required": ["source", "nodes"]
                }
            ),
            Tool(
                name="skywire_set_volume",
                description="Set the volume level for an audio node.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "Node ID to adjust volume for"
                        },
                        "volume": {
                            "type": "integer",
                            "description": "Volume level (0-100)",
                            "minimum": 0,
                            "maximum": 100
                        }
                    },
                    "required": ["node_id", "volume"]
                }
            ),
            Tool(
                name="skywire_set_mute",
                description="Mute or unmute an audio node.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "Node ID to mute/unmute"
                        },
                        "muted": {
                            "type": "boolean",
                            "description": "True to mute, False to unmute"
                        }
                    },
                    "required": ["node_id", "muted"]
                }
            ),
            Tool(
                name="skywire_play_tts",
                description="Send text-to-speech audio to specific nodes. The text will be synthesized and played through the specified speakers.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to speak"
                        },
                        "nodes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of node IDs to play audio on. If empty, uses default routing."
                        }
                    },
                    "required": ["text"]
                }
            ),
            Tool(
                name="skywire_get_status",
                description="Get Skywire system status including connected nodes, sources, and health.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="skywire_list_plugins",
                description="List all registered plugins (TTS bridge, STT bridge, processors, etc.).",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="skywire_enable_plugin",
                description="Enable a plugin by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plugin_id": {
                            "type": "string",
                            "description": "Plugin ID to enable"
                        }
                    },
                    "required": ["plugin_id"]
                }
            ),
            Tool(
                name="skywire_disable_plugin",
                description="Disable a plugin by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plugin_id": {
                            "type": "string",
                            "description": "Plugin ID to disable"
                        }
                    },
                    "required": ["plugin_id"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        try:
            result = await _handle_tool(client, name, arguments)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        except aiohttp.ClientError as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "connection_failed",
                    "message": f"Failed to connect to Skywire: {e}"
                }, indent=2)
            )]
        except Exception as e:
            logger.exception("Tool error")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "tool_error",
                    "message": str(e)
                }, indent=2)
            )]

    return server


async def _handle_tool(client: SkywireClient, name: str, args: dict) -> dict:
    """Handle individual tool calls."""

    if name == "skywire_list_nodes":
        return await client.get("/api/nodes")

    elif name == "skywire_list_sources":
        return await client.get("/api/sources")

    elif name == "skywire_get_routing":
        return await client.get("/api/routing")

    elif name == "skywire_set_routing":
        source = args["source"]
        nodes = args["nodes"]
        # Get current routing and update
        current = await client.get("/api/routing")
        routing = current.get("routing", {})
        routing[source] = nodes
        return await client.post("/api/routing", {"routing": routing})

    elif name == "skywire_set_volume":
        node_id = args["node_id"]
        volume = args["volume"]
        return await client.post(f"/api/node/{node_id}/volume", {"volume": volume})

    elif name == "skywire_set_mute":
        node_id = args["node_id"]
        muted = args["muted"]
        return await client.post(f"/api/node/{node_id}/volume", {"muted": muted})

    elif name == "skywire_play_tts":
        text = args["text"]
        nodes = args.get("nodes", [])
        return await client.post("/api/play", {"text": text, "targets": nodes})

    elif name == "skywire_get_status":
        return await client.get("/health")

    elif name == "skywire_list_plugins":
        return await client.get("/api/plugins")

    elif name == "skywire_enable_plugin":
        plugin_id = args["plugin_id"]
        return await client.post(f"/api/plugin/{plugin_id}/enable")

    elif name == "skywire_disable_plugin":
        plugin_id = args["plugin_id"]
        return await client.post(f"/api/plugin/{plugin_id}/disable")

    else:
        return {"error": "unknown_tool", "message": f"Unknown tool: {name}"}


async def run_server(skywire_url: str):
    """Run the MCP server."""
    server = create_server(skywire_url)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Skywire MCP Server - AI-controlled audio routing"
    )
    parser.add_argument(
        "--skywire-url",
        default="http://localhost:8080",
        help="Skywire server URL (default: http://localhost:8080)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Starting Skywire MCP server, connecting to {args.skywire_url}")

    asyncio.run(run_server(args.skywire_url))


if __name__ == "__main__":
    main()
