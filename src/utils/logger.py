#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
"""

from datetime import datetime


class Logger:
    """日志管理类"""
    
    def __init__(self, log_widget=None):
        """
        初始化日志管理器
        
        Args:
            log_widget: Tkinter ScrolledText 组件
        """
        self.log_widget = log_widget
        
    def set_widget(self, log_widget):
        """设置日志组件"""
        self.log_widget = log_widget
        
    def log(self, message, level="INFO"):
        """
        写入日志
        
        Args:
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
