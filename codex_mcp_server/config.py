"""Configuration management for the MCP server."""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration loader and manager."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to config file. Defaults to ~/.codex_mcp/config.toml
        """
        if config_path is None:
            self.config_dir = Path.home() / ".codex_mcp"
            config_path = self.config_dir / "config.toml"
        else:
            self.config_dir = config_path.parent
        
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables or defaults."""
        # Telegram Bot Configuration
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # Security: Allowed user IDs (comma-separated)
        allowed_ids = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        self.telegram_allowed_user_ids = set()
        if allowed_ids:
            try:
                self.telegram_allowed_user_ids = {
                    int(uid.strip()) for uid in allowed_ids.split(",") if uid.strip()
                }
            except ValueError as e:
                print(f"Warning: Invalid TELEGRAM_ALLOWED_USER_IDS format: {e}")
        
        # Enable Telegram if bot token is provided and (chat_id or allowed_user_ids is set)
        self.telegram_enabled = bool(
            self.telegram_bot_token and (self.telegram_chat_id or self.telegram_allowed_user_ids)
        )
        
        # If no allowed IDs specified, require authentication token
        self.telegram_auth_token = os.getenv("TELEGRAM_AUTH_TOKEN", "")
        if self.telegram_enabled and not self.telegram_allowed_user_ids and not self.telegram_auth_token:
            # Generate a default auth token if none provided
            import secrets
            self.telegram_auth_token = secrets.token_urlsafe(16)
            print(f"WARNING: No authentication configured. Generated temporary token: {self.telegram_auth_token}")
            print("Set TELEGRAM_AUTH_TOKEN or TELEGRAM_ALLOWED_USER_IDS for proper security.")
        
        # Command execution settings
        self.max_command_length = int(os.getenv("MAX_COMMAND_LENGTH", "1000"))
        self.command_timeout = int(os.getenv("COMMAND_TIMEOUT", "300"))
        
        # Codex CLI settings
        self.codex_default_model = os.getenv("CODEX_DEFAULT_MODEL", "")
        
        # Proactive notification settings
        self.enable_proactive_notifications = os.getenv("CODEX_PROACTIVE_NOTIFICATIONS", "true").lower() == "true"
        self.notify_on_questions = os.getenv("CODEX_NOTIFY_ON_QUESTIONS", "true").lower() == "true"
        self.notify_on_errors = os.getenv("CODEX_NOTIFY_ON_ERRORS", "true").lower() == "true"
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.telegram_enabled:
            if not self.telegram_bot_token:
                return False, "TELEGRAM_BOT_TOKEN is required when Telegram is enabled"
            if not self.telegram_chat_id and not self.telegram_allowed_user_ids and not self.telegram_auth_token:
                return False, "TELEGRAM_CHAT_ID, TELEGRAM_ALLOWED_USER_IDS, or TELEGRAM_AUTH_TOKEN must be set"
        
        return True, None
