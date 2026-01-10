#!/bin/bash
# Setup script for Codex MCP Server

set -e

echo "Setting up Codex MCP Server..."

# Check if Python 3.10+ is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Set environment variables:"
echo "   export TELEGRAM_BOT_TOKEN='your_bot_token'"
echo "   export TELEGRAM_ALLOWED_USER_IDS='your_user_id'"
echo ""
echo "2. Run the server:"
echo "   python3 -m codex_mcp_server.server"
echo "   or"
echo "   python3 run_server.py"
echo ""
echo "See README.md for more details."
