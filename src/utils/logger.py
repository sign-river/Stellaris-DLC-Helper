#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块（兼容层）
保持与旧代码的兼容性，内部使用统一日志系统
"""

from datetime import datetime
import logging
from logging import Handler
import traceback
from .path_utils import PathUtils
from pathlib import Path
from .unified_logger import get_logger


class Logger:
    """日志管理类（兼容层，委托给统一日志系统）"""
    
    def __init__(self, log_widget=None, root=None):
        """
        初始化日志管理器
        
            参数:
            log_widget: Tkinter ScrolledText 组件
            root: Tkinter根窗口，用于线程安全的GUI更新
        """
        self.log_widget = log_widget
        self.root = root
        self._unified_logger = get_logger()
        
        # 如果提供了GUI组件，设置到统一日志系统
        if log_widget and root:
            self._unified_logger.set_gui_widget(log_widget, root)
        
    def set_widget(self, log_widget, root=None):
        """设置日志组件"""
        self.log_widget = log_widget
        self.root = root
        # 更新统一日志系统的GUI组件
        self._unified_logger.set_gui_widget(log_widget, root)
        
    def log(self, message, level="INFO"):
        """
        写入日志
        
            参数:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR)
        """
        # 委托给标准logging系统（会自动处理文件和GUI日志）
        logger = logging.getLogger(__name__)
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "DEBUG":
            logger.debug(message)
        else:  # INFO, SUCCESS等
            logger.info(message)
    
    def info(self, message):
        """信息日志"""
        logging.getLogger(__name__).info(message)
        
    def warning(self, message):
        """警告日志"""
        logging.getLogger(__name__).warning(message)
        
    def error(self, message):
        """错误日志"""
        logging.getLogger(__name__).error(message)
        
    def success(self, message):
        """成功日志（仅显示在GUI）"""
        self._unified_logger.gui_success(message)

    def debug(self, message):
        """调试日志"""
        logging.getLogger(__name__).debug(message)

    def exception(self, message, exc: Exception = None):
        """记录异常并显示到 GUI 日志（同时将异常写入错误日志文件）"""
        self._unified_logger.log_exception(message, exc)

    def get_logging_handler(self) -> Handler:
        """
        获取日志处理器（兼容性方法）
        
        统一日志系统会自动处理，返回空处理器保持兼容性
        """
        class DummyHandler(Handler):
            def emit(self, record):
                pass
        
        return DummyHandler()

    def log_exception(self, message: str, exc: Exception = None):
        """记录异常到 GUI 日志并写入错误日志文件。

        Args:
            message: 要记录的上下文消息（简短）
            exc: 可选异常对象；如果为 None，将使用当前异常信息
        """
        self._unified_logger.log_exception(message, exc)
