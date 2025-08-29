"""
Logging configuration and utilities
"""

import sys
from pathlib import Path
from loguru import logger as _log
from src.config import settings

def setup_logger(name: str = "ugc_video_manager"):
    """
    Setup application logger with Loguru
    
    Args:
        name: Logger name/module
        
    Returns:
        Configured logger instance
    """
    
    # Remove default handler
    _log.remove()
    
    # Console handler with colors
    _log.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="DEBUG" if settings.debug_mode else "INFO",
        colorize=True
    )
    
    # File handler for all logs
    log_file = settings.log_folder_path / f"{name}.log"
    _log.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    # Error file handler
    error_file = settings.log_folder_path / f"{name}_error.log"
    _log.add(
        error_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    # Add context
    return _log.bind(module=name)

# Create default logger
default_logger = setup_logger()

def get_logger(name: str):
    """Get logger for specific module"""
    return _log.bind(module=name)
