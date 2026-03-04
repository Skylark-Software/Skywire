# Skywire

Distributed audio routing system - a software AV receiver for multi-room audio.

## Features

- **Multi-room audio** - Route audio to any connected node
- **Multiple sources** - TTS, music, system audio, streams
- **Web dashboard** - Visual routing matrix control
- **Always-on nodes** - Reliable audio endpoints with auto-reconnect
- **ThoughtMaker integration** - Receives TTS from ThoughtMaker modules

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

## Quick Start

### Server

```bash
# Install
pip install -e .

# Run
skywire --port 8765 --web-port 8080

# Or with Docker
docker-compose up -d
```

### Node Client

```bash
# On each audio endpoint
pip install skywire-node

skywire-node --server ws://skywire-host:8765 --node-id bedroom
```

## Configuration

### Server (`config.yaml`)

```yaml
server:
  websocket_port: 8765
  web_port: 8080
  host: 0.0.0.0

sources:
  tts:
    enabled: true
    port: 8766  # ThoughtMaker connects here
  pipewire:
    enabled: true
    capture_device: null  # Auto-detect

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

### Node (`node.yaml`)

```yaml
server: ws://skywire-host:8765
node_id: bedroom
sample_rate: 48000
auto_reconnect: true
playback:
  method: pipewire  # or pulseaudio, alsa
  device: null  # Auto-detect
```

## API

### WebSocket Protocol

**Node Connection:**
```
GET /audio?node_id=bedroom&sample_rate=48000
```

**Source Connection:**
```
GET /source?source_id=tts&name=ThoughtMaker%20TTS
```

**Messages:**

```json
// Node → Server: Device capabilities
{"type": "capabilities", "outputs": [...], "inputs": [...]}

// Server → Node: Audio data
Binary PCM data (int16, little-endian)

// Server → Node: Control
{"type": "set_volume", "volume": 80}
{"type": "set_mute", "muted": true}

// Source → Server: Audio with routing
{"type": "audio", "targets": ["bedroom", "office"], "data": "base64..."}
```

### REST API

```
GET  /api/nodes          - List connected nodes
GET  /api/sources        - List audio sources
GET  /api/routing        - Get routing matrix
POST /api/routing        - Update routing
POST /api/node/{id}/volume - Set node volume
POST /api/play           - Play audio to nodes
```

## Integration

### ThoughtMaker

Connect ThoughtMaker's TTS module to Skywire:

```python
# In ThoughtMaker config
tts:
  remote_playback: true
  skywire_url: ws://skywire-host:8766
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
```

## Development

```bash
# Clone
git clone git@skylark.labrack.me:jbrame/Skywire.git
cd Skywire

# Install dev dependencies
pip install -e ".[dev]"

# Run in dev mode
skywire --debug
```

## License

Copyright (c) 2026 Skylark Software LLC. All rights reserved.

This is proprietary software. See [LICENSE](LICENSE) for details.
