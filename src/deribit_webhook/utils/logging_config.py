"""
Logging configuration with millisecond precision

Provides structured logging with both JSON and text formats,
supporting millisecond-precision timestamps.
"""

import logging
import logging.handlers
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import structlog
from pathlib import Path

from ..config.settings import settings


class MillisecondFormatter(logging.Formatter):
    """Custom formatter that includes milliseconds in timestamps"""

    def formatTime(self, record, datefmt=None):
        """Format time with milliseconds"""
        # Always use millisecond precision
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Remove last 3 digits to get milliseconds


class JSONFormatter(logging.Formatter):
    """JSON formatter with millisecond precision"""
    
    def format(self, record):
        """Format log record as JSON"""
        # Create timestamp with milliseconds
        dt = datetime.fromtimestamp(record.created)
        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        log_entry = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return structlog.dev.ConsoleRenderer(colors=False)(None, None, log_entry)


def setup_logging() -> structlog.BoundLogger:
    """
    Setup logging configuration with millisecond precision
    
    Returns:
        Configured structlog logger
    """
    # Ensure logs directory exists
    if settings.log_file:
        log_dir = Path(settings.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    # File handler (if configured)
    file_handler = None
    if settings.log_file:
        try:
            # Use rotating file handler for better log management
            file_handler = logging.handlers.RotatingFileHandler(
                settings.log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, settings.log_level.upper()))
        except Exception as e:
            print(f"Warning: Could not create file handler for {settings.log_file}: {e}")
    
    # Set formatters based on log format
    if settings.log_format.lower() == 'json':
        formatter = JSONFormatter()
    else:
        # Text format with milliseconds
        formatter = MillisecondFormatter(
            fmt='%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)d)'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    if file_handler:
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create and return main application logger
    logger = structlog.get_logger("deribit_webhook")
    
    # Log configuration info
    logger.info(
        "Logging configured",
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
        console_output=True
    )
    
    return logger


def get_logger(name: str = "deribit_webhook") -> structlog.BoundLogger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_with_context(logger: structlog.BoundLogger, level: str, message: str, **context) -> None:
    """
    Log message with additional context
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields
    """
    log_method = getattr(logger, level.lower())
    log_method(message, **context)


# Global logger instance
_global_logger: Optional[structlog.BoundLogger] = None


def init_logging() -> structlog.BoundLogger:
    """Initialize global logging configuration"""
    global _global_logger
    if _global_logger is None:
        _global_logger = setup_logging()
    return _global_logger


def get_global_logger() -> structlog.BoundLogger:
    """Get the global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = init_logging()
    return _global_logger


# Convenience functions for common log levels
def debug(message: str, **context) -> None:
    """Log debug message"""
    get_global_logger().debug(message, **context)


def info(message: str, **context) -> None:
    """Log info message"""
    get_global_logger().info(message, **context)


def warning(message: str, **context) -> None:
    """Log warning message"""
    get_global_logger().warning(message, **context)


def error(message: str, **context) -> None:
    """Log error message"""
    get_global_logger().error(message, **context)


def critical(message: str, **context) -> None:
    """Log critical message"""
    get_global_logger().critical(message, **context)


# Alias for backward compatibility
warn = warning
