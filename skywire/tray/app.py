#!/usr/bin/env python3
"""
Skywire System Tray Application

Desktop system tray app for Skywire audio nodes with:
- Connection status indicator
- Volume control
- Mute toggle
- Quick reconnect
- Settings dialog

Copyright (c) 2026 Skylark Software LLC. All rights reserved.
"""

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox,
    QPushButton, QLineEdit, QDialog, QFormLayout, QMessageBox,
    QStyle
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("ERROR: websockets not installed. Run: pip install websockets")
    sys.exit(1)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("skywire-tray")

# Config
CONFIG_DIR = Path.home() / ".config" / "skywire"
CONFIG_FILE = CONFIG_DIR / "node.json"

DEFAULT_CONFIG = {
    "server": "ws://localhost:8765/audio",
    "node_id": socket.gethostname(),
    "sample_rate": 48000,
    "volume": 100,
    "muted": False,
    "auto_connect": True
}


@dataclass
class NodeState:
    """Current node state."""
    connected: bool = False
    server: str = ""
    node_id: str = ""
    volume: int = 100
    muted: bool = False
    last_audio: Optional[datetime] = None
    error: Optional[str] = None


class NodeWorker(QObject):
    """Background worker for WebSocket connection."""

    status_changed = pyqtSignal(bool, str)  # connected, message
    audio_received = pyqtSignal(int)  # bytes count
    error_occurred = pyqtSignal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self._running = False
        self._ws = None
        self._loop = None
        self._thread = None

    def start(self):
        """Start the worker thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the worker."""
        self._running = False
        if self._ws:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)

    def _run_loop(self):
        """Run the async event loop in background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())

    async def _connect_loop(self):
        """Connection loop with auto-reconnect."""
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.error_occurred.emit(str(e))
                self.status_changed.emit(False, str(e))

            if self._running:
                await asyncio.sleep(5)

    async def _connect(self):
        """Connect to Skywire server."""
        server = self.config.get("server", DEFAULT_CONFIG["server"])
        node_id = self.config.get("node_id", DEFAULT_CONFIG["node_id"])
        sample_rate = self.config.get("sample_rate", DEFAULT_CONFIG["sample_rate"])

        sep = "&" if "?" in server else "?"
        url = f"{server}{sep}node_id={node_id}&sample_rate={sample_rate}&format=pcm_s16le"

        logger.info(f"Connecting to {url}")
        self.status_changed.emit(False, "Connecting...")

        async with websockets.connect(
            url,
            max_size=50 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=10
        ) as ws:
            self._ws = ws

            # Receive welcome
            welcome = await ws.recv()
            data = json.loads(welcome)
            logger.info(f"Connected: {data}")
            self.status_changed.emit(True, "Connected")

            # Send capabilities
            await ws.send(json.dumps({
                "type": "device_list",
                "input_devices": [],
                "output_devices": [{"id": "0", "name": "Default", "channels": 2}],
                "active_input": "none",
                "active_output": "0"
            }))

            # Message loop
            async for message in ws:
                if isinstance(message, bytes):
                    self.audio_received.emit(len(message))
                    self._play_audio(message)
                else:
                    self._handle_control(json.loads(message))

    def _play_audio(self, audio_data: bytes):
        """Play audio through system audio."""
        import subprocess

        sample_rate = self.config.get("sample_rate", 48000)

        if self.config.get("muted", False):
            return

        try:
            # Try pw-cat first (PipeWire)
            cmd = ["pw-cat", "--playback", "--rate", str(sample_rate),
                   "--channels", "1", "--format", "s16", "-"]

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.stdin.write(audio_data)
            proc.stdin.close()
        except FileNotFoundError:
            # Fall back to paplay
            try:
                cmd = ["paplay", "--raw", f"--rate={sample_rate}",
                       "--channels=1", "--format=s16le"]
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                proc.stdin.write(audio_data)
                proc.stdin.close()
            except Exception as e:
                logger.error(f"Playback failed: {e}")

    def _handle_control(self, data: dict):
        """Handle control message."""
        msg_type = data.get("type")

        if msg_type == "set_volume":
            self.config["volume"] = data.get("volume", 100)
        elif msg_type == "set_mute":
            self.config["muted"] = data.get("muted", False)


class SettingsDialog(QDialog):
    """Settings dialog for node configuration."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle("Skywire Settings")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        # Server URL
        self.server_edit = QLineEdit(self.config.get("server", ""))
        self.server_edit.setPlaceholderText("ws://server:8765/audio")
        layout.addRow("Server:", self.server_edit)

        # Node ID
        self.node_id_edit = QLineEdit(self.config.get("node_id", ""))
        self.node_id_edit.setPlaceholderText(socket.gethostname())
        layout.addRow("Node ID:", self.node_id_edit)

        # Sample rate
        self.sample_rate_edit = QLineEdit(str(self.config.get("sample_rate", 48000)))
        layout.addRow("Sample Rate:", self.sample_rate_edit)

        # Auto connect
        self.auto_connect_check = QCheckBox("Connect on startup")
        self.auto_connect_check.setChecked(self.config.get("auto_connect", True))
        layout.addRow("", self.auto_connect_check)

        # Buttons
        btn_layout = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow("", btn_layout)

    def get_config(self) -> dict:
        """Get updated config."""
        return {
            "server": self.server_edit.text() or DEFAULT_CONFIG["server"],
            "node_id": self.node_id_edit.text() or socket.gethostname(),
            "sample_rate": int(self.sample_rate_edit.text() or 48000),
            "auto_connect": self.auto_connect_check.isChecked(),
            "volume": self.config.get("volume", 100),
            "muted": self.config.get("muted", False)
        }


class SkywireTray(QSystemTrayIcon):
    """Skywire system tray application."""

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.state = NodeState()
        self.worker: Optional[NodeWorker] = None

        # Load config
        self.config = self._load_config()

        # Setup UI
        self._setup_icon()
        self._setup_menu()

        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_display)
        self.status_timer.start(1000)

        # Auto-connect if configured
        if self.config.get("auto_connect", True):
            QTimer.singleShot(1000, self.connect)

        self.show()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _setup_icon(self):
        """Setup the tray icon."""
        self._update_icon()
        self.setToolTip(f"Skywire - {self.config.get('node_id', 'Unknown')}")

    def _update_icon(self):
        """Update icon based on connection state."""
        # Create a simple colored icon
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw speaker icon background
        if self.state.connected:
            color = QColor("#4ade80")  # Green
        elif self.state.error:
            color = QColor("#ef4444")  # Red
        else:
            color = QColor("#6b7280")  # Gray

        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, size - 8, size - 8)

        # Draw speaker symbol
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 24))

        if self.state.muted:
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "🔇")
        else:
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "🔊")

        painter.end()

        self.setIcon(QIcon(pixmap))

    def _setup_menu(self):
        """Setup the context menu."""
        menu = QMenu()

        # Status header
        self.status_action = QAction("Disconnected", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # Connect/Disconnect
        self.connect_action = QAction("Connect", menu)
        self.connect_action.triggered.connect(self._toggle_connection)
        menu.addAction(self.connect_action)

        menu.addSeparator()

        # Mute toggle
        self.mute_action = QAction("Mute", menu)
        self.mute_action.setCheckable(True)
        self.mute_action.setChecked(self.config.get("muted", False))
        self.mute_action.triggered.connect(self._toggle_mute)
        menu.addAction(self.mute_action)

        menu.addSeparator()

        # Settings
        settings_action = QAction("Settings...", menu)
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

        # Double-click to toggle connection
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_connection()

    def _toggle_connection(self):
        """Toggle connection state."""
        if self.state.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """Connect to Skywire server."""
        if self.worker:
            self.worker.stop()

        self.worker = NodeWorker(self.config)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.audio_received.connect(self._on_audio_received)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

        self.connect_action.setText("Disconnect")

    def disconnect(self):
        """Disconnect from server."""
        if self.worker:
            self.worker.stop()
            self.worker = None

        self.state.connected = False
        self.state.error = None
        self._update_icon()
        self._update_status_display()
        self.connect_action.setText("Connect")

    def _on_status_changed(self, connected: bool, message: str):
        """Handle connection status change."""
        self.state.connected = connected
        self.state.error = None if connected else message
        self._update_icon()
        self._update_status_display()

        if connected:
            self.showMessage(
                "Skywire",
                f"Connected to {self.config.get('server', 'server')}",
                QSystemTrayIcon.Information,
                2000
            )

    def _on_audio_received(self, byte_count: int):
        """Handle audio received."""
        self.state.last_audio = datetime.now()

    def _on_error(self, error: str):
        """Handle error."""
        self.state.error = error
        self._update_icon()

    def _update_status_display(self):
        """Update status display in menu."""
        if self.state.connected:
            status = f"● Connected - {self.config.get('node_id', 'Unknown')}"
            if self.state.last_audio:
                ago = (datetime.now() - self.state.last_audio).seconds
                status += f"\nLast audio: {ago}s ago"
        elif self.state.error:
            status = f"○ Error: {self.state.error[:30]}"
        else:
            status = "○ Disconnected"

        self.status_action.setText(status)
        self.connect_action.setText("Disconnect" if self.state.connected else "Connect")

    def _toggle_mute(self, checked: bool):
        """Toggle mute state."""
        self.config["muted"] = checked
        self.state.muted = checked
        self._save_config()
        self._update_icon()

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.config)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.get_config()
            self._save_config()
            self.setToolTip(f"Skywire - {self.config.get('node_id', 'Unknown')}")

            # Reconnect if connected
            if self.state.connected:
                self.disconnect()
                self.connect()

    def _quit(self):
        """Quit the application."""
        self.disconnect()
        self.app.quit()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Skywire")
    app.setApplicationDisplayName("Skywire Audio Node")

    # Check for system tray support
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None, "Skywire",
            "System tray is not available on this system."
        )
        sys.exit(1)

    tray = SkywireTray(app)

    # Handle signals
    signal.signal(signal.SIGINT, lambda *args: tray._quit())
    signal.signal(signal.SIGTERM, lambda *args: tray._quit())

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
