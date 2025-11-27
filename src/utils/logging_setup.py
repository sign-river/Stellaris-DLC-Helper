"""
Logging setup utilities for console and GUI integration.
"""
import logging
from typing import Optional
from logging.handlers import RotatingFileHandler
from .path_utils import PathUtils
from pathlib import Path


def configure_basic_logging(
    level: int = logging.INFO,
    fmt: Optional[str] = None,
    log_to_file: bool = True,
    filename: Optional[str] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
):
    """Configure basic logging for console with a default format.

    This sets up a StreamHandler for console output and a simple message format.
    """
    fmt = fmt or "[%(asctime)s] %(levelname)s: %(message)s"
    # Remove existing handlers to avoid duplicate logs when called multiple times
    root = logging.getLogger()
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt))
    console_handler.setLevel(level)
    root.setLevel(level)
    root.addHandler(console_handler)

    if log_to_file:
        # Ensure log dir exists using PathUtils
        log_dir = PathUtils.get_log_dir()
        filename = filename or "stellaris_dlc_helper.log"
        file_path = Path(log_dir) / filename
        # Rotating file handler
        file_handler = RotatingFileHandler(
            str(file_path), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(fmt))
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)


def get_root_logger(name: Optional[str] = None):
    return logging.getLogger(name) if name else logging.getLogger()


def get_default_log_file_path(filename: Optional[str] = None) -> str:
    """Return the path of the default log file (without creating it).

    Useful for showing the user where log files are stored.
    """
    if filename is None:
        filename = "stellaris_dlc_helper.log"
    return str(Path(PathUtils.get_log_dir()) / filename)
