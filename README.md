# Codex MCP Telegram

An MCP (Model Context Protocol) server that wraps Codex CLI commands and provides remote access via Telegram Bot API. Execute Codex CLI commands remotely when you're away from your machine.

## Features

- 🔧 **MCP Server**: Exposes Codex CLI commands as MCP tools
- 📱 **Telegram Escalation Tool**: MCP tool to ask humans for input over Telegram
- 🔒 **Security**: User authentication via allowed user IDs
- ⚡ **Async Execution**: Non-blocking command execution
- 📝 **Multiple Commands**: Support for exec, review, and status checks
- 💬 **Agentic Escalation**: Codex explicitly calls an MCP tool to request human guidance

## Prerequisites

1. **Codex CLI** installed and available in PATH
   ```bash
   # Verify installation
   codex --version
   ```

2. **Python 3.10+**

3. **Telegram Bot** (for remote access)
   - Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
   - Save the bot token

## Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Or install as a package:
   ```bash
   pip install -e .
   ```

## Configuration

The server uses environment variables for configuration:

### Required (for Telegram escalation tool)

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `TELEGRAM_CHAT_ID`: Chat ID where the escalation prompts should be sent
- `TELEGRAM_ALLOWED_USER_IDS`: Comma-separated list of Telegram user IDs allowed to reply

### Optional

- `MAX_COMMAND_LENGTH`: Maximum command length (default: 1000)
- `COMMAND_TIMEOUT`: Command execution timeout in seconds (default: 300)
- `CODEX_DEFAULT_MODEL`: Default model to use for Codex commands (e.g., "o1", "o3")

### Example Configuration

Create a `.env` file or export environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="123456789"
export TELEGRAM_ALLOWED_USER_IDS="123456789,987654321"
export COMMAND_TIMEOUT="600"
export CODEX_DEFAULT_MODEL="o1"
```

## Usage

### As MCP Server (stdio)

Run the server:

```bash
python -m codex_mcp_server.server
```

Or use the installed script:

```bash
codex-mcp-telegram
# or (backward compatibility alias)
codex-mcp-server
```

The server communicates via stdio following the MCP protocol.

### Telegram MCP Escalation Tool

The MCP tool `telegram_notify_and_wait` sends a message to the configured chat and waits for a reply.

**Reply format:** `#<correlation_id> <answer>`

Example message:
```
❓ MCP Escalation

Should we proceed with the migration?

Reply with #<id> <answer>
```

### Getting Your Telegram User ID

1. Start a chat with your bot
2. Send `/start`
3. The bot will show your User ID if you're not authorized
4. Add this ID to `TELEGRAM_ALLOWED_USER_IDS` or use `TELEGRAM_CHAT_ID`

## MCP Tools

The server exposes the following MCP tools:

### `codex_exec`

Execute a Codex CLI command.

**Parameters:**
- `prompt` (required): The prompt/command to execute
- `model` (optional): Model to use (e.g., "o1", "o3")

### `codex_review`

Run a code review on specified files or directories.

**Parameters:**
- `target` (required): File or directory path to review
- `prompt` (optional): Specific review instructions

### `codex_status`

Check Codex CLI availability and version.

**Parameters:** None

### `telegram_notify_and_wait`

Send a Telegram message and wait for a human response.

**Parameters:**
- `question` (required): Question to send
- `timeout_sec` (optional): Seconds to wait (default: 1800)
- `context` (optional): Additional context to include

**Response:**
Returns JSON with `answer` and `correlation_id`. On timeout, `answer` is `null` and an `error` field is included.

## Security Considerations

1. **Authentication**: Always configure `TELEGRAM_ALLOWED_USER_IDS` to prevent unauthorized access.

2. **Command Injection**: The server validates command length and uses proper subprocess execution. However, be cautious with prompts that may contain sensitive information.

3. **Network**: The Telegram bot requires network access. Ensure your firewall allows outbound connections to `api.telegram.org`.

4. **Tokens**: Never commit your bot token to version control. Use environment variables or secure configuration files.

## Troubleshooting

### "Codex CLI not found"
- Ensure Codex CLI is installed and in your PATH
- Verify with: `which codex`

### "Telegram bridge not starting"
- Check that `TELEGRAM_BOT_TOKEN` is set correctly
- Verify network connectivity to Telegram API
- Check logs for detailed error messages

### "Unauthorized" errors
- Verify your User ID is in `TELEGRAM_ALLOWED_USER_IDS` or `TELEGRAM_CHAT_ID` matches

### Timeout errors
- Increase `COMMAND_TIMEOUT` if commands take longer
- Check Codex CLI logs for underlying issues

### Telegram polling and timeouts
- Ensure `TELEGRAM_CHAT_ID` matches the chat where the bot should post escalation messages
- Replies must include the correlation ID: `#<id> <answer>`
- If timeouts persist, confirm the bot has permission to read messages in the chat

## MCP Client Configuration (Codex CLI)

Add the MCP server in your Codex CLI configuration so it can call `telegram_notify_and_wait`:

```json
{
  "mcpServers": {
    "codex-mcp-telegram": {
      "command": "codex-mcp-telegram",
      "args": []
    }
  }
}
```

## Development

```bash
# Install in development mode
pip install -e .

# Run tests (if available)
pytest

# Run with debug logging
PYTHONPATH=. python -m codex_mcp_server.server
```

### Local Telegram Tool Test

```bash
python scripts/telegram_notify_test.py "Should I proceed with the deploy?"
```

## Manual Verification Checklist

If automated tests are not available, verify the following manually:

- Start the MCP server and call `telegram_notify_and_wait`.
- Confirm the Telegram message includes the correlation ID and reply instructions.
- Reply with `#<id> <answer>` from an allowed user ID and confirm the tool returns the answer.
- Reply without `#<id>` and confirm nothing happens.
- Reply from an unallowed user ID and confirm nothing happens.
- Let the call time out and confirm the tool returns a clear timeout error.

## License

MIT License

## Contributing

Contributions welcome! Please ensure code follows PEP 8 style guidelines and includes appropriate error handling.
