#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新/公告对话框模块
提供更新检查、下载和安装的用户界面，同时支持显示系统公告
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import webbrowser
from pathlib import Path
from typing import Optional, Callable
import logging
import sys
import os
import subprocess
import json
import time

from ..core.updater import AutoUpdater, UpdateInfo


class UpdateDialog(ctk.CTkToplevel):
    """更新/公告对话框"""
    
    @staticmethod
    def should_show_announcement():
        """
        检查是否应该显示公告
        如果当前版本的公告已被用户标记为"不再显示"，则返回False
        """
        try:
            from ..config import VERSION
            from .. import config_loader
            
            # 读取配置
            dismissed_version = config_loader.get_config("settings", "dismissed_announcement_version", default="")
            
            # 如果记录的版本与当前版本相同，说明用户已选择不再显示
            if dismissed_version == VERSION:
                return False
            
            return True
        except Exception:
            # 出错时默认显示公告
            return True

    def __init__(self, parent, update_info: Optional[UpdateInfo] = None, announcement: str = ""):
        super().__init__(parent)

        self.update_info = update_info
        self.announcement = announcement
        self.updater = AutoUpdater()
        self.logger = logging.getLogger(__name__)
        self.dont_show_again_var = ctk.BooleanVar(value=False)
        
        try:
            # 根据是否有更新设置标题
            if update_info and update_info.has_update(self.updater.current_version):
                self.title(f"发现新版本 {update_info.latest_version}")
            else:
                self.title("系统公告")
            
            # 先隐藏窗口，避免闪烁
            self.withdraw()
            
            # 根据内容调整窗口高度
            if update_info and update_info.has_update(self.updater.current_version):
                # 有更新时的高度
                self.geometry("520x460")
            elif announcement:
                # 只有公告：中等高度
                self.geometry("520x420")
            else:
                # 默认高度
                self.geometry("520x400")
            
            self.resizable(False, False)

            # 设置窗口图标
            try:
                from ..utils.path_utils import PathUtils
                icon_path = PathUtils.get_resource_path("assets/images/tea_Gray.ico")
                if os.path.exists(icon_path):
                    self.iconbitmap(icon_path)
            except Exception as e:
                self.logger.warning(f"设置窗口图标失败: {e}")

            # 设置模态
            self.grab_set()
            self.focus_set()

            # 禁用主窗口的下载功能
            if update_info and update_info.has_update(self.updater.current_version):
                self._disable_main_window_download()

            self._create_widgets()
            self._center_window(parent)
            
            # 居中完成后再显示窗口
            self.deiconify()
            
        except Exception as e:
            # 如果初始化失败，确保释放grab并销毁窗口
            self.logger.error(f"UpdateDialog初始化失败: {e}")
            try:
                self.grab_release()
            except:
                pass
            try:
                self.destroy()
            except:
                pass
            raise  # 重新抛出异常让调用者知道失败了

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
        # 判断是否有更新
        has_update = self.update_info and self.update_info.has_update(self.updater.current_version)
        
        # 如果有更新，显示更新部分
        if has_update:
            # 标题
            title_label = ctk.CTkLabel(
                self,
                text=f"发现新版本 {self.update_info.latest_version}",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            title_label.pack(pady=(20, 10))

            # 版本信息
            info_frame = ctk.CTkFrame(self)
            info_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))

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

            # 更新信息文本框（使用公告内容填充）
            if self.announcement:
                self.info_textbox = ctk.CTkTextbox(
                    info_frame, 
                    width=440, 
                    height=120, 
                    wrap="char",
                    font=ctk.CTkFont(size=13),
                    fg_color="#F8F9FA"
                )
                self.info_textbox.pack(fill='both', expand=True, pady=(0, 10))
                # 增加行间距，让文本更透气
                self.info_textbox.insert("0.0", self.announcement)
                # 设置文本间距
                self.info_textbox.tag_config("spacing", spacing1=3, spacing3=3)
                self.info_textbox.tag_add("spacing", "1.0", "end")
                self.info_textbox.configure(state="disabled")  # 只读

            # 强制更新提示
            if self.update_info.is_force_update(self.updater.current_version):
                force_label = ctk.CTkLabel(
                    info_frame,
                    text="⚠️ 此更新为强制更新，必须安装才能继续使用",
                    text_color="red",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                force_label.pack(pady=(0, 10))

        # 如果只有公告没有更新，显示公告
        if self.announcement and not has_update:
            # 公告标题
            announcement_title = ctk.CTkLabel(
                self,
                text="📢 系统公告",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#FF6B00"
            )
            announcement_title.pack(pady=(20, 10))

            # 公告内容框
            announcement_frame = ctk.CTkFrame(self)
            announcement_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))

            announcement_textbox = ctk.CTkTextbox(
                announcement_frame, 
                width=440, 
                height=240,
                wrap="char",
                font=ctk.CTkFont(size=13),
                fg_color="#F8F9FA"
            )
            announcement_textbox.pack(fill='both', expand=True, padx=10, pady=10)
            # 增加行间距，让文本更透气
            announcement_textbox.insert("0.0", self.announcement)
            # 设置文本间距
            announcement_textbox.tag_config("spacing", spacing1=3, spacing3=3)
            announcement_textbox.tag_add("spacing", "1.0", "end")
            announcement_textbox.configure(state="disabled")  # 只读

            # 不再显示复选框
            dont_show_frame = ctk.CTkFrame(self, fg_color="transparent")
            dont_show_frame.pack(fill="x", padx=20, pady=(0, 5))
            
            dont_show_checkbox = ctk.CTkCheckBox(
                dont_show_frame,
                text="本版本不再显示此公告",
                variable=self.dont_show_again_var,
                font=ctk.CTkFont(size=12),
                text_color="#666666"
            )
            dont_show_checkbox.pack(anchor="w")

        # 按钮区域
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 20))

        if has_update:
            # 有更新时显示更新相关按钮
            later_button = ctk.CTkButton(
                button_frame,
                text="稍后提醒",
                command=self._remind_later,
                height=40,
                text_color="white",
                font=("Microsoft YaHei UI", 13)
            )
            later_button.pack(side="left", padx=(0, 10))

            update_button = ctk.CTkButton(
                button_frame,
                text="立即更新",
                command=self._start_update,
                height=40,
                text_color="white",
                font=("Microsoft YaHei UI", 13)
            )
            update_button.pack(side="right")
        else:
            # 只有公告时显示关闭按钮
            close_button = ctk.CTkButton(
                button_frame,
                text="知道了",
                command=self._close_announcement,
                height=40,
                text_color="white",
                font=("Microsoft YaHei UI", 13)
            )
            close_button.pack(side="right")

        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _close_announcement(self):
        """关闭公告"""
        # 如果用户勾选了不再显示，保存版本号
        if self.dont_show_again_var.get():
            self._save_announcement_dismissed()
        
        try:
            self.grab_release()  # 释放模态锁
        except Exception:
            pass
        self._enable_main_window_download()
        self.destroy()
    
    def _save_announcement_dismissed(self):
        """保存用户已查看公告的版本号"""
        try:
            from ..config import VERSION
            from .. import config_loader
            import json
            
            # 读取当前配置
            config_path = config_loader._loader.config_path
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 确保settings节点存在
            if "settings" not in config:
                config["settings"] = {}
            
            # 保存已查看的公告版本号
            config["settings"]["dismissed_announcement_version"] = VERSION
            
            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"已保存公告查看记录: v{VERSION}")
        except Exception as e:
            self.logger.error(f"保存公告查看记录失败: {e}", exc_info=True)

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
                    try:
                        self.grab_release()  # 释放模态锁
                    except Exception:
                        pass
                    self._enable_main_window_download()
                    self.destroy()
                else:
                    # 取消关闭，继续保留更新对话
                    return
            else:
                try:
                    self.grab_release()  # 释放模态锁
                except Exception:
                    pass
                self._enable_main_window_download()
                self.destroy()
        except Exception as e:
            self.logger.warning(f"处理稍后提醒时出错: {e}")
            try:
                self.grab_release()  # 释放模态锁
            except Exception:
                pass
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
                self.logger.info(f"开始安装更新包: {zip_path}")
                success = self.updater.apply_update(zip_path)

                if success:
                    # 创建更新成功标记文件
                    self._create_update_marker()
                    self.logger.info("更新安装成功")
                    self.after(0, self._show_success)
                else:
                    self.logger.error("更新安装失败")
                    self.after(0, lambda: self._show_error("安装失败，请查看日志了解详情"))

            except Exception as e:
                self.logger.error(f"安装更新失败: {e}", exc_info=True)
                self.after(0, lambda: self._show_error(f"安装失败: {str(e)[:100]}"))

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

        import sys
        is_frozen = getattr(sys, 'frozen', False)
        
        message_text = "程序已成功更新到最新版本。\n请重启程序以应用更改。"
        # 如果 exe 的替换被延期(写为 *.new)，提示用户退出以完成替换（仅在 exe 模式下）
        if is_frozen and hasattr(self.updater, 'exe_replacement_pending') and self.updater.exe_replacement_pending:
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
            command=self._restart_app,
            height=40,
            font=("Microsoft YaHei UI", 13)
        )
        restart_button.pack(pady=10)

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
            import subprocess
            from pathlib import Path
            
            # 判断是否为打包后的 exe 模式
            is_frozen = getattr(sys, 'frozen', False)
            
            # 检查是否有 .new 文件待替换（updater_helper.exe 已启动）
            from ..utils.path_utils import PathUtils
            app_root = Path(PathUtils.get_base_dir())
            new_files = list(app_root.glob("*.new"))
            has_new_files = len(new_files) > 0
            
            # 如果有 .new 文件，说明 updater_helper.exe 已启动并等待主程序退出
            # 直接退出，让 updater_helper.exe 完成替换并启动新进程
            if is_frozen and has_new_files:
                self.logger.info(f"检测到 {len(new_files)} 个 .new 文件待替换: {[f.name for f in new_files]}")
                self.logger.info(f"updater_helper.exe 正在等待，准备退出主程序...")
                # 短暂延迟确保日志写入和窗口关闭
                import time
                time.sleep(0.3)
                self.logger.info("主程序即将退出，updater_helper.exe 将接管文件替换和重启")
                os._exit(0)
            
            # 如果 exe 替换已排程（在 apply_update 中写入 .new 并创建替换脚本），且是 exe 模式，直接退出主进程以便批处理替换
            if is_frozen and hasattr(self.updater, 'exe_replacement_pending') and self.updater.exe_replacement_pending:
                # 触发退出，让替换批处理接管并重启
                self.logger.info("exe 替换已排程，退出以完成替换")
                os._exit(0)
            
            # 在 exe 模式下，使用 subprocess.Popen 启动新进程然后退出
            # 这样可以避免 PyInstaller 临时目录 _MEI 的问题
            if is_frozen:
                exe_path = sys.executable
                self.logger.info(f"exe 模式：启动新进程后退出: {exe_path}")
                # 启动新进程（不等待）
                # Windows: 隐藏窗口
                creationflags = 0
                if sys.platform == 'win32':
                    creationflags = 0x08000000  # CREATE_NO_WINDOW
                subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path), creationflags=creationflags)
                # 短暂延迟确保新进程启动
                import time
                time.sleep(0.5)
                # 退出当前进程
                os._exit(0)
            else:
                # 开发环境：直接重启当前进程
                python = sys.executable
                self.logger.info(f"开发环境：重启程序: {python} {sys.argv}")
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

    def _create_update_marker(self):
        """创建更新完成标记文件"""
        try:
            import json
            import os
            from ..utils import PathUtils
            from ..config import VERSION as CURRENT_VERSION
            
            marker_file = os.path.join(PathUtils.get_cache_dir(), "update_completed.json")
            marker_data = {
                "old_version": self.updater.current_version,
                "new_version": self.update_info.latest_version,
                "timestamp": self._get_timestamp(),
                "success": True
            }
            
            with open(marker_file, 'w', encoding='utf-8') as f:
                json.dump(marker_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"已创建更新标记文件: {marker_file}")
        except Exception as e:
            self.logger.error(f"创建更新标记文件失败: {e}")
    
    @staticmethod
    def _get_timestamp():
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _on_close(self):
        """窗口关闭事件"""
        if self.update_info and self.update_info.is_force_update(self.updater.current_version):
            # 温和提示: 强制更新时也允许关闭，但先询问用户是否确认关闭更新
            res = messagebox.askokcancel(
                "重要提示",
                "此更新为重要更新，跳过可能导致程序功能异常或不兼容。\n是否仍要关闭更新界面？"
            )
            if not res:
                return

        try:
            self.grab_release()  # 释放模态锁
        except Exception:
            pass
        self._enable_main_window_download()
        self.destroy()
