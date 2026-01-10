# Codex MCP Telegram

An MCP (Model Context Protocol) server that provides a Telegram escalation tool for human-in-the-loop guidance.

## Features

- 🔧 **MCP Server**: Exposes Telegram escalation as an MCP tool
- 📱 **Telegram Escalation Tool**: MCP tool to ask humans for input over Telegram
- 🔒 **Security**: User authentication via allowed user IDs
- ⚡ **Async Execution**: Non-blocking command execution
- 🧭 **Two-step Flow**: Prompt a human and poll for the answer
- 💬 **Agentic Escalation**: Codex explicitly calls an MCP tool to request human guidance

## Prerequisites

1. **Python 3.10+**

2. **Telegram Bot** (for remote access)
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

### Example Configuration

Create a `.env` file or export environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="123456789"
export TELEGRAM_ALLOWED_USER_IDS="123456789,987654321"
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

### Telegram MCP Escalation Tools

The MCP tool `telegram_prompt` sends a message to the configured chat and returns a `correlation_id`.
Use `telegram_poll` to check for a reply using that ID.

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

### `telegram_prompt`

Send a Telegram message and return a correlation ID.

**Parameters:**
- `question` (required): Question to send
- `context` (optional): Additional context to include

**Response:**
Returns JSON with `correlation_id`.

### `telegram_poll`

Check for a human response associated with a correlation ID.

**Parameters:**
- `correlation_id` (required): ID returned from `telegram_prompt`

**Response:**
Returns JSON with:
- `status`: `pending`, `answered`, `expired`, or `unknown`
- `answer`: Present when `status` is `answered`

## Security Considerations

1. **Authentication**: Always configure `TELEGRAM_ALLOWED_USER_IDS` to prevent unauthorized access.

2. **Command Injection**: The server validates command length and uses proper subprocess execution. However, be cautious with prompts that may contain sensitive information.

3. **Network**: The Telegram bot requires network access. Ensure your firewall allows outbound connections to `api.telegram.org`.

4. **Tokens**: Never commit your bot token to version control. Use environment variables or secure configuration files.

## Troubleshooting

### "Telegram bot not starting"
- Check that `TELEGRAM_BOT_TOKEN` is set correctly
- Verify network connectivity to Telegram API
- Check logs for detailed error messages

### "Unauthorized" errors
- Verify your User ID is in `TELEGRAM_ALLOWED_USER_IDS` or `TELEGRAM_CHAT_ID` matches

### Telegram polling and timeouts
- Ensure `TELEGRAM_CHAT_ID` matches the chat where the bot should post escalation messages
- Replies must include the correlation ID: `#<id> <answer>`
- If timeouts persist, confirm the bot has permission to read messages in the chat

## MCP Client Configuration (Codex CLI)

Add the MCP server in your Codex CLI configuration so it can call `telegram_prompt` and `telegram_poll`:

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

Or add it via the Codex CLI:

```bash
codex mcp add telegram -- python -m codex_mcp_server.server
Added global MCP server 'telegram'.
codex mcp list
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

## Manual Verification Checklist

If automated tests are not available, verify the following manually:

- Start the MCP server.
- Call `telegram_prompt` and confirm the Telegram message includes the correlation ID and reply instructions.
- Reply with `#<id> <answer>` from an allowed user ID.
- Call `telegram_poll` and confirm the tool returns `status=answered` and the answer.
- Reply without `#<id>` and confirm nothing happens.
- Reply from an unallowed user ID and confirm nothing happens.
- Wait for the request to expire and confirm the tool returns `status=expired`.

## License

MIT License

## Contributing

Contributions welcome! Please ensure code follows PEP 8 style guidelines and includes appropriate error handling.
