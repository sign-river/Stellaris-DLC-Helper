#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
"""

from datetime import datetime
import logging
from logging import Handler
import traceback
from .path_utils import PathUtils
from pathlib import Path


class Logger:
    """日志管理类"""
    
    def __init__(self, log_widget=None, root=None):
        """
        初始化日志管理器
        
            参数:
            log_widget: Tkinter ScrolledText 组件
            root: Tkinter根窗口，用于线程安全的GUI更新
        """
        self.log_widget = log_widget
        self.root = root
        
    def set_widget(self, log_widget, root=None):
        """设置日志组件"""
        self.log_widget = log_widget
        self.root = root
        
    def log(self, message, level="INFO"):
        """
        写入日志
        
            参数:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR)
        """
        if self.log_widget:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}\n"
            
            # 如果有root，使用after确保在主线程中更新GUI
            if self.root:
                self.root.after(0, lambda: self._insert_log(formatted_message))
            else:
                # 直接插入（用于主线程调用）
                self._insert_log(formatted_message)
    
    def _insert_log(self, message):
        """实际插入日志到GUI组件"""
        if self.log_widget:
            self.log_widget.insert("end", message)
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

    def debug(self, message):
        """调试日志"""
        self.log(message, "DEBUG")

    def exception(self, message, exc: Exception = None):
        """记录异常并显示到 GUI 日志（同时将异常写入错误日志文件）"""
        try:
            # 使用现有的错误记录方法
            self.error(message)
            import logging
            logging.getLogger().exception(message)
        except Exception:
            pass

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

    def log_exception(self, message: str, exc: Exception = None):
        """记录异常到 GUI 日志并写入错误日志文件。

        Args:
            message: 要记录的上下文消息（简短）
            exc: 可选异常对象；如果为 None，将使用当前异常信息
        """
        try:
            # 在 GUI 日志中记录简短提示 (包含前缀)
            self.error(message)

            # 使用标准 logging 将异常写入已配置的文件处理器（包含堆栈跟踪）
            import logging
            logging.getLogger().exception(message)

            # 写入专门的错误日志文件（errors.log）以保存完整堆栈信息
            log_dir = Path(PathUtils.get_log_dir())
            log_dir.mkdir(parents=True, exist_ok=True)
            error_log_path = log_dir / 'errors.log'
            tb = None
            if exc is None:
                tb = traceback.format_exc()
            else:
                tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(error_log_path, 'a', encoding='utf-8') as ef:
                ef.write(f"[{timestamp}] {message}\n")
                ef.write(tb + "\n")
        except Exception:
            # 如果日志写入本身失败，则安全忽略，避免崩溃
            pass
