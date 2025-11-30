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

        # 禁用主窗口的下载功能
        self._disable_main_window_download()

        self._create_widgets()
        self._center_window(parent)

    def _disable_main_window_download(self):
        """禁用主窗口的下载功能"""
        try:
            if hasattr(self.master, 'execute_btn'):
                self.master.execute_btn.configure(state="disabled", text="🔄 更新中...")
            if hasattr(self.master, 'update_btn'):
                self.master.update_btn.configure(state="disabled")
        except Exception as e:
            self.logger.warning(f"禁用下载功能失败: {e}")

    def _enable_main_window_download(self):
        """重新启用主窗口的下载功能"""
        try:
            if hasattr(self.master, 'execute_btn'):
                # 根据当前状态设置正确的按钮文本
                if hasattr(self.master, 'download_paused') and self.master.download_paused:
                    self.master.execute_btn.configure(state="normal", text="▶️ 继续下载")
                elif hasattr(self.master, 'is_downloading') and self.master.is_downloading:
                    self.master.execute_btn.configure(state="normal", text="⏸️ 暂停下载")
                else:
                    self.master.execute_btn.configure(state="normal", text="🔓 一键解锁")
            if hasattr(self.master, 'update_btn'):
                self.master.update_btn.configure(state="normal", text="🔄 检查更新")
        except Exception as e:
            self.logger.warning(f"启用下载功能失败: {e}")

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

        # 更新日志文本（直接在本窗口显示）
        if self.update_info.update_log_url:
            self.log_textbox = ctk.CTkTextbox(info_frame, width=440, height=120)
            self.log_textbox.pack(pady=(0, 10))
            self.log_textbox.insert("0.0", "正在加载更新日志...")
            # 异步加载日志并填充
            def load_log_thread():
                try:
                    content = self.updater.fetch_update_log(self.update_info)
                    if content:
                        self.after(0, lambda: (self.log_textbox.delete("0.0", "end"), self.log_textbox.insert("0.0", content)))
                    else:
                        self.after(0, lambda: (self.log_textbox.delete("0.0", "end"), self.log_textbox.insert("0.0", "无法加载更新日志或日志为空（请检查网络）。")))
                except Exception as e:
                    self.logger.warning(f"加载更新日志失败: {e}")
                    self.after(0, lambda: (self.log_textbox.delete("0.0", "end"), self.log_textbox.insert("0.0", f"加载日志失败: {e}")))

            threading.Thread(target=load_log_thread, daemon=True).start()

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

        # 稍后提醒按钮（强制/非强制更新均显示，但强制更新时会提示确认）
        # 注意: 强制更新仍会在界面中显示“稍后提醒”，以便用户有明确选择权，但点击时会弹出警告提示。
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
        """稍后提醒: 如果是强制更新，先弹出警告确认，确认后关闭对话框。"""
        try:
            if self.update_info.is_force_update(self.updater.current_version):
                # 温和提示: 强制更新的特殊处理
                res = messagebox.askokcancel(
                    "重要提示",
                    "此更新为重要更新，跳过可能导致程序功能异常或不兼容。\n确定要稍后提醒并关闭更新界面吗？"
                )
                if res:
                    # 仅关闭更新对话框，不重新打开
                    self._enable_main_window_download()
                    self.destroy()
                else:
                    # 取消关闭，继续保留更新对话
                    return
            else:
                self._enable_main_window_download()
                self.destroy()
        except Exception as e:
            self.logger.warning(f"处理稍后提醒时出错: {e}")
            try:
                self._enable_main_window_download()
            except Exception:
                pass
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

        message_text = "程序已成功更新到最新版本。\n请重启程序以应用更改。"
        # 如果 exe 的替换被延期(写为 *.new)，提示用户退出以完成替换
        if hasattr(self.updater, 'exe_replacement_pending') and self.updater.exe_replacement_pending:
            message_text = '更新已准备好，但需要重新启动以完成替换（会在退出后自动应用）。\n请点击"立即重启"以退出并完成更新。'

        message_label = ctk.CTkLabel(
            self,
            text=message_text,
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
            # 检查是否正在下载DLC，如果是则暂停下载
            if hasattr(self.master, 'is_downloading') and self.master.is_downloading:
                self.logger.info("检测到正在下载DLC，正在暂停下载...")
                self.master.pause_download()
                # 保存下载状态标记
                self._save_download_state()

            import sys
            import os
            # 如果 exe 替换已排程（在 apply_update 中写入 .new 并创建替换脚本），直接退出主进程以便批处理替换
            if hasattr(self.updater, 'exe_replacement_pending') and self.updater.exe_replacement_pending:
                # 触发退出，让替换批处理接管并重启
                os._exit(0)

            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            self.logger.error(f"重启失败: {e}")
            messagebox.showerror("错误", f"重启失败: {e}")

    def _save_download_state(self):
        """保存下载状态以便重启后恢复"""
        try:
            import json
            from ..utils import PathUtils

            state_file = PathUtils.get_cache_dir() / "download_state.json"
            state = {
                "download_paused": True,
                "timestamp": self._get_timestamp()
            }

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

            self.logger.info("下载状态已保存")
        except Exception as e:
            self.logger.error(f"保存下载状态失败: {e}")

    @staticmethod
    def _get_timestamp():
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _on_close(self):
        """窗口关闭事件"""
        if self.update_info.is_force_update(self.updater.current_version):
            # 温和提示: 强制更新时也允许关闭，但先询问用户是否确认关闭更新
            res = messagebox.askokcancel(
                "重要提示",
                "此更新为重要更新，跳过可能导致程序功能异常或不兼容。\n是否仍要关闭更新界面？"
            )
            if not res:
                return

        self._enable_main_window_download()
        self.destroy()