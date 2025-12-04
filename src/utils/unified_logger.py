#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志系统
整合GUI日志、文件日志、错误日志和操作日志到一个统一的管理系统
"""

import logging
import traceback
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional, Callable
import threading


class UnifiedLogger:
    """
    统一日志管理器
    
    职责分离：
    1. GUI日志：用户界面操作提示（简洁）
    2. 文件日志：详细的程序运行日志（stellaris_dlc_helper.log）
    3. 错误日志：专门记录错误和异常堆栈（errors.log）
    4. 操作日志：用户操作记录（operations_*.json，独立模块）
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志系统"""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            # GUI 组件（可选）
            self.gui_widget = None
            self.gui_root = None
            
            # 日志配置
            self.log_dir = None
            self.file_logger = None
            self.error_logger = None
            
            # 标记避免循环日志
            self._in_gui_logging = False
            
            self._initialized = True
    
    def configure(
        self,
        log_dir: str,
        level: int = logging.INFO,
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 5
    ):
        """
        配置日志系统
        
        参数:
            log_dir: 日志目录
            level: 日志级别
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的日志文件数量
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # 清除现有处理器（避免重复）
        root_logger.handlers.clear()
        
        # 1. 控制台处理器（用于开发调试）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 2. 文件处理器（详细日志）
        file_log_path = self.log_dir / 'stellaris_dlc_helper.log'
        file_handler = RotatingFileHandler(
            str(file_log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(name)s - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # 3. 错误日志处理器（仅ERROR及以上）
        error_log_path = self.log_dir / 'errors.log'
        error_handler = RotatingFileHandler(
            str(error_log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '[%(asctime)s] %(name)s - %(levelname)s: %(message)s\n%(pathname)s:%(lineno)d\n',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
        
        # 4. 添加GUI处理器（如果GUI已设置）
        if self.gui_widget is not None:
            gui_handler = self._create_gui_handler()
            root_logger.addHandler(gui_handler)
        
        logging.info(f"日志系统已配置，日志目录: {self.log_dir}")
    
    def set_gui_widget(self, widget, root):
        """
        设置GUI日志组件
        
        参数:
            widget: Tkinter ScrolledText 组件
            root: Tkinter 根窗口
        """
        self.gui_widget = widget
        self.gui_root = root
        
        # 如果日志系统已配置，添加GUI处理器
        root_logger = logging.getLogger()
        if root_logger.handlers:
            # 移除旧的GUI处理器
            root_logger.handlers = [
                h for h in root_logger.handlers 
                if not isinstance(h, GUIHandler)
            ]
            # 添加新的GUI处理器
            gui_handler = self._create_gui_handler()
            root_logger.addHandler(gui_handler)
    
    def _create_gui_handler(self):
        """创建GUI日志处理器"""
        handler = GUIHandler(self)
        handler.setLevel(logging.INFO)  # GUI只显示INFO及以上
        formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        return handler
    
    def _write_to_gui(self, message: str, level: str):
        """
        写入GUI日志（线程安全）
        
        参数:
            message: 日志消息
            level: 日志级别
        """
        if self._in_gui_logging:
            return  # 防止循环
            
        if not self.gui_widget or not self.gui_root:
            return
        
        try:
            self._in_gui_logging = True
            
            # 根据级别添加图标
            if level == 'ERROR':
                formatted = f"✗ {message}\n"
            elif level == 'WARNING':
                formatted = f"⚠ {message}\n"
            elif level == 'SUCCESS':
                formatted = f"✓ {message}\n"
            else:
                formatted = f"{message}\n"
            
            # 使用after确保在主线程中更新GUI
            if self.gui_root:
                self.gui_root.after(0, lambda: self._insert_to_gui(formatted))
            else:
                self._insert_to_gui(formatted)
        finally:
            self._in_gui_logging = False
    
    def _insert_to_gui(self, message: str):
        """实际插入到GUI组件"""
        if self.gui_widget:
            try:
                self.gui_widget.insert("end", message)
                self.gui_widget.see("end")
            except Exception:
                pass  # 忽略GUI更新错误
    
    def gui_success(self, message: str):
        """GUI成功消息（仅显示在GUI，不记录到文件）"""
        self._write_to_gui(message, 'SUCCESS')
    
    def log_exception(self, message: str, exc: Optional[Exception] = None):
        """
        记录异常（带完整堆栈跟踪）
        
        参数:
            message: 错误消息
            exc: 异常对象（可选）
        """
        # 1. 在GUI显示简短错误信息
        self._write_to_gui(message, 'ERROR')
        
        # 2. 使用标准logging记录异常（会自动写入文件日志和错误日志）
        logger = logging.getLogger(__name__)
        if exc:
            logger.error(f"{message}: {str(exc)}", exc_info=exc)
        else:
            logger.exception(message)
        
        # 3. 额外写入详细的错误日志文件（带完整堆栈）
        self._write_detailed_error_log(message, exc)
    
    def _write_detailed_error_log(self, message: str, exc: Optional[Exception] = None):
        """写入详细错误日志（带分隔线和完整堆栈）"""
        if not self.log_dir:
            return
            
        try:
            error_log_path = self.log_dir / 'errors.log'
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
                    tb = traceback.format_exc()
                    if tb and tb != "NoneType: None\n":
                        f.write(tb)
                
                f.write("\n")
        except Exception:
            pass  # 忽略错误日志写入失败
    
    def safe_execute(
        self,
        func: Callable,
        error_message: str = "操作失败",
        show_in_gui: bool = True,
        return_on_error=None
    ):
        """
        安全执行函数（自动处理异常）
        
        参数:
            func: 要执行的函数
            error_message: 错误消息前缀
            show_in_gui: 是否在GUI显示错误
            return_on_error: 发生错误时的返回值
            
        返回:
            函数执行结果，或错误时的return_on_error
        """
        try:
            return func()
        except Exception as e:
            if show_in_gui:
                self.log_exception(f"{error_message}: {str(e)}", e)
            else:
                logger = logging.getLogger(__name__)
                logger.error(f"{error_message}: {str(e)}", exc_info=True)
            return return_on_error
    
    def get_log_file_path(self, log_type: str = 'main') -> str:
        """
        获取日志文件路径
        
        参数:
            log_type: 日志类型 ('main', 'error')
            
        返回:
            日志文件路径
        """
        if not self.log_dir:
            return ""
        
        if log_type == 'error':
            return str(self.log_dir / 'errors.log')
        else:
            return str(self.log_dir / 'stellaris_dlc_helper.log')


class GUIHandler(logging.Handler):
    """GUI日志处理器"""
    
    def __init__(self, unified_logger: UnifiedLogger):
        super().__init__()
        self.unified_logger = unified_logger
    
    def emit(self, record):
        """处理日志记录"""
        try:
            msg = self.format(record)
            level = record.levelname
            self.unified_logger._write_to_gui(msg, level)
        except Exception:
            pass  # 忽略GUI日志处理错误


# 全局单例实例
_logger_instance: Optional[UnifiedLogger] = None


def get_logger() -> UnifiedLogger:
    """获取全局日志管理器实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = UnifiedLogger()
    return _logger_instance


def configure_logging(
    log_dir: str,
    level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5
):
    """配置全局日志系统"""
    logger = get_logger()
    logger.configure(log_dir, level, max_bytes, backup_count)


def set_gui_widget(widget, root):
    """设置GUI日志组件"""
    logger = get_logger()
    logger.set_gui_widget(widget, root)


# 便捷函数（兼容旧代码）
def log_exception(message: str, exc: Optional[Exception] = None):
    """记录异常"""
    logger = get_logger()
    logger.log_exception(message, exc)


def safe_execute(
    func: Callable,
    error_message: str = "操作失败",
    show_in_gui: bool = True,
    return_on_error=None
):
    """安全执行函数"""
    logger = get_logger()
    return logger.safe_execute(func, error_message, show_in_gui, return_on_error)
