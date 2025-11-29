#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新对话框模块
提供更新检查、下载和安装的用户界面
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import webbrowser
from pathlib import Path
from typing import Optional, Callable
import logging

from ..core.updater import AutoUpdater, UpdateInfo


class UpdateDialog(ctk.CTkToplevel):
    """更新对话框"""

    def __init__(self, parent, update_info: UpdateInfo):
        super().__init__(parent)

        self.update_info = update_info
        self.updater = AutoUpdater()
        self.logger = logging.getLogger(__name__)

        self.title("发现新版本")
        self.geometry("500x400")
        self.resizable(False, False)

        # 设置模态
        self.grab_set()
        self.focus_set()

        self._create_widgets()
        self._center_window(parent)

    def _create_widgets(self):
        """创建界面组件"""
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text=f"发现新版本 {self.update_info.latest_version}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(20, 10))

        # 版本信息
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=20, pady=(0, 20))

        current_label = ctk.CTkLabel(
            info_frame,
            text=f"当前版本: {self.updater.current_version}",
            font=ctk.CTkFont(size=12)
        )
        current_label.pack(anchor="w", padx=15, pady=(10, 5))

        latest_label = ctk.CTkLabel(
            info_frame,
            text=f"最新版本: {self.update_info.latest_version}",
            font=ctk.CTkFont(size=12)
        )
        latest_label.pack(anchor="w", padx=15, pady=(0, 5))

        if self.update_info.release_date:
            date_label = ctk.CTkLabel(
                info_frame,
                text=f"发布日期: {self.update_info.release_date}",
                font=ctk.CTkFont(size=12)
            )
            date_label.pack(anchor="w", padx=15, pady=(0, 5))

        if self.update_info.file_size:
            size_label = ctk.CTkLabel(
                info_frame,
                text=f"文件大小: {self.update_info.file_size}",
                font=ctk.CTkFont(size=12)
            )
            size_label.pack(anchor="w", padx=15, pady=(0, 10))

        # 更新日志按钮
        if self.update_info.update_log_url:
            log_button = ctk.CTkButton(
                info_frame,
                text="查看更新日志",
                command=self._show_update_log
            )
            log_button.pack(pady=(0, 10))

        # 强制更新提示
        if self.update_info.is_force_update(self.updater.current_version):
            force_label = ctk.CTkLabel(
                info_frame,
                text="⚠️ 此更新为强制更新，必须安装才能继续使用",
                text_color="red",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            force_label.pack(pady=(0, 10))

        # 按钮区域
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        # 稍后提醒按钮（非强制更新时显示）
        if not self.update_info.is_force_update(self.updater.current_version):
            later_button = ctk.CTkButton(
                button_frame,
                text="稍后提醒",
                command=self._remind_later
            )
            later_button.pack(side="left", padx=(0, 10))

        # 立即更新按钮
        update_button = ctk.CTkButton(
            button_frame,
            text="立即更新",
            command=self._start_update
        )
        update_button.pack(side="right")

        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self, parent):
        """居中窗口"""
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        width = self.winfo_width()
        height = self.winfo_height()

        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2

        self.geometry(f"+{x}+{y}")

    def _show_update_log(self):
        """显示更新日志"""
        try:
            webbrowser.open(self.update_info.update_log_url)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开更新日志: {e}")

    def _remind_later(self):
        """稍后提醒"""
        self.destroy()

    def _start_update(self):
        """开始更新"""
        # 隐藏当前界面，显示下载进度
        for widget in self.winfo_children():
            widget.destroy()

        self._create_download_ui()

        # 开始下载
        def download_thread():
            try:
                zip_path = self.updater.download_update(
                    self.update_info,
                    self._update_progress
                )

                if zip_path:
                    self.after(0, lambda: self._show_install_ui(zip_path))
                else:
                    self.after(0, lambda: self._show_error("下载失败"))

            except Exception as e:
                self.logger.error(f"下载更新失败: {e}")
                self.after(0, lambda: self._show_error(f"下载失败: {e}"))

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def _create_download_ui(self):
        """创建下载进度界面"""
        title_label = ctk.CTkLabel(
            self,
            text="正在下载更新...",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(30, 20))

        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(self, text="0%")
        self.progress_label.pack()

    def _update_progress(self, current: int, total: int):
        """更新下载进度"""
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)
            percentage = int(progress * 100)
            self.progress_label.configure(text=f"{percentage}% ({current}/{total} bytes)")

    def _show_install_ui(self, zip_path: Path):
        """显示安装界面"""
        # 清除下载界面
        for widget in self.winfo_children():
            widget.destroy()

        title_label = ctk.CTkLabel(
            self,
            text="正在安装更新...",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(30, 20))

        progress_label = ctk.CTkLabel(self, text="请稍候，正在应用更新...")
        progress_label.pack(pady=(0, 20))

        # 开始安装
        def install_thread():
            try:
                success = self.updater.apply_update(zip_path)

                if success:
                    self.after(0, self._show_success)
                else:
                    self.after(0, lambda: self._show_error("安装失败"))

            except Exception as e:
                self.logger.error(f"安装更新失败: {e}")
                self.after(0, lambda: self._show_error(f"安装失败: {e}"))

        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()

    def _show_success(self):
        """显示成功界面"""
        for widget in self.winfo_children():
            widget.destroy()

        success_label = ctk.CTkLabel(
            self,
            text="✅ 更新完成！",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="green"
        )
        success_label.pack(pady=(30, 10))

        message_label = ctk.CTkLabel(
            self,
            text="程序已成功更新到最新版本。\n请重启程序以应用更改。",
            font=ctk.CTkFont(size=12)
        )
        message_label.pack(pady=(0, 20))

        restart_button = ctk.CTkButton(
            self,
            text="立即重启",
            command=self._restart_app
        )
        restart_button.pack(pady=(0, 10))

        later_button = ctk.CTkButton(
            self,
            text="稍后重启",
            command=self.destroy
        )
        later_button.pack()

    def _show_error(self, message: str):
        """显示错误界面"""
        for widget in self.winfo_children():
            widget.destroy()

        error_label = ctk.CTkLabel(
            self,
            text="❌ 更新失败",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="red"
        )
        error_label.pack(pady=(30, 10))

        message_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=12)
        )
        message_label.pack(pady=(0, 20))

        retry_button = ctk.CTkButton(
            self,
            text="重试",
            command=self._start_update
        )
        retry_button.pack(pady=(0, 10))

        close_button = ctk.CTkButton(
            self,
            text="关闭",
            command=self.destroy
        )
        close_button.pack()

    def _restart_app(self):
        """重启应用程序"""
        try:
            import sys
            import os
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            self.logger.error(f"重启失败: {e}")
            messagebox.showerror("错误", f"重启失败: {e}")

    def _on_close(self):
        """窗口关闭事件"""
        if self.update_info.is_force_update(self.updater.current_version):
            # 强制更新时不允许关闭
            messagebox.showwarning("提示", "此更新为强制更新，请完成更新后再关闭。")
            return

        self.destroy()