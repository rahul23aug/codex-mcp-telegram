"""Codex CLI command executor."""

import asyncio
import logging
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


class CodexExecutor:
    """Handles execution of Codex CLI commands."""
    
    def __init__(self):
        """Initialize the executor and find codex binary."""
        self.codex_path = shutil.which("codex")
        if not self.codex_path:
            raise RuntimeError("Codex CLI not found in PATH. Please install Codex CLI first.")
        logger.info(f"Found Codex CLI at: {self.codex_path}")
    
    async def execute(self, prompt: str, model: Optional[str] = None, timeout: int = 300) -> str:
        """
        Execute a Codex CLI command with the given prompt.
        
        Args:
            prompt: The prompt/command to execute
            model: Optional model to use
            timeout: Timeout in seconds (default: 300)
        
        Returns:
            The output from Codex CLI
        """
        cmd = [self.codex_path, "exec", prompt]
        
        if model:
            cmd.extend(["-m", model])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=None
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
                return f"Codex CLI error (exit code {process.returncode}): {error_msg}"
            
            output = stdout.decode('utf-8', errors='replace') if stdout else ""
            return output.strip() or "Command executed successfully (no output)"
        
        except asyncio.TimeoutError:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            logger.error(f"Error executing Codex command: {e}", exc_info=True)
            return f"Error executing command: {str(e)}"
    
    async def review(self, target: str, review_prompt: Optional[str] = None, timeout: int = 300) -> str:
        """
        Run a code review on the specified target.
        
        Args:
            target: File or directory path to review
            review_prompt: Optional specific review instructions
            timeout: Timeout in seconds (default: 300)
        
        Returns:
            The review output from Codex CLI
        """
        cmd = [self.codex_path, "review", target]
        
        if review_prompt:
            cmd.extend(["--", review_prompt])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Unknown error"
                return f"Codex review error (exit code {process.returncode}): {error_msg}"
            
            output = stdout.decode('utf-8', errors='replace') if stdout else ""
            return output.strip() or "Review completed (no output)"
        
        except asyncio.TimeoutError:
            return f"Error: Review timed out after {timeout} seconds"
        except Exception as e:
            logger.error(f"Error executing Codex review: {e}", exc_info=True)
            return f"Error executing review: {str(e)}"
    
    async def check_status(self) -> str:
        """Check if Codex CLI is available and get version."""
        try:
            process = await asyncio.create_subprocess_exec(
                self.codex_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version = stdout.decode('utf-8', errors='replace').strip()
                return f"Codex CLI is available: {version}"
            else:
                return "Codex CLI found but version check failed"
        
        except Exception as e:
            return f"Error checking Codex status: {str(e)}"
