"""Codex CLI output monitor for detecting prompts and questions."""

import asyncio
import logging
import re
from typing import Callable, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Types of questions/prompts Codex might ask."""
    CONFIRMATION = "confirmation"
    CHOICE = "choice"
    CLARIFICATION = "clarification"
    PERMISSION = "permission"
    UNCERTAINTY = "uncertainty"
    ERROR = "error"


class CodexMonitor:
    """Monitors Codex CLI output for questions, prompts, and guidance needs."""
    
    # Patterns that indicate Codex needs user input or guidance
    QUESTION_PATTERNS = [
        (r'\?[ \t]*$', QuestionType.CLARIFICATION),  # Question mark at end of line
        (r'(?:should|would|could|can|may|might|do you|does|did)[\s\w]+\?', QuestionType.CLARIFICATION, re.IGNORECASE),
        (r'(?:confirm|proceed|continue|apply|execute)[\s\w]*\?', QuestionType.CONFIRMATION, re.IGNORECASE),
        (r'(?:yes|no|y/n|y or n)', QuestionType.CHOICE, re.IGNORECASE),
        (r'(?:choose|select|pick|which|what|how)', QuestionType.CHOICE, re.IGNORECASE),
        (r'(?:permission|allow|grant|access)', QuestionType.PERMISSION, re.IGNORECASE),
        (r'(?:not sure|uncertain|unclear|unsure|confused|doubt)', QuestionType.UNCERTAINTY, re.IGNORECASE),
        (r'(?:waiting for|awaiting|needs|requires).*?(?:input|response|feedback|guidance)', QuestionType.CLARIFICATION, re.IGNORECASE),
    ]
    
    # Error patterns that might need attention
    ERROR_PATTERNS = [
        (r'error:', QuestionType.ERROR, re.IGNORECASE),
        (r'failed|failure', QuestionType.ERROR, re.IGNORECASE),
        (r'cannot|couldn\'t|unable to', QuestionType.ERROR, re.IGNORECASE),
        (r'exception|traceback', QuestionType.ERROR, re.IGNORECASE),
    ]
    
    # Prompts that indicate Codex is waiting for input
    WAITING_PATTERNS = [
        r'>[ \t]*$',  # Prompt indicator
        r':[ \t]*$',  # Colon at end (common prompt style)
        r'\[Y/n\]',  # Yes/No prompt
        r'\[y/N\]',
        r'\(y/n\)',
        r'continue\?',
        r'proceed\?',
    ]
    
    def __init__(self, notification_callback: Optional[Callable] = None):
        """
        Initialize the monitor.
        
        Args:
            notification_callback: Optional callback function to call when guidance is needed.
                                  Should accept (question_type, message, context)
        """
        self.notification_callback = notification_callback
        self.detected_questions: List[dict] = []
        self.buffer = ""
        
    def detect_question(self, line: str) -> Optional[tuple[QuestionType, str]]:
        """
        Detect if a line contains a question or prompt.
        
        Args:
            line: Line of output to check
            
        Returns:
            Tuple of (QuestionType, matched_text) if detected, None otherwise
        """
        line_stripped = line.strip()
        if not line_stripped:
            return None
        
        # Check question patterns
        for pattern_info in self.QUESTION_PATTERNS:
            if len(pattern_info) == 2:
                pattern, q_type = pattern_info
                flags = 0
            else:
                pattern, q_type, flags = pattern_info
            
            match = re.search(pattern, line, flags)
            if match:
                return (q_type, match.group(0))
        
        # Check waiting patterns
        for pattern in self.WAITING_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return (QuestionType.CONFIRMATION, line_stripped)
        
        return None
    
    def detect_error(self, line: str) -> Optional[str]:
        """
        Detect if a line contains an error.
        
        Args:
            line: Line of output to check
            
        Returns:
            Error message if detected, None otherwise
        """
        for pattern_info in self.ERROR_PATTERNS:
            if len(pattern_info) == 2:
                pattern, _ = pattern_info
                flags = 0
            else:
                pattern, _, flags = pattern_info
            
            if re.search(pattern, line, flags):
                return line.strip()
        return None
    
    async def process_line(self, line: str, context: dict = None) -> bool:
        """
        Process a line of output and check for questions/errors.
        
        Args:
            line: Line of output to process
            context: Optional context dictionary (command, etc.)
            
        Returns:
            True if a question/error was detected, False otherwise
        """
        if context is None:
            context = {}
        
        # Detect questions
        question_info = self.detect_question(line)
        if question_info:
            q_type, matched_text = question_info
            question_data = {
                'type': q_type,
                'message': line.strip(),
                'matched': matched_text,
                'context': context,
                'timestamp': asyncio.get_event_loop().time()
            }
            self.detected_questions.append(question_data)
            
            # Call notification callback if available
            if self.notification_callback:
                try:
                    await self.notification_callback(q_type, line.strip(), context)
                except Exception as e:
                    logger.error(f"Error in notification callback: {e}", exc_info=True)
            
            return True
        
        # Detect errors
        error_msg = self.detect_error(line)
        if error_msg:
            question_data = {
                'type': QuestionType.ERROR,
                'message': error_msg,
                'context': context,
                'timestamp': asyncio.get_event_loop().time()
            }
            self.detected_questions.append(question_data)
            
            if self.notification_callback:
                try:
                    await self.notification_callback(QuestionType.ERROR, error_msg, context)
                except Exception as e:
                    logger.error(f"Error in notification callback: {e}", exc_info=True)
            
            return True
        
        return False
    
    async def monitor_stream(self, stream, context: dict = None) -> str:
        """
        Monitor a stream (stdout/stderr) for questions and collect output.
        
        Args:
            stream: Async stream to monitor
            context: Optional context dictionary
            
        Returns:
            Collected output as string
        """
        if context is None:
            context = {}
        
        output_lines = []
        buffer = ""
        
        try:
            while True:
                chunk = await stream.read(1024)
                if not chunk:
                    break
                
                # Decode chunk
                try:
                    text = chunk.decode('utf-8', errors='replace')
                except Exception as e:
                    logger.error(f"Error decoding chunk: {e}")
                    continue
                
                buffer += text
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    output_lines.append(line)
                    
                    # Check for questions/errors
                    await self.process_line(line, context)
                
                # Small delay to avoid busy waiting
                await asyncio.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Error monitoring stream: {e}", exc_info=True)
        finally:
            # Process remaining buffer
            if buffer.strip():
                output_lines.append(buffer)
                await self.process_line(buffer, context)
        
        return '\n'.join(output_lines)
    
    def get_detected_questions(self) -> List[dict]:
        """Get all detected questions."""
        return self.detected_questions.copy()
    
    def clear_questions(self):
        """Clear detected questions list."""
        self.detected_questions.clear()
