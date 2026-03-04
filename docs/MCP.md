# Skywire MCP Server

Model Context Protocol server for AI-controlled audio routing.

The MCP server exposes Skywire's audio routing capabilities to AI models, enabling natural language control of multi-room audio systems.

## Installation

```bash
# Install MCP dependency
pip install mcp aiohttp

# If installed via Debian package, skywire-mcp is already available
# Otherwise, run directly:
python -m skywire.mcp.server --skywire-url http://localhost:8080
```

## Usage

### Command Line

```bash
skywire-mcp [OPTIONS]

Options:
  --skywire-url URL   Skywire server URL (default: http://localhost:8080)
  --debug             Enable debug logging
```

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skywire": {
      "command": "skywire-mcp",
      "args": ["--skywire-url", "http://skywire-host:8080"]
    }
  }
}
```

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "skywire": {
      "command": "skywire-mcp",
      "args": ["--skywire-url", "http://skywire-host:8080"]
    }
  }
}
```

## Available Tools

### skywire_list_nodes

List all connected audio nodes (speakers/endpoints).

**Parameters:** None

**Returns:**
```json
{
  "nodes": [
    {
      "node_id": "bedroom",
      "connected": true,
      "volume": 80,
      "muted": false,
      "sample_rate": 48000
    },
    {
      "node_id": "kitchen",
      "connected": true,
      "volume": 100,
      "muted": false,
      "sample_rate": 48000
    }
  ]
}
```

### skywire_list_sources

List all audio sources connected to Skywire.

**Parameters:** None

**Returns:**
```json
{
  "sources": [
    {
      "source_id": "tts",
      "name": "ThoughtMaker TTS",
      "connected": true
    },
    {
      "source_id": "music",
      "name": "MPD Player",
      "connected": false
    }
  ]
}
```

### skywire_get_routing

Get the current audio routing matrix.

**Parameters:** None

**Returns:**
```json
{
  "routing": {
    "tts": ["bedroom", "kitchen", "office"],
    "music": ["living_room"],
    "default": ["bedroom"]
  }
}
```

### skywire_set_routing

Route an audio source to specific nodes.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| source | string | Yes | Source ID (e.g., "tts", "music", "default") |
| nodes | array | Yes | List of node IDs to route to |

**Example:**
```json
{
  "source": "tts",
  "nodes": ["bedroom", "kitchen"]
}
```

**Returns:**
```json
{
  "success": true,
  "routing": {
    "tts": ["bedroom", "kitchen"]
  }
}
```

### skywire_set_volume

Set the volume level for an audio node.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| node_id | string | Yes | Node ID to adjust |
| volume | integer | Yes | Volume level (0-100) |

**Example:**
```json
{
  "node_id": "bedroom",
  "volume": 75
}
```

### skywire_set_mute

Mute or unmute an audio node.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| node_id | string | Yes | Node ID to mute/unmute |
| muted | boolean | Yes | True to mute, False to unmute |

**Example:**
```json
{
  "node_id": "bedroom",
  "muted": true
}
```

### skywire_play_tts

Send text-to-speech to specific nodes.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| text | string | Yes | Text to speak |
| nodes | array | No | Target nodes (uses default routing if empty) |

**Example:**
```json
{
  "text": "Dinner is ready!",
  "nodes": ["kitchen", "living_room"]
}
```

**Returns:**
```json
{
  "success": true,
  "text": "Dinner is ready!",
  "targets": ["kitchen", "living_room"]
}
```

### skywire_get_status

Get Skywire system health and status.

**Parameters:** None

**Returns:**
```json
{
  "status": "healthy",
  "uptime": 86400,
  "nodes_connected": 5,
  "sources_connected": 2,
  "version": "0.1.0"
}
```

### skywire_list_plugins

List all registered plugins.

**Parameters:** None

**Returns:**
```json
{
  "plugins": [
    {
      "plugin_id": "tts_bridge",
      "name": "TTS Bridge",
      "type": "bridge",
      "enabled": true
    },
    {
      "plugin_id": "stt_bridge",
      "name": "STT Bridge",
      "type": "bridge",
      "enabled": false
    }
  ]
}
```

### skywire_enable_plugin

Enable a plugin by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| plugin_id | string | Yes | Plugin ID to enable |

### skywire_disable_plugin

Disable a plugin by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| plugin_id | string | Yes | Plugin ID to disable |

## Example Conversations

### Listing Speakers

**User:** "What speakers are connected?"

**AI:** Uses `skywire_list_nodes`

**Response:** "You have 5 audio nodes connected: bedroom (80% volume), kitchen (100%), office (70%), living_room (muted), and garage (50%)."

### Playing Announcements

**User:** "Announce that dinner is ready in the kitchen and dining room"

**AI:** Uses `skywire_play_tts` with:
```json
{
  "text": "Dinner is ready!",
  "nodes": ["kitchen", "dining_room"]
}
```

**Response:** "I've announced 'Dinner is ready!' in the kitchen and dining room."

### Adjusting Volume

**User:** "Turn down the bedroom speakers to 50%"

**AI:** Uses `skywire_set_volume` with:
```json
{
  "node_id": "bedroom",
  "volume": 50
}
```

**Response:** "I've set the bedroom speakers to 50% volume."

### Managing Audio Routing

**User:** "Route music to all downstairs rooms"

**AI:** Uses `skywire_set_routing` with:
```json
{
  "source": "music",
  "nodes": ["kitchen", "living_room", "dining_room"]
}
```

**Response:** "Music is now playing in the kitchen, living room, and dining room."

### Muting Rooms

**User:** "Mute the office, I'm in a meeting"

**AI:** Uses `skywire_set_mute` with:
```json
{
  "node_id": "office",
  "muted": true
}
```

**Response:** "The office speakers are now muted."

## Error Handling

The MCP server returns structured error responses:

### Connection Error

```json
{
  "error": "connection_failed",
  "message": "Failed to connect to Skywire: Connection refused"
}
```

**Common causes:**
- Skywire server not running
- Wrong URL in `--skywire-url`
- Firewall blocking connection

### Unknown Tool

```json
{
  "error": "unknown_tool",
  "message": "Unknown tool: skywire_invalid_tool"
}
```

### Tool Error

```json
{
  "error": "tool_error",
  "message": "Node 'invalid_node' not found"
}
```

## Troubleshooting

### MCP server won't start

1. Check dependencies are installed:
   ```bash
   pip install mcp aiohttp
   ```

2. Verify Python version (3.9+ required):
   ```bash
   python3 --version
   ```

### Can't connect to Skywire

1. Verify Skywire server is running:
   ```bash
   curl http://skywire-host:8080/health
   ```

2. Check URL is correct (HTTP, not WebSocket):
   ```bash
   # Correct:
   skywire-mcp --skywire-url http://localhost:8080

   # Wrong:
   skywire-mcp --skywire-url ws://localhost:8765
   ```

### Tools not appearing in Claude

1. Restart Claude Desktop/Claude Code after config changes
2. Check config file syntax (valid JSON)
3. Verify `skywire-mcp` is in PATH:
   ```bash
   which skywire-mcp
   ```

### Debug mode

Enable verbose logging to troubleshoot issues:

```bash
skywire-mcp --skywire-url http://localhost:8080 --debug
```

## Architecture

```
┌─────────────────┐     stdio      ┌─────────────────┐     HTTP      ┌─────────────────┐
│  Claude Model   │ ◄────────────► │  skywire-mcp    │ ◄───────────► │  Skywire Server │
│  (Claude Code,  │    MCP JSON    │  (MCP Server)   │   REST API    │  (Port 8080)    │
│  Claude Desktop)│                └─────────────────┘               └─────────────────┘
└─────────────────┘                                                          │
                                                                             │ WebSocket
                                                                             ▼
                                                                   ┌─────────────────┐
                                                                   │  Audio Nodes    │
                                                                   │  (speakers)     │
                                                                   └─────────────────┘
```

The MCP server acts as a bridge between AI models and Skywire:

1. Claude sends tool calls via MCP protocol (stdio)
2. `skywire-mcp` translates to HTTP REST API calls
3. Skywire server executes commands and returns results
4. Results are formatted and returned to Claude

## Security Considerations

- The MCP server has full control over audio routing
- Run on trusted networks only
- Consider firewall rules to limit access to Skywire API
- No authentication currently implemented (planned for future)
