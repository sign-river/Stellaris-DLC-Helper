#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理模块
提供统一的错误处理接口，确保错误同时记录到GUI日志和文件日志
"""

import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from .path_utils import PathUtils


class ErrorHandler:
    """统一错误处理类"""
    
    def __init__(self, gui_logger=None):
        """
        初始化错误处理器
        
        参数:
            gui_logger: GUI日志记录器 (Logger实例)
        """
        self.gui_logger = gui_logger
        self.file_logger = logging.getLogger(__name__)
        
    def set_gui_logger(self, gui_logger):
        """设置GUI日志记录器"""
        self.gui_logger = gui_logger
        
    def handle_error(
        self, 
        message: str, 
        exc: Optional[Exception] = None,
        show_in_gui: bool = True,
        log_traceback: bool = True
    ):
        """
        统一处理错误，同时记录到GUI日志和文件日志
        
        参数:
            message: 错误消息
            exc: 异常对象
            show_in_gui: 是否在GUI中显示
            log_traceback: 是否记录完整堆栈跟踪
        """
        # 1. 在GUI操作日志中显示简短错误信息
        if show_in_gui and self.gui_logger:
            try:
                self.gui_logger.error(message)
            except Exception:
                pass
        
        # 2. 在标准日志文件中记录详细信息
        if exc:
            self.file_logger.error(f"{message}: {str(exc)}")
            if log_traceback:
                self.file_logger.exception(message)
        else:
            self.file_logger.error(message)
        
        # 3. 在专门的错误日志文件中记录完整堆栈
        if log_traceback:
            self._write_error_log(message, exc)
    
    def _write_error_log(self, message: str, exc: Optional[Exception] = None):
        """写入专门的错误日志文件"""
        try:
            log_dir = Path(PathUtils.get_log_dir())
            log_dir.mkdir(parents=True, exist_ok=True)
            error_log_path = log_dir / 'errors.log'
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"[{timestamp}] {message}\n")
                f.write(f"{'='*80}\n")
                
                if exc:
                    tb = ''.join(traceback.format_exception(
                        type(exc), exc, exc.__traceback__
                    ))
                    f.write(tb)
                else:
                    # 获取当前堆栈
                    tb = traceback.format_exc()
                    if tb != "NoneType: None\n":
                        f.write(tb)
                
                f.write("\n")
        except Exception:
            # 如果错误日志写入失败，静默忽略
            pass
    
    def handle_warning(self, message: str, show_in_gui: bool = True):
        """
        处理警告信息
        
        参数:
            message: 警告消息
            show_in_gui: 是否在GUI中显示
        """
        if show_in_gui and self.gui_logger:
            try:
                self.gui_logger.warning(message)
            except Exception:
                pass
        
        self.file_logger.warning(message)
    
    def safe_execute(
        self, 
        func: Callable, 
        error_message: str = "操作失败",
        show_in_gui: bool = True,
        return_on_error=None
    ):
        """
        安全执行函数，自动处理异常
        
        参数:
            func: 要执行的函数
            error_message: 错误消息前缀
            show_in_gui: 是否在GUI中显示错误
            return_on_error: 发生错误时的返回值
            
        返回:
            函数执行结果，或错误时的return_on_error
        """
        try:
            return func()
        except Exception as e:
            self.handle_error(
                f"{error_message}: {str(e)}", 
                exc=e,
                show_in_gui=show_in_gui
            )
            return return_on_error


# 全局错误处理器实例
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_gui_logger(gui_logger):
    """设置全局错误处理器的GUI日志记录器"""
    handler = get_error_handler()
    handler.set_gui_logger(gui_logger)


def handle_error(message: str, exc: Optional[Exception] = None, show_in_gui: bool = True):
    """快捷函数：处理错误"""
    handler = get_error_handler()
    handler.handle_error(message, exc, show_in_gui)


def handle_warning(message: str, show_in_gui: bool = True):
    """快捷函数：处理警告"""
    handler = get_error_handler()
    handler.handle_warning(message, show_in_gui)


def safe_execute(func: Callable, error_message: str = "操作失败", show_in_gui: bool = True, return_on_error=None):
    """快捷函数：安全执行"""
    handler = get_error_handler()
    return handler.safe_execute(func, error_message, show_in_gui, return_on_error)
