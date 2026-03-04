"""
Skywire Web Dashboard

Simple embedded web UI for controlling the audio router.

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import SkywireServer


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skywire - Audio Router</title>
    <style>
        :root {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-card: #0f3460;
            --accent: #e94560;
            --accent-hover: #ff6b6b;
            --text-primary: #eee;
            --text-secondary: #aaa;
            --success: #4ade80;
            --warning: #fbbf24;
            --error: #ef4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        header {
            background: var(--bg-secondary);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--bg-card);
        }

        .logo {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent);
        }

        .status {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--success);
        }

        .status-dot.offline {
            background: var(--error);
        }

        main {
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
        }

        .card h2 {
            font-size: 1rem;
            color: var(--text-secondary);
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .node-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .node-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            background: var(--bg-secondary);
            border-radius: 8px;
        }

        .node-info {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .node-name {
            font-weight: 500;
        }

        .node-meta {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .node-controls {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }

        .volume-slider {
            width: 80px;
            accent-color: var(--accent);
        }

        .btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.2s;
        }

        .btn:hover {
            background: var(--accent-hover);
        }

        .btn.secondary {
            background: var(--bg-secondary);
        }

        .btn.secondary:hover {
            background: var(--bg-card);
        }

        .routing-matrix {
            display: grid;
            gap: 0.5rem;
        }

        .routing-row {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.5rem;
        }

        .routing-source {
            width: 100px;
            font-weight: 500;
        }

        .routing-targets {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .routing-target {
            padding: 0.25rem 0.75rem;
            background: var(--bg-secondary);
            border-radius: 20px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .routing-target.active {
            background: var(--accent);
        }

        .routing-target:hover {
            opacity: 0.8;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            text-align: center;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }

        .stat-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .now-playing {
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .now-playing-icon {
            font-size: 2rem;
        }

        .now-playing-info {
            flex: 1;
        }

        .now-playing-title {
            font-weight: 500;
        }

        .now-playing-subtitle {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .empty-state {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .playing .status-dot {
            animation: pulse 1s infinite;
            background: var(--accent);
        }
    </style>
</head>
<body>
    <header>
        <div class="logo">🔊 Skywire</div>
        <div class="status">
            <div class="status-indicator">
                <div class="status-dot" id="server-status"></div>
                <span id="server-status-text">Connected</span>
            </div>
        </div>
    </header>

    <main>
        <div class="grid">
            <div class="card">
                <h2>Connected Nodes</h2>
                <div class="node-list" id="node-list">
                    <div class="empty-state">Loading...</div>
                </div>
            </div>

            <div class="card">
                <h2>Audio Sources</h2>
                <div class="node-list" id="source-list">
                    <div class="empty-state">No sources connected</div>
                </div>
            </div>

            <div class="card">
                <h2>Statistics</h2>
                <div class="stats">
                    <div>
                        <div class="stat-value" id="stat-nodes">0</div>
                        <div class="stat-label">Nodes</div>
                    </div>
                    <div>
                        <div class="stat-value" id="stat-sources">0</div>
                        <div class="stat-label">Sources</div>
                    </div>
                    <div>
                        <div class="stat-value" id="stat-plugins">0</div>
                        <div class="stat-label">Plugins</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Plugins</h2>
            <div class="node-list" id="plugin-list">
                <div class="empty-state">Loading plugins...</div>
            </div>
        </div>

        <div class="card">
            <h2>Routing Matrix</h2>
            <div class="routing-matrix" id="routing-matrix">
                <div class="empty-state">Configure routing below</div>
            </div>
        </div>

        <div class="card" style="margin-top: 1.5rem;">
            <h2>Now Playing</h2>
            <div class="now-playing" id="now-playing">
                <div class="now-playing-icon">🔇</div>
                <div class="now-playing-info">
                    <div class="now-playing-title">Nothing playing</div>
                    <div class="now-playing-subtitle">Waiting for audio...</div>
                </div>
            </div>
        </div>
    </main>

    <script>
        const API_BASE = '';  // Same origin

        async function fetchNodes() {
            try {
                const res = await fetch(`${API_BASE}/api/nodes`);
                const data = await res.json();
                updateNodeList(data.nodes);
            } catch (e) {
                console.error('Failed to fetch nodes:', e);
            }
        }

        async function fetchSources() {
            try {
                const res = await fetch(`${API_BASE}/api/sources`);
                const data = await res.json();
                updateSourceList(data.sources);
            } catch (e) {
                console.error('Failed to fetch sources:', e);
            }
        }

        async function fetchHealth() {
            try {
                const res = await fetch(`${API_BASE}/health`);
                const data = await res.json();
                updateStats(data);
            } catch (e) {
                document.getElementById('server-status').classList.add('offline');
                document.getElementById('server-status-text').textContent = 'Disconnected';
            }
        }

        async function fetchRouting() {
            try {
                const res = await fetch(`${API_BASE}/api/routing`);
                const data = await res.json();
                updateRoutingMatrix(data);
            } catch (e) {
                console.error('Failed to fetch routing:', e);
            }
        }

        function updateNodeList(nodes) {
            const container = document.getElementById('node-list');
            document.getElementById('stat-nodes').textContent = nodes.length;

            if (nodes.length === 0) {
                container.innerHTML = '<div class="empty-state">No nodes connected</div>';
                return;
            }

            container.innerHTML = nodes.map(node => `
                <div class="node-item">
                    <div class="node-info">
                        <div class="status-dot ${node.muted ? 'offline' : ''}"></div>
                        <div>
                            <div class="node-name">${node.id}</div>
                            <div class="node-meta">${node.sample_rate}Hz • ${node.format || 'pcm'}</div>
                        </div>
                    </div>
                    <div class="node-controls">
                        <input type="range" class="volume-slider" min="0" max="100"
                               value="${node.volume}" onchange="setVolume('${node.id}', this.value)">
                        <button class="btn secondary" onclick="toggleMute('${node.id}')">
                            ${node.muted ? '🔇' : '🔊'}
                        </button>
                    </div>
                </div>
            `).join('');
        }

        function updateSourceList(sources) {
            const container = document.getElementById('source-list');
            document.getElementById('stat-sources').textContent = sources.length;

            if (sources.length === 0) {
                container.innerHTML = '<div class="empty-state">No sources connected</div>';
                return;
            }

            container.innerHTML = sources.map(source => `
                <div class="node-item">
                    <div class="node-info">
                        <div class="status-dot"></div>
                        <div>
                            <div class="node-name">${source.name}</div>
                            <div class="node-meta">${source.id}</div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function updateStats(health) {
            document.getElementById('stat-nodes').textContent = health.nodes;
            document.getElementById('stat-sources').textContent = health.sources;
            document.getElementById('server-status').classList.remove('offline');
            document.getElementById('server-status-text').textContent = 'Connected';
        }

        async function fetchPlugins() {
            try {
                const res = await fetch(`${API_BASE}/api/plugins`);
                const data = await res.json();
                updatePluginList(data.plugins);
            } catch (e) {
                console.error('Failed to fetch plugins:', e);
            }
        }

        function updatePluginList(plugins) {
            const container = document.getElementById('plugin-list');
            document.getElementById('stat-plugins').textContent = plugins.length;

            if (plugins.length === 0) {
                container.innerHTML = '<div class="empty-state">No plugins registered</div>';
                return;
            }

            container.innerHTML = plugins.map(plugin => `
                <div class="node-item">
                    <div class="node-info">
                        <div class="status-dot ${plugin.running ? '' : 'offline'}"></div>
                        <div>
                            <div class="node-name">${plugin.name}</div>
                            <div class="node-meta">${plugin.type} • ${plugin.id}</div>
                        </div>
                    </div>
                    <div class="node-controls">
                        <button class="btn ${plugin.enabled ? 'secondary' : ''}"
                                onclick="togglePlugin('${plugin.id}', ${!plugin.enabled})">
                            ${plugin.enabled ? 'Disable' : 'Enable'}
                        </button>
                    </div>
                </div>
            `).join('');
        }

        async function togglePlugin(pluginId, enable) {
            const action = enable ? 'enable' : 'disable';
            await fetch(`${API_BASE}/api/plugin/${pluginId}/${action}`, {
                method: 'POST'
            });
            fetchPlugins();
        }

        function updateRoutingMatrix(data) {
            const container = document.getElementById('routing-matrix');
            const routing = data.routing || {};
            const nodes = Object.keys(routing).length > 0 ?
                [...new Set(Object.values(routing).flat())] : [];

            // Get all connected node IDs from the stats
            fetchNodes().then(() => {
                const allNodes = Array.from(document.querySelectorAll('.node-name'))
                    .map(el => el.textContent);

                const sources = ['tts', 'music', 'system', 'default'];

                container.innerHTML = sources.map(source => `
                    <div class="routing-row">
                        <div class="routing-source">${source}</div>
                        <div class="routing-targets">
                            ${allNodes.map(node => `
                                <span class="routing-target ${(routing[source] || []).includes(node) ? 'active' : ''}"
                                      onclick="toggleRoute('${source}', '${node}')">
                                    ${node}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            });
        }

        async function setVolume(nodeId, volume) {
            await fetch(`${API_BASE}/api/node/${nodeId}/volume`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({volume: parseInt(volume)})
            });
        }

        async function toggleMute(nodeId) {
            // Toggle mute - need to track current state
            await fetch(`${API_BASE}/api/node/${nodeId}/volume`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({muted: true})  // TODO: toggle properly
            });
            fetchNodes();
        }

        async function toggleRoute(source, node) {
            const res = await fetch(`${API_BASE}/api/routing`);
            const data = await res.json();
            const routing = data.routing || {};

            if (!routing[source]) routing[source] = [];

            const idx = routing[source].indexOf(node);
            if (idx >= 0) {
                routing[source].splice(idx, 1);
            } else {
                routing[source].push(node);
            }

            await fetch(`${API_BASE}/api/routing`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({routing})
            });

            fetchRouting();
        }

        // Initial fetch
        fetchHealth();
        fetchNodes();
        fetchSources();
        fetchPlugins();
        fetchRouting();

        // Refresh every 5 seconds
        setInterval(() => {
            fetchHealth();
            fetchNodes();
            fetchSources();
            fetchPlugins();
        }, 5000);
    </script>
</body>
</html>
"""


def render_dashboard(server: 'SkywireServer') -> str:
    """Render the dashboard HTML."""
    # For now, return static HTML
    # Could use Jinja2 for dynamic content later
    return DASHBOARD_HTML
