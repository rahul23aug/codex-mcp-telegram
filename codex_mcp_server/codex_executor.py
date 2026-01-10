"""Codex CLI command executor."""

import asyncio
import logging
import shutil
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class CodexExecutor:
    """Handles execution of Codex CLI commands."""
    
    def __init__(self, notification_callback: Optional[Callable] = None):
        """
        Initialize the executor and find codex binary.
        
        Args:
            notification_callback: Optional callback for notifications when Codex needs guidance.
                                  Should accept (question_type, message, context)
        """
        self.codex_path = shutil.which("codex")
        if not self.codex_path:
            raise RuntimeError("Codex CLI not found in PATH. Please install Codex CLI first.")
        logger.info(f"Found Codex CLI at: {self.codex_path}")
        self.notification_callback = notification_callback
    
    async def execute(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        timeout: int = 300,
        monitor: bool = True
    ) -> str:
        """
        Execute a Codex CLI command with the given prompt.
        
        Args:
            prompt: The prompt/command to execute
            model: Optional model to use
            timeout: Timeout in seconds (default: 300)
            monitor: If True, monitor output for questions/errors and notify (default: True)
        
        Returns:
            The output from Codex CLI
        """
        cmd = [self.codex_path, "exec", prompt]
        
        if model:
            cmd.extend(["-m", model])
        
        try:
            context = {
                'command': ' '.join(cmd),
                'prompt': prompt,
                'model': model
            }
            
            if monitor and self.notification_callback:
                # Use streaming mode with monitoring
                return await self._execute_with_monitoring(cmd, context, timeout)
            else:
                # Use standard non-monitored execution
                return await self._execute_standard(cmd, timeout)
        
        except asyncio.TimeoutError:
            error_msg = f"Error: Command timed out after {timeout} seconds"
            if self.notification_callback:
                try:
                    from .codex_monitor import QuestionType
                    await self.notification_callback(
                        QuestionType.ERROR,
                        error_msg,
                        context
                    )
                except Exception as e:
                    logger.error(f"Error sending timeout notification: {e}")
            return error_msg
        except Exception as e:
            logger.error(f"Error executing Codex command: {e}", exc_info=True)
            error_msg = f"Error executing command: {str(e)}"
            if self.notification_callback:
                try:
                    from .codex_monitor import QuestionType
                    await self.notification_callback(
                        QuestionType.ERROR,
                        error_msg,
                        {'command': ' '.join(cmd), 'error': str(e)}
                    )
                except Exception as notify_err:
                    logger.error(f"Error sending error notification: {notify_err}")
            return error_msg
    
    async def _execute_standard(self, cmd: list[str], timeout: int) -> str:
        """Standard execution without monitoring."""
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
    
    async def _execute_with_monitoring(
        self, 
        cmd: list[str], 
        context: Dict[str, Any], 
        timeout: int
    ) -> str:
        """Execute with output monitoring for questions/errors."""
        from .codex_monitor import CodexMonitor
        
        monitor = CodexMonitor(self.notification_callback)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=None
            )
            
            # Monitor stdout and stderr concurrently
            stdout_task = asyncio.create_task(
                monitor.monitor_stream(process.stdout, context)
            )
            stderr_task = asyncio.create_task(
                monitor.monitor_stream(process.stderr, {**context, 'stream': 'stderr'})
            )
            
            # Wait for process completion with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(stdout_task, stderr_task, process.wait()),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise asyncio.TimeoutError(f"Command timed out after {timeout} seconds")
            
            stdout_output = await stdout_task
            stderr_output = await stderr_task
            
            if process.returncode != 0:
                error_msg = stderr_output if stderr_output else "Unknown error"
                return f"Codex CLI error (exit code {process.returncode}): {error_msg}"
            
            output = stdout_output if stdout_output else ""
            return output.strip() or "Command executed successfully (no output)"
        
        except Exception as e:
            logger.error(f"Error in monitored execution: {e}", exc_info=True)
            raise
    
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
