# Skywire

Distributed multi-room audio routing. A software AV receiver that connects speaker nodes across a network, routes audio sources to any combination of rooms, and captures microphone audio for speech recognition.

![Dashboard](docs/screenshots/dashboard.png)

Copyright (c) 2026 Skylark Software LLC. All rights reserved.

---

## What it does

- **Routes audio to any room** — TTS, music, system audio, or any WebSocket source can be directed to one room, a group of rooms, or broadcast everywhere
- **Per-room volume and mute** — each node has independent volume and mute control from the dashboard or tray
- **TTS switching** — one-click to direct speech to a specific room, or broadcast to all
- **STT microphone routing** — select which node's microphone feeds your speech-to-text service
- **Web dashboard** — visual routing matrix, live node status, and audio source monitoring
- **System tray** — desktop nodes show connection status, mic toggle, and mute in the taskbar
- **AI control via MCP** — Claude and other MCP-compatible models can control routing, volume, and STT source

---

## Architecture

```
Audio Sources                Skywire Server              Speaker Nodes
─────────────                ──────────────              ─────────────
TTS engine  ──────────────►  routing matrix  ◄────────►  Living Room 🔊🎤
Music/MPD   ──────────────►  web dashboard   ◄────────►  Kitchen     🔊🎤
System audio ─────────────►  REST API        ◄────────►  Bedroom     🔊🎤
                             MCP server      ◄────────►  Office      🔊🎤
STT engine  ◄─────────────   (mic audio)
```

The server runs centrally (Docker recommended). Nodes are lightweight processes running on any machine with speakers — desktop machines use the tray app, headless machines use the node service.

---

## Components

### Server

Runs in Docker on your central machine. Handles all WebSocket connections, the routing matrix, and serves the web dashboard.

```bash
docker compose -f packaging/docker/docker-compose.yml up -d
```

Dashboard at `http://localhost:9765` (or behind a reverse proxy).

### System Tray App (`skywire-tray`)

For desktop machines. Sits in the taskbar showing connection state — click to connect/disconnect, toggle mute, toggle microphone, or open settings.

| | |
|---|---|
| ![Tray menu](docs/screenshots/skywire-tray.png) | ![Settings](docs/screenshots/settings.png) |
| Right-click menu | Settings dialog |

- Blue icon = connected
- Gray icon = disconnected  
- Red icon = error
- Mic checkbox enables microphone capture for STT

### Headless Node (`skywire-node`)

For always-on endpoints (servers, Raspberry Pi, etc.). Runs as a systemd user service with auto-reconnect.

```bash
skywire-node --server wss://your-server/apps/skywire/audio --node-id kitchen
```

### MCP Server (`skywire-mcp`)

Exposes audio routing controls to AI models via the Model Context Protocol.

```json
{
  "mcpServers": {
    "skywire": {
      "command": "skywire-mcp",
      "args": ["--skywire-url", "https://your-server/apps/skywire"]
    }
  }
}
```

Available tools: `list_nodes`, `list_sources`, `get/set_routing`, `set_volume`, `set_mute`, `get/set_stt_source`, `get_status`.

---

## Requirements

### System Tray App (Linux)

The tray app requires the following system libraries:

```bash
# Debian/Ubuntu
sudo apt install libxdo3 libasound2-dev libgtk-3-dev

# Fedora
sudo dnf install libxdo alsa-lib-devel gtk3-devel
```

### Headless Node (Linux)

```bash
# Debian/Ubuntu
sudo apt install libasound2-dev

# Fedora
sudo dnf install alsa-lib-devel
```

### Building from Source

Requires Rust 1.75+ and Cargo:

```bash
cargo build --release -p skywire-tray
cargo build --release -p skywire-node
```

---

## Platform Compatibility

### Linux Distribution Support

Pre-built binaries require **OpenSSL 3.x** and **glibc 2.35+**:

| Distribution | Version | Status | Notes |
|--------------|---------|--------|-------|
| Ubuntu | 22.04+ | ✅ Supported | |
| Ubuntu | 20.04 | ❌ Not supported | OpenSSL 1.1 only |
| Debian | 12 (Bookworm)+ | ✅ Supported | |
| Debian | 11 (Bullseye) | ❌ Not supported | OpenSSL 1.1 only |
| Fedora | 36+ | ✅ Supported | |
| RHEL / Rocky / Alma | 9+ | ✅ Supported | |
| RHEL / Rocky / Alma | 8 | ❌ Not supported | OpenSSL 1.1 only |
| Arch Linux | Rolling | ✅ Supported | |
| openSUSE Tumbleweed | Rolling | ✅ Supported | |
| openSUSE Leap | 15.5+ | ⚠️ Untested | May require OpenSSL 3 |

### Runtime Dependencies

| Component | Required Libraries | Package (Debian/Ubuntu) | Package (Fedora/RHEL) |
|-----------|-------------------|-------------------------|----------------------|
| skywire-node | ALSA, OpenSSL 3 | `libasound2 libssl3` | `alsa-lib openssl` |
| skywire-tray | ALSA, OpenSSL 3, GTK3, libxdo | `libasound2 libssl3 libgtk-3-0 libxdo3` | `alsa-lib openssl gtk3 libxdo` |
| skywire-server | OpenSSL 3 | `libssl3` | `openssl` |

### Architecture

- **x86_64 (amd64)**: ✅ Fully supported
- **aarch64 (arm64)**: ⚠️ Build from source (Raspberry Pi 4/5, Apple Silicon VMs)
- **armv7 (armhf)**: ⚠️ Build from source (Raspberry Pi 3 and older)

### Audio Backend

Skywire uses **ALSA** directly on Linux. For best compatibility:

- Systems with **PulseAudio**: Works via PulseAudio's ALSA compatibility layer
- Systems with **PipeWire**: Works via PipeWire's ALSA compatibility layer
- **Headless servers**: Requires ALSA configured with a dummy or loopback device, or a real sound card

---

## Node Configuration

Each node reads `~/.config/skywire/node.json`:

```json
{
  "server": "wss://your-server/apps/skywire/audio",
  "node_id": "kitchen",
  "location": "Kitchen",
  "sample_rate": 16000,
  "volume": 100,
  "muted": false,
  "mic_enabled": true,
  "mic_device": "pulse",
  "auto_connect": true
}
```

| Field | Description |
|-------|-------------|
| `server` | Skywire server WebSocket URL |
| `node_id` | Unique identifier shown in dashboard |
| `location` | Human-readable room label (e.g. "Living Room") |
| `sample_rate` | Audio rate sent to server (16000 recommended for STT) |
| `mic_enabled` | Capture and stream microphone audio |
| `mic_device` | Mic device name (`pulse`, `default`, or device name) |
| `auto_connect` | Connect automatically on startup |

---

## Deployment

### Reverse Proxy (Caddy example)

```
handle_path /apps/skywire* {
    reverse_proxy localhost:9765
}
```

### Node as a systemd user service

```ini
[Unit]
Description=Skywire Audio Node
After=network-online.target sound.target

[Service]
ExecStart=/usr/local/bin/skywire-node
Restart=always
RestartSec=5
WatchdogSec=60

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now skywire-node
```

### Tray app autostart (KDE/GNOME)

`~/.config/autostart/skywire-tray.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Skywire Tray
Exec=/usr/local/bin/skywire-tray
X-KDE-AutostartEnabled=true
```

---

## Audio sources (TTS/STT integration)

Sources connect via WebSocket to `/source` and send raw PCM or base64-wrapped JSON:

```json
{ "type": "audio", "data": "<base64-pcm>", "targets": ["kitchen", "bedroom"] }
```

STT engines connect to `/stt` and receive raw PCM from whichever nodes are selected as the active microphone source in the dashboard.

---

## License

Copyright (c) 2026 Skylark Software LLC. All rights reserved.

This software is the proprietary property of Skylark Software LLC. Unauthorized copying, distribution, or modification is strictly prohibited. See [LICENSE](LICENSE).
