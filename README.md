# Skywire

Distributed audio routing system - a software AV receiver for multi-room audio.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.

## Features

- **Multi-room audio** - Route audio to any connected node on your network
- **Multiple sources** - TTS, music, system audio, streams
- **Web dashboard** - Visual routing matrix control at a glance
- **System tray app** - Desktop integration with volume/mute controls
- **Headless nodes** - Always-on audio endpoints with auto-reconnect
- **Plugin system** - Extensible TTS/STT bridges and audio processors
- **MCP server** - AI model integration via Model Context Protocol
- **Debian packaging** - Easy installation via `apt install skywire`

## Architecture

```
Sources                          Skywire Server                   Destinations
───────                          ──────────────                   ────────────
┌─────────────┐                 ┌──────────────┐                 ┌─────────────┐
│ TTS Engine  │────────────────►│              │────────────────►│ bedroom     │
└─────────────┘                 │   Routing    │                 └─────────────┘
┌─────────────┐                 │   Matrix     │                 ┌─────────────┐
│ Music/MPD   │────────────────►│              │────────────────►│ office      │
└─────────────┘                 │   WebSocket  │                 └─────────────┘
┌─────────────┐                 │   Server     │                 ┌─────────────┐
│ PipeWire    │────────────────►│              │────────────────►│ kitchen     │
└─────────────┘                 │   Web UI     │                 └─────────────┘
                                └──────────────┘
```

## Installation

### Debian/Ubuntu (Recommended)

```bash
# Download and install
sudo dpkg -i skywire_0.1.0_all.deb
sudo apt-get install -f  # Install dependencies

# This provides four commands:
#   skywire       - Audio routing server
#   skywire-tray  - System tray application
#   skywire-node  - Headless audio node client
#   skywire-mcp   - MCP server for AI integration
```

### From Source

```bash
git clone git@github.com:Skylark-Software/Skywire.git
cd Skywire
pip install -e .
```

### Build Debian Package

```bash
./build-deb.sh
# Creates dist/skywire_0.1.0_all.deb
```

## Quick Start

### 1. Start the Server

```bash
# Run the Skywire server (on your central machine)
skywire --port 8765 --web-port 8080

# Or specify host for network access
skywire --host 0.0.0.0 --port 8765 --web-port 8080
```

Access the web dashboard at `http://localhost:8080`

### 2. Connect Audio Nodes

**Option A: System Tray App (Desktop)**

```bash
# On desktop machines with speakers
skywire-tray
```

Right-click the tray icon to configure server address and node settings.

**Option B: Headless Node (Servers/Raspberry Pi)**

```bash
# On headless audio endpoints
skywire-node --server ws://skywire-host:8765/audio --node-id kitchen
```

**Option C: Systemd Service (Always-on)**

```bash
# Enable auto-start on login
systemctl --user enable skywire-node
systemctl --user start skywire-node
```

### 3. Route Audio

Open the web dashboard and use the routing matrix to send audio from sources to destination nodes.

## Components

### Server (`skywire`)

The central audio routing hub:

- WebSocket server for node connections
- REST API for control
- Web dashboard for visual management
- Plugin system for extensibility

```bash
skywire [OPTIONS]

Options:
  --host TEXT       Host to bind to (default: 0.0.0.0)
  --port INTEGER    WebSocket port (default: 8765)
  --web-port INT    Web dashboard port (default: 8080)
  --config PATH     Configuration file
  --debug           Enable debug logging
```

### System Tray App (`skywire-tray`)

Desktop application for audio nodes:

- Connection status indicator (sky blue = connected, red = error, gray = disconnected)
- Volume slider and mute toggle
- Settings dialog for server configuration
- Auto-connect on startup
- Double-click to toggle connection

Configuration stored in `~/.config/skywire/node.json`

### Headless Node (`skywire-node`)

Command-line audio endpoint for always-on systems:

- Auto-reconnect with exponential backoff
- PipeWire, PulseAudio, and ALSA support
- Low resource usage

```bash
skywire-node [OPTIONS]

Options:
  --server URL      Skywire server URL (default: ws://localhost:8765/audio)
  --node-id TEXT    Node identifier (default: hostname)
  --sample-rate INT Audio sample rate (default: 48000)
```

### MCP Server (`skywire-mcp`)

Model Context Protocol server for AI integration:

- Expose audio routing controls to AI models
- List/control nodes, sources, and routing
- Play TTS to specific rooms
- Compatible with Claude Desktop, Claude Code, and other MCP clients

```bash
# Install MCP dependency
pip install mcp

# Run MCP server
skywire-mcp --skywire-url http://localhost:8080
```

**Available Tools:**

| Tool | Description |
|------|-------------|
| `skywire_list_nodes` | List connected audio nodes |
| `skywire_list_sources` | List audio sources |
| `skywire_get_routing` | Get current routing matrix |
| `skywire_set_routing` | Route source to nodes |
| `skywire_set_volume` | Set node volume (0-100) |
| `skywire_set_mute` | Mute/unmute a node |
| `skywire_play_tts` | Send TTS to nodes |
| `skywire_get_status` | System health check |
| `skywire_list_plugins` | List registered plugins |
| `skywire_enable_plugin` | Enable a plugin |
| `skywire_disable_plugin` | Disable a plugin |

**Claude Desktop Configuration:**

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

**Example AI Interactions:**

- "What speakers are connected?" → `skywire_list_nodes`
- "Play an announcement in the kitchen" → `skywire_play_tts`
- "Mute the bedroom" → `skywire_set_mute`
- "Route music to all rooms" → `skywire_set_routing`

## Configuration

### Server (`config.yaml`)

```yaml
server:
  websocket_port: 8765
  web_port: 8080
  host: 0.0.0.0

plugins:
  tts_bridge:
    enabled: true
    port: 8766
  stt_bridge:
    enabled: true

nodes:
  bedroom:
    display_name: "Bedroom Speakers"
    default_volume: 80
  office:
    display_name: "Office"
    default_volume: 70

routing:
  default_targets: [bedroom, office]
  tts_targets: [bedroom]
```

### Node (`~/.config/skywire/node.json`)

```json
{
  "server": "ws://skywire-host:8765/audio",
  "node_id": "bedroom",
  "sample_rate": 48000,
  "volume": 100,
  "muted": false,
  "auto_connect": true
}
```

## Plugin System

Skywire supports plugins for extending functionality:

| Type | Purpose |
|------|---------|
| **Source** | Audio input (TTS, music players) |
| **Sink** | Audio output (custom endpoints) |
| **Processor** | Audio effects (EQ, compression) |
| **Bridge** | External service integration |

### Built-in Plugins

- **TTS Bridge** - Receives synthesized speech from TTS engines
- **STT Bridge** - Forwards microphone audio to speech recognition

### Creating a Plugin

```python
from skywire.plugins.base import SourcePlugin

class MyAudioSource(SourcePlugin):
    """Custom audio source plugin."""

    def __init__(self):
        super().__init__(
            plugin_id="my-source",
            name="My Audio Source",
            description="Custom audio input"
        )

    async def start(self):
        # Initialize your audio source
        pass

    async def stop(self):
        # Cleanup
        pass
```

## API Reference

### WebSocket Protocol

**Node Connection:**
```
GET /audio?node_id=bedroom&sample_rate=48000&format=pcm_s16le
```

**Source Connection:**
```
GET /source?source_id=tts&name=ThoughtMaker%20TTS
```

**Messages:**

```javascript
// Server → Node: Welcome
{"type": "welcome", "node_id": "bedroom"}

// Node → Server: Device capabilities
{"type": "device_list", "input_devices": [], "output_devices": [...]}

// Server → Node: Audio data (binary)
// PCM int16 little-endian audio frames

// Server → Node: Volume control
{"type": "set_volume", "volume": 80}
{"type": "set_mute", "muted": true}
```

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |
| `/api/nodes` | GET | List connected nodes |
| `/api/sources` | GET | List audio sources |
| `/api/plugins` | GET | List registered plugins |
| `/api/routing` | GET | Get routing matrix |
| `/api/routing` | POST | Update routing matrix |
| `/api/node/{id}/volume` | POST | Set node volume |
| `/api/plugin/{id}/enable` | POST | Enable plugin |
| `/api/plugin/{id}/disable` | POST | Disable plugin |

## Integration

### ThoughtMaker

ThoughtMaker's TTS module has built-in Skywire integration for distributed speech output.

**Enable in code:**

```python
# Configure TTS module for Skywire
tts_module.set_skywire(
    enabled=True,
    url="ws://skywire-host:8766/plugin/tts",
    targets=["bedroom", "kitchen"]  # Default playback nodes
)

# Connect
await tts_module.connect_skywire()
```

**Per-request targeting:**

```python
# Speak to specific rooms
await tts_module._synthesize("Dinner is ready!", {
    'skywire_targets': ['kitchen', 'living_room']
})
```

**Protocol:**

ThoughtMaker connects to `ws://skywire:8766/plugin/tts` and sends:

```json
{
  "type": "audio",
  "data": "<base64-encoded-pcm>",
  "targets": ["bedroom", "kitchen"],
  "format": "wav"
}
```

### Home Assistant

```yaml
# configuration.yaml
rest_command:
  skywire_announce:
    url: "http://skywire-host:8080/api/play"
    method: POST
    content_type: "application/json"
    payload: '{"text": "{{ message }}", "targets": {{ targets }}}'

# Example automation
automation:
  - trigger:
      platform: state
      entity_id: binary_sensor.front_door
      to: "on"
    action:
      service: rest_command.skywire_announce
      data:
        message: "Front door opened"
        targets: '["kitchen", "living_room"]'
```

### MPD/Music Player Daemon

Route MPD audio through Skywire using PipeWire:

```bash
# Create a PipeWire loopback that Skywire captures
pw-loopback -C mpd_output -P skywire_input
```

## Deployment

### Systemd User Service

The Debian package installs a systemd user service:

```bash
# Enable auto-start for headless node
systemctl --user enable skywire-node
systemctl --user start skywire-node

# Check status
systemctl --user status skywire-node
```

### Desktop Autostart

For the tray app, create `~/.config/autostart/skywire-tray.desktop`:

```ini
[Desktop Entry]
Name=Skywire
Comment=Skywire Audio Node
Exec=skywire-tray
Type=Application
Terminal=false
X-GNOME-Autostart-enabled=true
```

## Requirements

- Python 3.9+
- PyQt5 (for tray app)
- aiohttp, websockets
- PipeWire or PulseAudio (for audio playback)

## Development

```bash
# Clone repository
git clone git@github.com:Skylark-Software/Skywire.git
cd Skywire

# Install in development mode
pip install -e .

# Run server with debug logging
skywire --debug

# Run tests
pytest
```

## License

Copyright (c) 2026 Skylark Software LLC. All rights reserved.

This is proprietary software. Unauthorized copying, modification, or distribution is prohibited.
