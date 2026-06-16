#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单实例锁：防止用户多次双击启动多个程序窗口
"""

import sys
import logging

logger = logging.getLogger(__name__)

# 保持 mutex 句柄存活，进程退出前不释放
_mutex_handle = None

MUTEX_NAME = "Stellaris-DLC-Helper-SingleInstance"


def ensure_single_instance(show_message: bool = True) -> bool:
    """
    尝试获取单实例锁。

    返回:
        True  - 当前是第一个实例，可继续启动
        False - 已有实例在运行
    """
    if sys.platform != "win32":
        return True

    global _mutex_handle

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183

        _mutex_handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            if _mutex_handle:
                kernel32.CloseHandle(_mutex_handle)
                _mutex_handle = None
            if show_message:
                _show_already_running_dialog()
            return False

        return True
    except Exception as e:
        logger.warning(f"单实例检测失败，允许继续启动: {e}")
        return True


def _show_already_running_dialog():
    """提示用户程序已在运行"""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        messagebox.showwarning(
            "程序已在运行",
            "Stellaris DLC Helper 已经在运行中，请不要重复打开。\n\n"
            "如果看不到窗口，请检查任务栏是否已最小化。",
            parent=root,
        )
        root.destroy()
    except Exception as e:
        logger.warning(f"无法显示单实例提示: {e}")
