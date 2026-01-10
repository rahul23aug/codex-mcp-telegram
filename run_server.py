#!/usr/bin/env python3
"""Entry point for Codex MCP Server."""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from codex_mcp_server.server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
