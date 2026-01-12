#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置对话框模块
提供应用程序设置界面，包括源管理等功能
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
from pathlib import Path
from typing import Optional
import logging
import os


class SettingsDialog(ctk.CTkToplevel):
    """设置对话框"""

    def __init__(self, parent, main_logger=None, is_downloading_callback=None):
        super().__init__(parent)

        self.main_logger = main_logger  # 主窗口的日志记录器
        self.is_downloading_callback = is_downloading_callback  # 检查下载状态的回调函数
        self.logger = logging.getLogger(__name__)

        self.title("设置")
        self.geometry("700x500")
        self.resizable(False, False)

        # 设置窗口图标
        try:
            from ..utils.path_utils import PathUtils
            icon_path = PathUtils.get_resource_path("assets/images/icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            self.logger.warning(f"设置窗口图标失败: {e}")

        # 设置模态
        self.grab_set()
        self.focus_set()

        self._create_widgets()
        self._center_window(parent)

    def _center_window(self, parent):
        """居中显示窗口"""
        self.update_idletasks()
        
        # 获取父窗口位置和大小
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 计算居中位置
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title_label = ctk.CTkLabel(
            main_frame,
            text="⚙️ 设置",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#1976D2"
        )
        title_label.pack(pady=(0, 20))

        # 选项卡
        self.tabview = ctk.CTkTabview(main_frame, height=350)
        self.tabview.pack(fill="both", expand=True)

        # 添加选项卡（常规设置排在最前面）
        self.tabview.add("常规设置")
        self.tabview.add("测速")
        self.tabview.add("配置管理")
        # 可以添加更多选项卡
        # self.tabview.add("高级选项")

        # 创建选项卡内容
        self._create_general_settings_tab()
        self._create_speed_test_tab()
        self._create_config_tab()

        # 底部按钮
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(20, 0))

        close_btn = ctk.CTkButton(
            button_frame,
            text="关闭",
            command=self.destroy,
            width=120,
            height=40,
            font=ctk.CTkFont(size=14),
            corner_radius=8,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        close_btn.pack(side="right")

    def _create_source_management_tab(self):
        """创建源管理选项卡内容"""
        tab = self.tabview.tab("源管理")

        # 说明文字
        info_label = ctk.CTkLabel(
            tab,
            text="管理下载源，测试各源的连接速度",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        info_label.pack(pady=(10, 20))
        # （配置路径已移至“配置管理”选项卡）

        # 源列表框架
        sources_frame = ctk.CTkScrollableFrame(
            tab,
            height=200,
            fg_color="#FAFAFA",
            corner_radius=8
        )
        sources_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 获取源列表 - 从config导入DLC_SOURCES
        from ..config import DLC_SOURCES
        sources = DLC_SOURCES if DLC_SOURCES else []
            
        for i, source in enumerate(sources):
            source_frame = ctk.CTkFrame(sources_frame, fg_color="#FFFFFF", corner_radius=6)
            source_frame.pack(fill="x", padx=5, pady=5)

            # 源信息
            info_frame = ctk.CTkFrame(source_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=10)

            name_label = ctk.CTkLabel(
                info_frame,
                text=f"📡 {source.get('name', '未知源')}",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            name_label.pack(anchor="w")

            # 显示测试URL（如果有）或基础URL
            display_url = source.get('test_url', '') or source.get('url', '')
            url_label = ctk.CTkLabel(
                info_frame,
                text=display_url,
                font=ctk.CTkFont(size=10),
                text_color="#666666",
                anchor="w"
            )
            url_label.pack(anchor="w")

            status_label = ctk.CTkLabel(
                info_frame,
                text=f"优先级: {source.get('priority', 'N/A')} | 状态: {'✓ 启用' if source.get('enabled', True) else '✗ 禁用'}",
                font=ctk.CTkFont(size=10),
                text_color="#888888",
                anchor="w"
            )
            status_label.pack(anchor="w")

            # 速度标签（用于显示测速结果）
            speed_label = ctk.CTkLabel(
                source_frame,
                text="",
                font=ctk.CTkFont(size=11),
                text_color="#1976D2",
                width=100
            )
            speed_label.pack(side="right", padx=10)

            # 保存引用以便更新
            source_frame.speed_label = speed_label
            source_frame.source_data = source

        # 按钮框架
        button_frame = ctk.CTkFrame(tab, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=10)

        # 测速所有源按钮
        test_all_btn = ctk.CTkButton(
            button_frame,
            text="🚀 测速所有源",
            command=self._test_all_sources,
            width=140,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            fg_color="#4CAF50",
            hover_color="#45a049",
            text_color="#FFFFFF"
        )
        test_all_btn.pack(side="left", padx=5)

        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            button_frame,
            text="🔄 刷新",
            command=self._refresh_sources,
            width=100,
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        refresh_btn.pack(side="left", padx=5)

        # 保存引用
        self.sources_frame = sources_frame
        self.test_all_btn = test_all_btn

    def _test_all_sources(self):
        """已废弃 - 仅支持GitLink单一源"""
        pass

    def _copy_config_path(self):
        """复制 config.json 路径到剪贴板"""
        try:
            path = self.config_path_entry.get()
            self.clipboard_clear()
            self.clipboard_append(path)
            self.update()
            messagebox.showinfo("已复制", "配置路径已复制到剪贴板")
        except Exception as e:
            messagebox.showwarning("复制失败", f"无法复制配置路径: {e}")

    def _copy_log_path(self):
        """复制日志目录路径到剪贴板"""
        try:
            path = self.log_path_entry.get()
            self.clipboard_clear()
            self.clipboard_append(path)
            self.update()
            messagebox.showinfo("已复制", "日志路径已复制到剪贴板")
        except Exception as e:
            messagebox.showwarning("复制失败", f"无法复制日志路径: {e}")

    def _open_config_in_explorer(self):
        """在资源管理器中打开 config.json 所在目录"""
        try:
            from pathlib import Path
            path_str = self.config_path_entry.get()
            p = Path(path_str)
            target = p if p.exists() and p.is_file() else p.parent
            import subprocess
            if os.name == 'nt':
                subprocess.Popen(['explorer', str(target)])
            else:
                # cross-platform fallback
                subprocess.Popen(['xdg-open', str(target)])
        except Exception as e:
            messagebox.showwarning("打开失败", f"无法打开路径: {e}")

    def _open_log_in_explorer(self):
        """在资源管理器中打开日志目录"""
        try:
            from pathlib import Path
            path_str = self.log_path_entry.get()
            p = Path(path_str)
            target = p if p.exists() and p.is_dir() else p.parent if p.exists() else p
            import subprocess
            if os.name == 'nt':
                subprocess.Popen(['explorer', str(target)])
            else:
                # cross-platform fallback
                subprocess.Popen(['xdg-open', str(target)])
        except Exception as e:
            messagebox.showwarning("打开失败", f"无法打开路径: {e}")

    def _create_general_settings_tab(self):
        """创建常规设置选项卡"""
        tab = self.tabview.tab("常规设置")

        # 创建可滚动框架
        scrollable_frame = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent"
        )
        scrollable_frame.pack(fill="both", expand=True, padx=0, pady=0)

        info_label = ctk.CTkLabel(
            scrollable_frame,
            text="常规设置：配置应用程序的基本行为",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        info_label.pack(pady=(10, 20))

        # 公告显示设置框架
        announcement_frame = ctk.CTkFrame(scrollable_frame, fg_color="#FFFFFF", corner_radius=8)
        announcement_frame.pack(fill="x", padx=20, pady=(0, 15))

        # 标题行
        announcement_title_frame = ctk.CTkFrame(announcement_frame, fg_color="transparent")
        announcement_title_frame.pack(fill="x", padx=15, pady=(15, 10))

        announcement_title = ctk.CTkLabel(
            announcement_title_frame,
            text="📢 公告显示设置",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#1976D2"
        )
        announcement_title.pack(side="left")

        # 内容区域
        announcement_content_frame = ctk.CTkFrame(announcement_frame, fg_color="transparent")
        announcement_content_frame.pack(fill="x", padx=20, pady=(5, 15))

        # 左侧：描述信息
        left_frame = ctk.CTkFrame(announcement_content_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True)

        desc_label = ctk.CTkLabel(
            left_frame,
            text="启动时显示系统公告\n每个版本的公告独立控制",
            font=ctk.CTkFont(size=12),
            text_color="#666666",
            anchor="w",
            justify="left"
        )
        desc_label.pack(anchor="w")

        # 右侧：开关按钮
        right_frame = ctk.CTkFrame(announcement_content_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=(20, 0))

        # 读取当前配置
        from ..config import VERSION
        from .. import config_loader
        dismissed_version = config_loader.get_config("settings", "dismissed_announcement_version", default="")
        # 如果记录的版本与当前版本相同，说明已禁用
        is_enabled = (dismissed_version != VERSION)
        
        self.announcement_switch_var = ctk.BooleanVar(value=is_enabled)
        announcement_switch = ctk.CTkSwitch(
            right_frame,
            text="",
            variable=self.announcement_switch_var,
            command=self._toggle_announcement,
            width=50,
            height=24
        )
        announcement_switch.pack()

        # 状态标签
        self.announcement_status_label = ctk.CTkLabel(
            right_frame,
            text="已启用" if is_enabled else "已禁用",
            font=ctk.CTkFont(size=11),
            text_color="#4CAF50" if is_enabled else "#999999"
        )
        self.announcement_status_label.pack(pady=(5, 0))

        # 更新文件管理框架
        update_files_frame = ctk.CTkFrame(scrollable_frame, fg_color="#FFFFFF", corner_radius=8)
        update_files_frame.pack(fill="x", padx=20, pady=(15, 15))

        # 标题行
        update_title_frame = ctk.CTkFrame(update_files_frame, fg_color="transparent")
        update_title_frame.pack(fill="x", padx=15, pady=(15, 10))

        update_title = ctk.CTkLabel(
            update_title_frame,
            text="🗂️ 更新文件管理",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#1976D2"
        )
        update_title.pack(side="left")

        # 说明文本
        update_desc_label = ctk.CTkLabel(
            update_files_frame,
            text="清理更新过程中产生的临时文件和残留文件",
            font=ctk.CTkFont(size=11),
            text_color="#999999"
        )
        update_desc_label.pack(padx=15, pady=(0, 10), anchor="w")

        # 按钮容器
        update_btn_frame = ctk.CTkFrame(update_files_frame, fg_color="transparent")
        update_btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        # 清理临时文件按钮
        clean_temp_btn = ctk.CTkButton(
            update_btn_frame,
            text="🗑️ 清理临时文件",
            command=self._clean_temp_files,
            width=150,
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            fg_color="#1976D2",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        clean_temp_btn.pack(side="left", padx=(0, 10))

        # 清理备份文件按钮
        clean_backup_btn = ctk.CTkButton(
            update_btn_frame,
            text="🗑️ 清理备份文件",
            command=self._clean_backup_files,
            width=150,
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            fg_color="#1976D2",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        clean_backup_btn.pack(side="left", padx=(0, 10))

        # 清理更新下载包按钮
        clean_update_pkg_btn = ctk.CTkButton(
            update_btn_frame,
            text="🗑️ 清理更新下载包",
            command=self._clean_update_packages,
            width=150,
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            fg_color="#1976D2",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        clean_update_pkg_btn.pack(side="left")

        # 文件统计信息
        self.update_files_info_label = ctk.CTkLabel(
            update_files_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        )
        self.update_files_info_label.pack(padx=15, pady=(0, 10), anchor="w")

        # 更新文件统计信息
        self._update_files_info()

    def _toggle_announcement(self):
        """切换公告显示设置"""
        try:
            from ..config import VERSION
            from .. import config_loader
            import json
            
            is_enabled = self.announcement_switch_var.get()
            
            # 读取当前配置
            config_path = config_loader._loader.config_path
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 确保settings节点存在
            if "settings" not in config:
                config["settings"] = {}
            
            # 更新配置
            if is_enabled:
                # 启用公告：清空记录的版本号
                config["settings"]["dismissed_announcement_version"] = ""
                self.announcement_status_label.configure(
                    text="已启用",
                    text_color="#4CAF50"
                )
                self.logger.info("已启用公告显示")
            else:
                # 禁用公告：保存当前版本号
                config["settings"]["dismissed_announcement_version"] = VERSION
                self.announcement_status_label.configure(
                    text="已禁用",
                    text_color="#999999"
                )
                self.logger.info(f"已禁用v{VERSION}的公告显示")
            
            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 提示用户
            if is_enabled:
                messagebox.showinfo("设置已保存", "公告显示已启用\n\n下次启动时将显示系统公告")
            else:
                messagebox.showinfo("设置已保存", "公告显示已禁用\n\n下次启动时将不再显示本版本公告")
            
        except Exception as e:
            self.logger.error(f"切换公告显示设置失败: {e}", exc_info=True)
            messagebox.showerror("保存失败", f"无法保存设置:\n{str(e)}")
            # 恢复开关状态
            self.announcement_switch_var.set(not self.announcement_switch_var.get())

    def _create_config_tab(self):
        """创建配置管理选项卡内容（显示生效的 config.json 路径等）"""
        tab = self.tabview.tab("配置管理")

        info_label = ctk.CTkLabel(
            tab,
            text="配置管理：显示当前生效的配置文件路径和日志目录，便于诊断与手动替换",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        info_label.pack(pady=(10, 16))

        try:
            from .. import config_loader
            cfg_path = getattr(config_loader, '_loader').config_path
        except Exception:
            cfg_path = "(未找到)"

        # 配置文件路径框架
        cfg_frame = ctk.CTkFrame(tab, fg_color="#FFFFFF", corner_radius=6)
        cfg_frame.pack(fill="x", padx=10, pady=(0, 12))
        cfg_frame.grid_columnconfigure(0, weight=0, minsize=180)
        cfg_frame.grid_columnconfigure(1, weight=1)
        cfg_frame.grid_columnconfigure(2, weight=0)

        cfg_label = ctk.CTkLabel(
            cfg_frame,
            text="配置文件路径:",
            font=ctk.CTkFont(size=11),
            text_color="#333333"
        )
        cfg_label.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=8)

        # 路径输入框，占据中间可扩展列
        self.config_path_entry = ctk.CTkEntry(
            cfg_frame,
            width=20,
            height=32,
            font=ctk.CTkFont(size=11),
            state="normal"
        )
        try:
            self.config_path_entry.insert(0, str(cfg_path))
            self.config_path_entry.configure(state="readonly")
        except Exception:
            self.config_path_entry.insert(0, "(未找到)")
            self.config_path_entry.configure(state="readonly")
        self.config_path_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)

        # 右侧按钮容器，固定大小，内含复制与打开按钮垂直/水平排列
        btn_container = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        btn_container.grid(row=0, column=2, sticky="e", padx=(0, 12), pady=8)

        copy_btn = ctk.CTkButton(
            btn_container,
            text="复制",
            width=90,
            height=32,
            font=ctk.CTkFont(size=11),
            command=self._copy_config_path
        )
        copy_btn.pack(side="left", padx=(0, 6))

        open_btn = ctk.CTkButton(
            btn_container,
            text="打开目录",
            width=110,
            height=32,
            font=ctk.CTkFont(size=11),
            command=self._open_config_in_explorer
        )
        open_btn.pack(side="left")

        # 日志目录路径框架
        try:
            from ..utils.path_utils import PathUtils
            log_path = PathUtils.get_log_dir()
        except Exception:
            log_path = "(未找到)"

        log_frame = ctk.CTkFrame(tab, fg_color="#FFFFFF", corner_radius=6)
        log_frame.pack(fill="x", padx=10, pady=(0, 12))
        log_frame.grid_columnconfigure(0, weight=0, minsize=180)
        log_frame.grid_columnconfigure(1, weight=1)
        log_frame.grid_columnconfigure(2, weight=0)

        log_label = ctk.CTkLabel(
            log_frame,
            text="日志目录路径:",
            font=ctk.CTkFont(size=11),
            text_color="#333333"
        )
        log_label.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=8)

        # 日志路径输入框
        self.log_path_entry = ctk.CTkEntry(
            log_frame,
            width=20,
            height=32,
            font=ctk.CTkFont(size=11),
            state="normal"
        )
        try:
            self.log_path_entry.insert(0, str(log_path))
            self.log_path_entry.configure(state="readonly")
        except Exception:
            self.log_path_entry.insert(0, "(未找到)")
            self.log_path_entry.configure(state="readonly")
        self.log_path_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)

        # 日志路径按钮容器
        log_btn_container = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_btn_container.grid(row=0, column=2, sticky="e", padx=(0, 12), pady=8)

        log_copy_btn = ctk.CTkButton(
            log_btn_container,
            text="复制",
            width=90,
            height=32,
            font=ctk.CTkFont(size=11),
            command=self._copy_log_path
        )
        log_copy_btn.pack(side="left", padx=(0, 6))

        log_open_btn = ctk.CTkButton(
            log_btn_container,
            text="打开目录",
            width=110,
            height=32,
            font=ctk.CTkFont(size=11),
            command=self._open_log_in_explorer
        )
        log_open_btn.pack(side="left")

    def _update_files_info(self):
        """更新文件统计信息"""
        try:
            from ..utils.path_utils import PathUtils
            from pathlib import Path
            cache_dir = Path(PathUtils.get_cache_dir())
            
            # 统计 .new 文件（临时文件）
            temp_files = list(cache_dir.parent.glob("*.new"))
            temp_size = sum(f.stat().st_size for f in temp_files if f.is_file())
            
            # 统计备份文件
            backup_files = []
            backup_size = 0
            backup_dir = cache_dir / "backup"
            if backup_dir.exists():
                for file in backup_dir.glob("**/*"):
                    if file.is_file():
                        backup_files.append(file)
                        backup_size += file.stat().st_size
            
            # 统计更新下载包（系统临时文件夹中的更新包）
            import tempfile
            system_temp_dir = Path(tempfile.gettempdir()) / "StellarisUpdate"
            update_pkg_files = []
            update_pkg_size = 0
            if system_temp_dir.exists():
                for file in system_temp_dir.glob("*.zip"):
                    if file.is_file() and "Stellaris-DLC-Helper" in file.name:
                        update_pkg_files.append(file)
                        update_pkg_size += file.stat().st_size
            
            # 格式化文件大小
            def format_size(size_bytes):
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
            
            info_text = f"临时文件: {len(temp_files)} 个 ({format_size(temp_size)})  |  备份文件: {len(backup_files)} 个 ({format_size(backup_size)})  |  更新下载包: {len(update_pkg_files)} 个 ({format_size(update_pkg_size)})"
            self.update_files_info_label.configure(text=info_text)
            
        except Exception as e:
            self.logger.warning(f"更新文件统计失败: {e}")
            self.update_files_info_label.configure(text="无法获取文件统计信息")

    def _clean_temp_files(self):
        """清理临时文件（.new 文件）"""
        try:
            # 确认对话框
            result = messagebox.askyesno(
                "确认清理",
                "确定要清理临时文件吗？\n\n此操作将删除程序目录中的 *.new 文件。\n\n此操作不可恢复！",
                icon="warning"
            )
            
            if not result:
                return
            
            from ..utils.path_utils import PathUtils
            from pathlib import Path
            cache_dir = Path(PathUtils.get_cache_dir())
            deleted_count = 0
            deleted_size = 0
            
            # 清理 .new 文件
            for new_file in cache_dir.parent.glob("*.new"):
                if new_file.is_file():
                    try:
                        size = new_file.stat().st_size
                        new_file.unlink()
                        deleted_count += 1
                        deleted_size += size
                        self.logger.info(f"已删除: {new_file.name}")
                    except Exception as e:
                        self.logger.warning(f"删除文件失败 {new_file}: {e}")
            
            # 格式化大小
            def format_size(size_bytes):
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
            
            # 更新统计信息
            self._update_files_info()
            
            messagebox.showinfo(
                "清理完成",
                f"已成功清理 {deleted_count} 个临时文件\n释放空间: {format_size(deleted_size)}"
            )
            
        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}", exc_info=True)
            messagebox.showerror("清理失败", f"清理临时文件时出错:\n{str(e)}")

    def _clean_backup_files(self):
        """清理备份文件"""
        try:
            # 确认对话框
            result = messagebox.askyesno(
                "确认清理",
                "确定要清理备份文件吗？\n\n此操作将删除 backup 目录下的所有备份文件。\n\n⚠️ 警告: 此操作不可恢复！清理后将无法回滚更新！",
                icon="warning"
            )
            
            if not result:
                return
            
            from ..utils.path_utils import PathUtils
            from pathlib import Path
            cache_dir = Path(PathUtils.get_cache_dir())
            backup_dir = cache_dir / "backup"
            deleted_count = 0
            deleted_size = 0
            
            if backup_dir.exists():
                for file in backup_dir.glob("**/*"):
                    if file.is_file():
                        try:
                            size = file.stat().st_size
                            file.unlink()
                            deleted_count += 1
                            deleted_size += size
                        except Exception as e:
                            self.logger.warning(f"删除备份文件失败 {file}: {e}")
                
                # 清理空目录
                try:
                    import shutil
                    for subdir in backup_dir.glob("*"):
                        if subdir.is_dir() and not any(subdir.iterdir()):
                            subdir.rmdir()
                except Exception as e:
                    self.logger.warning(f"清理空目录失败: {e}")
            
            # 格式化大小
            def format_size(size_bytes):
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
            
            # 更新统计信息
            self._update_files_info()
            
            messagebox.showinfo(
                "清理完成",
                f"已成功清理 {deleted_count} 个备份文件\n释放空间: {format_size(deleted_size)}"
            )
            
        except Exception as e:
            self.logger.error(f"清理备份文件失败: {e}", exc_info=True)
            messagebox.showerror("清理失败", f"清理备份文件时出错:\n{str(e)}")

    def _clean_update_packages(self):
        """清理更新下载包（系统临时文件夹中的zip文件）"""
        try:
            # 确认对话框
            result = messagebox.askyesno(
                "确认清理",
                "确定要清理更新下载包吗？\n\n此操作将删除系统临时文件夹中的所有更新程序压缩包。\n\n此操作不可恢复！",
                icon="warning"
            )
            
            if not result:
                return
            
            from pathlib import Path
            import tempfile
            # 使用系统临时文件夹（与 updater.py 中一致）
            system_temp_dir = Path(tempfile.gettempdir()) / "StellarisUpdate"
            deleted_count = 0
            deleted_size = 0
            
            if system_temp_dir.exists():
                # 只清理系统临时文件夹中的更新包 zip 文件
                for file in system_temp_dir.glob("*.zip"):
                    if file.is_file() and "Stellaris-DLC-Helper" in file.name:
                        try:
                            size = file.stat().st_size
                            file.unlink()
                            deleted_count += 1
                            deleted_size += size
                            self.logger.info(f"已删除更新包: {file.name}")
                        except Exception as e:
                            self.logger.warning(f"删除更新包失败 {file}: {e}")
            
            # 格式化大小
            def format_size(size_bytes):
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
            
            # 更新统计信息
            self._update_files_info()
            
            messagebox.showinfo(
                "清理完成",
                f"已成功清理 {deleted_count} 个更新下载包\n释放空间: {format_size(deleted_size)}"
            )
            
        except Exception as e:
            self.logger.error(f"清理更新下载包失败: {e}", exc_info=True)
            messagebox.showerror("清理失败", f"清理更新下载包时出错:\n{str(e)}")

    def _create_speed_test_tab(self):
        """创建测速选项卡"""
        tab = self.tabview.tab("测速")
        
        # 标题
        title_label = ctk.CTkLabel(
            tab,
            text="🚀 GitLink源速度测试",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1976D2"
        )
        title_label.pack(pady=(15, 5))
        
        # 创建可滚动容器
        scrollable_frame = ctk.CTkScrollableFrame(
            tab,
            fg_color="#F8F9FA",
            corner_radius=0
        )
        scrollable_frame.pack(fill="both", expand=True, padx=0, pady=(10, 0))
        
        # GitLink测速模块
        speed_frame = ctk.CTkFrame(scrollable_frame, fg_color="#FFFFFF", corner_radius=8)
        speed_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        # 内容框架（左右布局）
        content_frame = ctk.CTkFrame(speed_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=20)
        
        # 左侧：描述信息
        left_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True)
        
        title = ctk.CTkLabel(
            left_frame,
            text="📊 GitLink下载速度",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#333333",
            anchor="w"
        )
        title.pack(anchor="w", pady=(0, 8))
        
        desc = ctk.CTkLabel(
            left_frame,
            text="测试GitLink源的下载速度\n测试文件: test.bin (约70MB)\n评估网络连接质量",
            font=ctk.CTkFont(size=12),
            text_color="#666666",
            anchor="w",
            justify="left"
        )
        desc.pack(anchor="w")
        
        # 右侧：速度显示
        right_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=(20, 0))
        
        # 速度标签（大号显示）
        self.speed_value_label = ctk.CTkLabel(
            right_frame,
            text="--",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#4CAF50"
        )
        self.speed_value_label.pack(pady=(0, 5))
        
        # 单位标签
        self.speed_unit_label = ctk.CTkLabel(
            right_frame,
            text="MB/s",
            font=ctk.CTkFont(size=14),
            text_color="#999999"
        )
        self.speed_unit_label.pack()
        
        # 状态标签
        self.speed_status_label = ctk.CTkLabel(
            right_frame,
            text="未测试",
            font=ctk.CTkFont(size=12),
            text_color="#999999"
        )
        self.speed_status_label.pack(pady=(5, 0))
        
        # 测速按钮（在容器外）
        button_frame = ctk.CTkFrame(tab, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.speed_test_btn = ctk.CTkButton(
            button_frame,
            text="🚀 开始测速",
            command=self._start_speed_test,
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#4CAF50",
            hover_color="#45A049"
        )
        self.speed_test_btn.pack()
    
    def _start_speed_test(self):
        """开始GitLink源速度测试"""
        import threading
        import time
        import requests
        
        def test_thread():
            try:
                # 禁用按钮
                self.speed_test_btn.configure(state="disabled", text="测速中...")
                
                # 重置显示状态
                self.speed_value_label.configure(text="0.00", text_color="#FF9800")
                self.speed_status_label.configure(text="正在连接...", text_color="#FF9800")
                
                # GitLink test.bin URL (正确的URL)
                test_url = "https://gitlink.org.cn/signriver/file-warehouse/releases/download/test/test.bin"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                total_downloaded = 0
                start_time = time.time()
                last_update_time = start_time
                
                with requests.get(test_url, headers=headers, stream=True, timeout=(7.0, 10.0)) as response:
                    if not response.ok:
                        raise Exception(f"服务器返回状态码 {response.status_code}")
                    
                    self.speed_status_label.configure(text="正在测速...", text_color="#FF9800")
                    
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            break
                        
                        total_downloaded += len(chunk)
                        current_time = time.time()
                        elapsed = current_time - start_time
                        
                        # 每0.3秒更新一次显示
                        if current_time - last_update_time >= 0.3:
                            if elapsed > 0.001:
                                speed_mbps = (total_downloaded / (1024 * 1024)) / elapsed
                                self.speed_value_label.configure(text=f"{speed_mbps:.2f}")
                                last_update_time = current_time
                        
                        # 测速超过10秒或下载超过70MB就停止
                        if elapsed >= 10.0 or total_downloaded >= 70 * 1024 * 1024:
                            break
                
                # 计算最终速度
                final_duration = time.time() - start_time
                if final_duration <= 0.001:
                    final_duration = 0.001
                
                speed_mbps = (total_downloaded / (1024 * 1024)) / final_duration
                
                # 更新最终速度显示
                self.speed_value_label.configure(text=f"{speed_mbps:.2f}")
                
                # 根据速度设置评价和颜色
                if speed_mbps >= 5:
                    status_text = "优秀 ⭐⭐⭐⭐⭐"
                    color = "#4CAF50"
                elif speed_mbps >= 2:
                    status_text = "良好 ⭐⭐⭐⭐"
                    color = "#8BC34A"
                elif speed_mbps >= 1:
                    status_text = "一般 ⭐⭐⭐"
                    color = "#FFC107"
                elif speed_mbps >= 0.5:
                    status_text = "较慢 ⭐⭐"
                    color = "#FF9800"
                else:
                    status_text = "很慢 ⭐"
                    color = "#F44336"
                
                self.speed_value_label.configure(text_color=color)
                self.speed_status_label.configure(text=status_text, text_color=color)
                
                self.logger.info(f"GitLink测速完成: {speed_mbps:.2f} MB/s (下载 {total_downloaded/(1024*1024):.2f} MB)")
                
            except Exception as e:
                self.logger.error(f"测速失败: {e}", exc_info=True)
                self.speed_value_label.configure(text="失败", text_color="#F44336")
                self.speed_status_label.configure(text=f"连接超时或网络错误", text_color="#F44336")
            
            finally:
                # 恢复按钮
                self.speed_test_btn.configure(state="normal", text="🚀 开始测速")
        
        # 在后台线程执行测速
        threading.Thread(target=test_thread, daemon=True).start()

