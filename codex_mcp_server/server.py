"""MCP Server implementation for Codex CLI with Telegram integration."""

import asyncio
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

from .codex_executor import CodexExecutor
from .config import Config
from .telegram_bot import TelegramBot

logger = logging.getLogger(__name__)

# Create server instance
app = Server("codex-mcp-telegram")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Codex CLI tools."""
    return [
        types.Tool(
            name="codex_exec",
            description="Execute a Codex CLI command. This runs codex in non-interactive mode with the provided prompt.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt/command to execute with Codex CLI"
                    },
                    "model": {
                        "type": "string",
                        "description": "Optional model to use (e.g., 'o1', 'o3')",
                        "default": None
                    }
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="codex_review",
            description="Run a code review using Codex CLI on specified files or directories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "File or directory path to review"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Optional specific review instructions"
                    }
                },
                "required": ["target"]
            }
        ),
        types.Tool(
            name="codex_status",
            description="Get the status of Codex CLI and check if it's available.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
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
        executor = CodexExecutor()
        
        if name == "codex_exec":
            prompt = arguments.get("prompt", "")
            model = arguments.get("model")
            result = await executor.execute(prompt, model=model)
            return [types.TextContent(
                type="text",
                text=result
            )]
        
        elif name == "codex_review":
            target = arguments.get("target", "")
            review_prompt = arguments.get("prompt", "")
            result = await executor.review(target, review_prompt)
            return [types.TextContent(
                type="text",
                text=result
            )]
        
        elif name == "codex_status":
            status = await executor.check_status()
            return [types.TextContent(
                type="text",
                text=status
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
    
    # Start Telegram bot if configured
    telegram_bot: Optional[TelegramBot] = None
    bot_task: Optional[asyncio.Task] = None
    if config.telegram_enabled:
        try:
            telegram_bot = TelegramBot(config, app)
            bot_task = asyncio.create_task(telegram_bot.start())
            logger.info("Telegram bot starting...")
            # Give bot a moment to initialize
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
    
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
        if telegram_bot:
            try:
                if bot_task and not bot_task.done():
                    bot_task.cancel()
                    try:
                        await bot_task
                    except asyncio.CancelledError:
                        pass
                await telegram_bot.stop()
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
