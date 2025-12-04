"""
日志设置工具 - 用于控制台与 GUI 集成（兼容层）
内部使用统一日志系统
"""
import logging
from typing import Optional
from .unified_logger import configure_logging, get_logger
from pathlib import Path


def configure_basic_logging(
    level: int = logging.INFO,
    fmt: Optional[str] = None,
    log_to_file: bool = True,
    filename: Optional[str] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
):
    """为控制台配置基本日志，使用统一日志系统。

    本函数配置统一日志系统，包括控制台、文件和错误日志。
    """
    from .path_utils import PathUtils
    
    log_dir = PathUtils.get_log_dir()
    configure_logging(log_dir, level, max_bytes, backup_count)


def get_root_logger(name: Optional[str] = None):
    """获取日志记录器"""
    return logging.getLogger(name) if name else logging.getLogger()


def get_default_log_file_path(filename: Optional[str] = None) -> str:
    """返回默认日志文件路径（不创建文件）。

    可用于向用户展示日志文件的存放位置。
    """
    unified = get_logger()
    if unified.log_dir:
        if filename == 'errors.log':
            return unified.get_log_file_path('error')
        else:
            return unified.get_log_file_path('main')
    
    # 降级处理
    from .path_utils import PathUtils
    if filename is None:
        filename = "stellaris_dlc_helper.log"
    return str(Path(PathUtils.get_log_dir()) / filename)

