#!/bin/bash

echo "🤖 Installing Jaavis..."

# 1. Determine local path
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JAAVIS_CORE="$INSTALL_DIR/src/jaavis_core.py"
LOGO_PATH="$INSTALL_DIR/src/logo.md"

# 2. Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 is not installed."
    exit 1
fi

# 3. Create Symlink
echo "🔗 linking $JAAVIS_CORE to /usr/local/bin/jaavis..."
sudo ln -sf "$JAAVIS_CORE" /usr/local/bin/jaavis

# 4. Initialize Library if missing
LIB_DIR="$HOME/jaavis-library"
if [ ! -d "$LIB_DIR" ]; then
    echo "📚 Initializing default library at $LIB_DIR..."
    mkdir -p "$LIB_DIR/templates"
    cp -r "$INSTALL_DIR/library/templates/" "$LIB_DIR/templates/"
else
    echo "✅ Library found at $LIB_DIR"
fi

echo "✨ Jaavis Installed! Type 'jaavis' to start."
