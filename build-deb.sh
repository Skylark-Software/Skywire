#!/bin/bash
# Build Skywire Debian package
#
# Usage: ./build-deb.sh
#
# Copyright (c) 2026 Skylark Software LLC. All rights reserved.

set -e

VERSION="0.1.0"
PACKAGE="skywire"
ARCH="all"

echo "=== Building Skywire $VERSION ==="

# Clean previous builds
rm -rf build/ dist/ *.egg-info/ debian/.debhelper/ debian/skywire/

# Create output directory
mkdir -p dist

# Create build directory structure
BUILD_DIR="build/deb/${PACKAGE}_${VERSION}"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/lib/python3/dist-packages"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/etc/systemd/user"

# Copy Python packages
cp -r skywire "$BUILD_DIR/usr/lib/python3/dist-packages/"
cp -r client "$BUILD_DIR/usr/lib/python3/dist-packages/skywire_client"

# Create wrapper scripts
cat > "$BUILD_DIR/usr/bin/skywire" << 'EOF'
#!/usr/bin/env python3
from skywire.__main__ import run
run()
EOF
chmod +x "$BUILD_DIR/usr/bin/skywire"

cat > "$BUILD_DIR/usr/bin/skywire-tray" << 'EOF'
#!/usr/bin/env python3
from skywire.tray.app import main
main()
EOF
chmod +x "$BUILD_DIR/usr/bin/skywire-tray"

cat > "$BUILD_DIR/usr/bin/skywire-node" << 'EOF'
#!/usr/bin/env python3
from skywire_client.skywire_node import main
main()
EOF
chmod +x "$BUILD_DIR/usr/bin/skywire-node"

cat > "$BUILD_DIR/usr/bin/skywire-mcp" << 'EOF'
#!/usr/bin/env python3
from skywire.mcp.server import main
main()
EOF
chmod +x "$BUILD_DIR/usr/bin/skywire-mcp"

# Copy desktop file
cp debian/skywire.desktop "$BUILD_DIR/usr/share/applications/"

# Create systemd user service
cat > "$BUILD_DIR/etc/systemd/user/skywire-node.service" << 'EOF'
[Unit]
Description=Skywire Audio Node
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/skywire-node
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# Create control file
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: $PACKAGE
Version: $VERSION
Section: sound
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.9), python3-pyqt5, python3-websockets, python3-aiohttp, python3-yaml, python3-numpy, python3-jinja2, pipewire | pulseaudio
Maintainer: Jay Brame <jay@skylarksoftware.com>
Suggests: python3-mcp
Description: Distributed audio routing system
 Skywire is a software AV receiver for multi-room audio distribution.
 It routes audio from sources (TTS, media players) to speaker endpoints
 across your network.
 .
 Commands:
  - skywire: Audio routing server with web dashboard
  - skywire-tray: Desktop system tray application
  - skywire-node: Headless audio playback client
  - skywire-mcp: MCP server for AI model integration
EOF

# Create postinst script
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database -q /usr/share/applications || true
fi

echo ""
echo "Skywire installed successfully!"
echo ""
echo "Commands:"
echo "  skywire          - Start the audio routing server"
echo "  skywire-tray     - Start the system tray app"
echo "  skywire-node     - Start headless audio node"
echo "  skywire-mcp      - MCP server for AI integration"
echo ""
echo "To start on login, run:"
echo "  systemctl --user enable skywire-node"
echo ""
echo "For AI integration (requires: pip install mcp):"
echo "  skywire-mcp --skywire-url http://localhost:8080"
echo ""

exit 0
EOF
chmod +x "$BUILD_DIR/DEBIAN/postinst"

# Build the package
DEB_FILE="${PACKAGE}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$BUILD_DIR" "dist/$DEB_FILE"

echo ""
echo "=== Build Complete ==="
echo "Package: dist/$DEB_FILE"
echo ""
echo "Install with:"
echo "  sudo dpkg -i dist/$DEB_FILE"
echo "  sudo apt-get install -f  # Install dependencies"
echo ""
