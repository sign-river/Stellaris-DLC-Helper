#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
"""

from datetime import datetime
import logging
from logging import Handler


class Logger:
    """日志管理类"""
    
    def __init__(self, log_widget=None):
        """
        初始化日志管理器
        
            参数:
            log_widget: Tkinter ScrolledText 组件
        """
        self.log_widget = log_widget
        
    def set_widget(self, log_widget):
        """设置日志组件"""
        self.log_widget = log_widget
        
    def log(self, message, level="INFO"):
        """
        写入日志
        
            参数:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR)
        """
        if self.log_widget:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_widget.insert("end", f"[{timestamp}] {message}\n")
            self.log_widget.see("end")
            
    def info(self, message):
        """信息日志"""
        self.log(message, "INFO")
        
    def warning(self, message):
        """警告日志"""
        self.log(f"⚠ {message}", "WARNING")
        
    def error(self, message):
        """错误日志"""
        self.log(f"✗ {message}", "ERROR")
        
    def success(self, message):
        """成功日志"""
        self.log(f"✓ {message}", "SUCCESS")

    def get_logging_handler(self) -> Handler:
        """创建一个将日志记录转发到 GUI Logger 的 logging.Handler。

        返回的处理器可以附加到 Python 的日志系统，使得 logging.info/warning/error
        等日志消息会显示在 GUI 日志组件中。
        """
        class GUIHandler(Handler):
            def __init__(self, gui_logger: Logger):
                super().__init__()
                self.gui_logger = gui_logger

            def emit(self, record):
                try:
                    msg = self.format(record)
                    level = record.levelno
                    if level >= logging.ERROR:
                        self.gui_logger.error(msg)
                    elif level >= logging.WARNING:
                        self.gui_logger.warning(msg)
                    elif level >= logging.INFO:
                        self.gui_logger.info(msg)
                    else:
                        self.gui_logger.log(msg, "DEBUG")
                except Exception:
                    # 安全地忽略 GUI 日志处理错误，防止应用程序崩溃
                    pass

        handler = GUIHandler(self)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        return handler
