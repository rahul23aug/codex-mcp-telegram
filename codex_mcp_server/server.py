"""MCP Server implementation for Codex CLI with Telegram integration."""

import asyncio
import json
import logging
import sys
from typing import Any, Optional

try:
    # Try the official MCP SDK structure
    from mcp.server.stdio import stdio_server
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    # Fallback for different MCP SDK versions
    try:
        from mcp import server
        import mcp.types as types
        from mcp.server import NotificationOptions, Server
        from mcp.server.models import InitializationOptions
        MCP_AVAILABLE = True
        # Try to get stdio_server from server.stdio
        if hasattr(server, 'stdio'):
            stdio_server = server.stdio.stdio_server
        else:
            stdio_server = None
    except ImportError:
        try:
            import mcp.server.stdio as stdio_module
            import mcp.types as types
            from mcp.server import NotificationOptions, Server
            from mcp.server.models import InitializationOptions
            MCP_AVAILABLE = True
            stdio_server = getattr(stdio_module, 'stdio_server', None)
        except ImportError:
            MCP_AVAILABLE = False
            stdio_server = None
            logging.warning("MCP SDK not available. Install with: pip install mcp")

from .config import Config
from .telegram_bridge import TelegramBridge

logger = logging.getLogger(__name__)

# Create server instance
app = Server("codex-mcp-telegram")

_telegram_bridge: Optional[TelegramBridge] = None


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Codex CLI tools."""
    return [
        types.Tool(
            name="telegram_notify_and_wait",
            description=(
                "Send a Telegram message for human escalation and wait for a reply. "
                "The recipient must reply with #<id> <answer>."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or prompt to send over Telegram"
                    },
                    "timeout_sec": {
                        "type": "integer",
                        "description": "How long to wait for a reply before timing out",
                        "default": 1800
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context to include with the question",
                        "default": ""
                    }
                },
                "required": ["question"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    if arguments is None:
        arguments = {}
    
    try:
        if name == "telegram_notify_and_wait":
            if _telegram_bridge is None:
                raise RuntimeError("Telegram bridge is not configured. Check TELEGRAM_* environment variables.")
            question = arguments.get("question", "")
            timeout_sec = int(arguments.get("timeout_sec", 1800))
            context = arguments.get("context", "")
            response = await _telegram_bridge.ask_and_wait(
                question=question,
                timeout_sec=timeout_sec,
                context=context,
            )
            return [types.TextContent(
                type="text",
                text=json.dumps(response)
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Main entry point for the MCP server."""
    if not MCP_AVAILABLE or stdio_server is None:
        logger.error("MCP SDK is not installed or stdio_server is not available. Please install it with: pip install mcp")
        sys.exit(1)
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    config = Config()
    
    # Validate configuration
    is_valid, error_msg = config.validate()
    if not is_valid and config.telegram_enabled:
        logger.error(f"Configuration error: {error_msg}")
        sys.exit(1)
    
    # Start Telegram bridge if configured
    global _telegram_bridge
    telegram_bridge: Optional[TelegramBridge] = None
    if config.telegram_enabled:
        try:
            telegram_bridge = TelegramBridge(
                bot_token=config.telegram_bot_token,
                chat_id=config.telegram_chat_id,
                allowed_user_ids=config.telegram_allowed_user_ids,
            )
            _telegram_bridge = telegram_bridge
            await telegram_bridge.start()
            logger.info("Telegram bridge polling started.")
        except Exception as e:
            logger.error(f"Failed to start Telegram bridge: {e}", exc_info=True)
    
    # Run MCP server over stdio
    try:
        # Use stdio_server context manager
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="codex-mcp-telegram",
                    server_version="0.1.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        raise
    finally:
        if telegram_bridge:
            try:
                await telegram_bridge.stop()
            except Exception as e:
                logger.error(f"Error stopping Telegram bridge: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
