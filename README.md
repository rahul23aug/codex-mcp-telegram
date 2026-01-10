# Codex MCP Telegram

An MCP (Model Context Protocol) server that wraps Codex CLI commands and provides remote access via Telegram Bot API. Execute Codex CLI commands remotely when you're away from your machine.

## Features

- 🔧 **MCP Server**: Exposes Codex CLI commands as MCP tools
- 📱 **Telegram Integration**: Remote access via Telegram bot
- 🚨 **Proactive Notifications**: Codex automatically reaches out via Telegram when it needs your guidance, has questions, or encounters errors
- 🔒 **Security**: User authentication via allowed user IDs or auth tokens
- ⚡ **Async Execution**: Non-blocking command execution
- 📝 **Multiple Commands**: Support for exec, review, and status checks
- 💬 **Interactive Guidance**: Respond to Codex's questions via Telegram

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

### Required (for Telegram)

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `TELEGRAM_CHAT_ID` or `TELEGRAM_ALLOWED_USER_IDS`: Chat ID or comma-separated list of allowed user IDs

### Optional

- `TELEGRAM_AUTH_TOKEN`: Custom authentication token (if not using allowed user IDs)
- `TELEGRAM_ALLOWED_USER_IDS`: Comma-separated list of Telegram user IDs allowed to execute commands
- `MAX_COMMAND_LENGTH`: Maximum command length (default: 1000)
- `COMMAND_TIMEOUT`: Command execution timeout in seconds (default: 300)
- `CODEX_DEFAULT_MODEL`: Default model to use for Codex commands (e.g., "o1", "o3")
- `CODEX_PROACTIVE_NOTIFICATIONS`: Enable proactive notifications when Codex needs guidance (default: true)
- `CODEX_NOTIFY_ON_QUESTIONS`: Notify when Codex has questions or needs clarification (default: true)
- `CODEX_NOTIFY_ON_ERRORS`: Notify when Codex encounters errors (default: true)
- `CODEX_PROACTIVE_NOTIFICATIONS`: Enable proactive notifications when Codex needs guidance (default: true)
- `CODEX_NOTIFY_ON_QUESTIONS`: Notify when Codex has questions or needs clarification (default: true)
- `CODEX_NOTIFY_ON_ERRORS`: Notify when Codex encounters errors (default: true)

### Example Configuration

Create a `.env` file or export environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_ALLOWED_USER_IDS="123456789,987654321"
export COMMAND_TIMEOUT="600"
export CODEX_DEFAULT_MODEL="o1"
```

Or use a single chat ID:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="123456789"
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

### With Telegram Bot

When `TELEGRAM_BOT_TOKEN` is set, the server automatically starts the Telegram bot.

**Available Telegram Commands:**

- `/start` - Initialize the bot and show welcome message
- `/help` - Show help and available commands
- `/status` - Check Codex CLI availability and version
- `/exec <prompt>` - Execute a Codex CLI command
  - Example: `/exec write a Python hello world program`
- `/review <path>` - Review code at specified path
  - Example: `/review /path/to/file.py`
- `/respond <guidance>` - Provide guidance when Codex asks for help
  - Example: `/respond yes, proceed with the changes`

You can also send plain text messages - they'll be treated as `/exec` commands.

### Proactive Notifications (Codex Reaches Out to You)

When Codex CLI needs your guidance during execution, it will **automatically send you a Telegram notification**. This includes:

- **Questions**: When Codex needs clarification or has doubts
- **Confirmation Requests**: When Codex needs approval to proceed
- **Choices**: When Codex needs you to make a decision
- **Errors**: When Codex encounters issues that need attention
- **Uncertainty**: When Codex is unsure about something

**Example Notification:**
```
🚨 Codex Needs Your Guidance

Type: Clarification

Message:
Should I proceed with deleting the old files?

Command: codex exec clean up old files
Prompt: clean up old files

Codex is waiting for your guidance. 
You can respond via Telegram or check the logs.
```

**Responding to Codex:**
- Use `/respond <your_guidance>` to provide feedback when Codex asks
- Example: `/respond yes, proceed with the changes`
- Codex will continue its workflow based on your response

**Configuration:**
- `CODEX_PROACTIVE_NOTIFICATIONS=true` (default) - Enable proactive notifications
- `CODEX_NOTIFY_ON_QUESTIONS=true` (default) - Notify on questions
- `CODEX_NOTIFY_ON_ERRORS=true` (default) - Notify on errors

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

## Security Considerations

1. **Authentication**: Always configure either `TELEGRAM_ALLOWED_USER_IDS` or `TELEGRAM_AUTH_TOKEN` to prevent unauthorized access.

2. **Command Injection**: The server validates command length and uses proper subprocess execution. However, be cautious with prompts that may contain sensitive information.

3. **Network**: The Telegram bot requires network access. Ensure your firewall allows outbound connections to `api.telegram.org`.

4. **Tokens**: Never commit your bot token or auth tokens to version control. Use environment variables or secure configuration files.

## Troubleshooting

### "Codex CLI not found"
- Ensure Codex CLI is installed and in your PATH
- Verify with: `which codex`

### "Telegram bot not starting"
- Check that `TELEGRAM_BOT_TOKEN` is set correctly
- Verify network connectivity to Telegram API
- Check logs for detailed error messages

### "Unauthorized" errors
- Verify your User ID is in `TELEGRAM_ALLOWED_USER_IDS` or `TELEGRAM_CHAT_ID` matches
- Check that auth token (if used) is included in your messages

### Timeout errors
- Increase `COMMAND_TIMEOUT` if commands take longer
- Check Codex CLI logs for underlying issues

## Development

```bash
# Install in development mode
pip install -e .

# Run tests (if available)
pytest

# Run with debug logging
PYTHONPATH=. python -m codex_mcp_server.server
```

## License

MIT License

## Contributing

Contributions welcome! Please ensure code follows PEP 8 style guidelines and includes appropriate error handling.
