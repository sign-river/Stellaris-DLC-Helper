#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理模块（兼容层）
提供统一的错误处理接口，内部使用统一日志系统
"""

import logging
from typing import Optional, Callable
from .unified_logger import get_logger


class ErrorHandler:
    """统一错误处理类（兼容层）"""
    
    def __init__(self, gui_logger=None):
        """
        初始化错误处理器
        
        参数:
            gui_logger: GUI日志记录器（已忽略，使用统一日志系统）
        """
        self.unified_logger = get_logger()
        
    def handle_error(
        self, 
        message: str, 
        exc: Optional[Exception] = None,
        show_in_gui: bool = True,
        log_traceback: bool = True
    ):
        """
        统一处理错误
        
        参数:
            message: 错误消息
            exc: 异常对象
            show_in_gui: 是否在GUI中显示（忽略，始终显示）
            log_traceback: 是否记录完整堆栈跟踪
        """
        if log_traceback:
            self.unified_logger.log_exception(message, exc)
        else:
            logging.getLogger(__name__).error(f"{message}: {str(exc)}" if exc else message)
    
    def handle_warning(self, message: str, show_in_gui: bool = True):
        """
        处理警告信息
        
        参数:
            message: 警告消息
            show_in_gui: 是否在GUI中显示（忽略，始终显示）
        """
        logging.getLogger(__name__).warning(message)
    
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
        return self.unified_logger.safe_execute(func, error_message, show_in_gui, return_on_error)


# 全局错误处理器实例
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


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
