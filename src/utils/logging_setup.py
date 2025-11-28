"""
日志设置工具 - 用于控制台与 GUI 集成。
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
    """为控制台配置基本日志，使用默认格式。

    本函数设置一个用于控制台输出的 StreamHandler，并应用简单的消息格式。
    """
    fmt = fmt or "[%(asctime)s] %(levelname)s: %(message)s"
    # 移除现有的处理器以避免多次调用导致日志重复
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
        # 使用 PathUtils 确保日志目录存在
        log_dir = PathUtils.get_log_dir()
        filename = filename or "stellaris_dlc_helper.log"
        file_path = Path(log_dir) / filename
        # 循环写日志文件处理器（RotatingFileHandler）
        file_handler = RotatingFileHandler(
            str(file_path), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(fmt))
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
        # 额外的专用错误日志文件，记录 ERROR 及以上级别（单独文件方便排查）
        error_log_path = Path(log_dir) / (filename or "stellaris_dlc_helper.log")
        error_file_handler = RotatingFileHandler(str(Path(log_dir) / "errors.log"), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        error_file_handler.setFormatter(logging.Formatter(fmt))
        error_file_handler.setLevel(logging.ERROR)
        root.addHandler(error_file_handler)


def get_root_logger(name: Optional[str] = None):
    return logging.getLogger(name) if name else logging.getLogger()


def get_default_log_file_path(filename: Optional[str] = None) -> str:
    """返回默认日志文件路径（不创建文件）。

    可用于向用户展示日志文件的存放位置。
    """
    if filename is None:
        filename = "stellaris_dlc_helper.log"
    return str(Path(PathUtils.get_log_dir()) / filename)
