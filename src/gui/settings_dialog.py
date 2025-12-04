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

    def __init__(self, parent, source_manager=None, main_logger=None, is_downloading_callback=None):
        super().__init__(parent)

        self.source_manager = source_manager
        self.main_logger = main_logger  # 主窗口的日志记录器
        self.is_downloading_callback = is_downloading_callback  # 检查下载状态的回调函数
        self.logger = logging.getLogger(__name__)

        self.title("设置")
        self.geometry("700x500")
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
        self.tabview.add("源管理")
        self.tabview.add("配置管理")
        # 可以添加更多选项卡
        # self.tabview.add("高级选项")

        # 创建选项卡内容
        self._create_general_settings_tab()
        self._create_source_management_tab()
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
        """测试所有源的速度"""
        # 检查是否正在下载
        if self.is_downloading_callback and self.is_downloading_callback():
            messagebox.showwarning("提示", "下载进行中，无法进行测速操作！\n请等待下载完成后再测速。")
            return
        
        if not self.source_manager:
            messagebox.showwarning("警告", "源管理器未初始化")
            return

        # 禁用按钮
        self.test_all_btn.configure(state="disabled", text="⏳ 测速中...")

        def test_thread():
            try:
                # 获取所有源
                from ..config import DLC_SOURCES
                sources = DLC_SOURCES if DLC_SOURCES else []
                
                # 记录测速开始
                if self.main_logger:
                    self.main_logger.info(f"开始测速，共 {len(sources)} 个源")
                
                tested_count = 0
                for widget in self.sources_frame.winfo_children():
                    if hasattr(widget, 'source_data') and hasattr(widget, 'speed_label'):
                        source = widget.source_data
                        speed_label = widget.speed_label
                        source_name = source.get('name', '未知源')
                        
                        tested_count += 1
                        
                        # 更新状态
                        self.after(0, lambda l=speed_label: l.configure(text="测速中..."))
                        
                        # 记录测速进度
                        if self.main_logger:
                            self.main_logger.info(f"正在测速: {source_name}")
                        
                        # 测试速度
                        try:
                            from ..core.speed_test import test_speed
                            test_url = source.get('test_url', '')
                            
                            if test_url:
                                speed = test_speed(test_url, timeout=10)
                                if speed > 0:
                                    speed_mb = speed / (1024 * 1024)
                                    speed_text = f"✓ {speed_mb:.2f} MB/s"
                                    color = "#4CAF50"
                                    if self.main_logger:
                                        self.main_logger.info(f"{source_name}: {speed_mb:.2f} MB/s")
                                else:
                                    speed_text = "✗ 超时"
                                    color = "#F44336"
                                    if self.main_logger:
                                        self.main_logger.warning(f"{source_name}: 超时")
                            else:
                                speed_text = "⚠ 无测试URL"
                                color = "#FF9800"
                                if self.main_logger:
                                    self.main_logger.warning(f"{source_name}: 无测试URL")
                            
                            self.after(0, lambda l=speed_label, t=speed_text, c=color: (
                                l.configure(text=t, text_color=c)
                            ))
                        except Exception as e:
                            error_msg = str(e)
                            if self.main_logger:
                                self.main_logger.error(f"{source_name} 测速失败: {error_msg}")
                            self.after(0, lambda l=speed_label: l.configure(
                                text=f"✗ 错误",
                                text_color="#F44336"
                            ))
                
                if self.main_logger:
                    self.main_logger.info(f"测速完成，共测试 {tested_count} 个源")
                
                self.after(0, lambda: messagebox.showinfo("完成", f"源测速已完成\n共测试 {tested_count} 个源"))
                
            except Exception as e:
                error_msg = str(e)
                # 记录错误到日志
                import logging
                logging.error(f"源测速失败: {error_msg}", exc_info=True)
                # 如果有主窗口logger，也记录到那里
                if self.main_logger:
                    self.main_logger.error(f"源测速失败: {error_msg}")
                self.after(0, lambda msg=error_msg: messagebox.showerror("错误", f"测速失败:\n{msg}"))
            finally:
                self.after(0, lambda: self.test_all_btn.configure(state="normal", text="🚀 测速所有源"))

        threading.Thread(target=test_thread, daemon=True).start()

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

    def _refresh_sources(self):
        """刷新源列表"""
        # 重新创建源管理选项卡
        self._create_source_management_tab()
        messagebox.showinfo("完成", "源列表已刷新")

    def _create_general_settings_tab(self):
        """创建常规设置选项卡"""
        tab = self.tabview.tab("常规设置")

        info_label = ctk.CTkLabel(
            tab,
            text="常规设置：配置应用程序的基本行为",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        info_label.pack(pady=(10, 20))

        # 获取当前配置
        try:
            from .. import config_loader
            skip_test = config_loader.get_config("settings", "skip_speed_test", default=False)
            default_source = config_loader.get_config("settings", "default_source", default="github")
        except Exception:
            skip_test = False
            default_source = "github"

        # 跳过启动测速设置框架
        speed_test_frame = ctk.CTkFrame(tab, fg_color="#FFFFFF", corner_radius=8)
        speed_test_frame.pack(fill="x", padx=20, pady=(0, 15))

        # 标题行
        title_frame = ctk.CTkFrame(speed_test_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(15, 10))

        speed_title = ctk.CTkLabel(
            title_frame,
            text="⚡ 启动测速设置",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#1976D2"
        )
        speed_title.pack(side="left")

        # 跳过测速开关
        switch_frame = ctk.CTkFrame(speed_test_frame, fg_color="transparent")
        switch_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.skip_test_var = ctk.BooleanVar(value=skip_test)
        skip_test_switch = ctk.CTkSwitch(
            switch_frame,
            text="跳过启动时的源测速",
            variable=self.skip_test_var,
            command=self._on_skip_test_changed,
            font=ctk.CTkFont(size=13),
            switch_width=50,
            switch_height=24
        )
        skip_test_switch.pack(side="left")

        # 说明文本
        desc_label = ctk.CTkLabel(
            speed_test_frame,
            text="启用后，程序启动时将不进行源测速，直接使用下方选择的默认源",
            font=ctk.CTkFont(size=11),
            text_color="#999999"
        )
        desc_label.pack(padx=15, pady=(0, 10), anchor="w")

        # 分隔线
        separator = ctk.CTkFrame(speed_test_frame, height=1, fg_color="#E0E0E0")
        separator.pack(fill="x", padx=15, pady=10)

        # 默认源选择
        source_frame = ctk.CTkFrame(speed_test_frame, fg_color="transparent")
        source_frame.pack(fill="x", padx=15, pady=(0, 15))

        source_label = ctk.CTkLabel(
            source_frame,
            text="默认下载源:",
            font=ctk.CTkFont(size=13),
            text_color="#333333"
        )
        source_label.pack(side="left", padx=(0, 15))

        # 获取所有可用源
        try:
            from ..config import DLC_SOURCES
            sources = DLC_SOURCES if DLC_SOURCES else []
            source_names = [s.get("name", "") for s in sources if s.get("enabled", True)]
            # 源的中文显示名称映射
            source_display_names = {
                "r2": "R2 (推荐)",
                "github": "GitHub",
                "domestic_cloud": "国内云",
                "gitee": "Gitee"
            }
        except Exception:
            source_names = ["r2", "github", "domestic_cloud", "gitee"]
            source_display_names = {
                "r2": "R2 (推荐)",
                "github": "GitHub",
                "domestic_cloud": "国内云",
                "gitee": "Gitee"
            }

        # 确保默认源在列表中
        if default_source not in source_names:
            default_source = source_names[0] if source_names else "github"

        self.default_source_var = ctk.StringVar(value=default_source)

        # 创建单选按钮
        radio_container = ctk.CTkFrame(source_frame, fg_color="transparent")
        radio_container.pack(side="left", fill="x", expand=True)

        for idx, source_name in enumerate(source_names):
            display_name = source_display_names.get(source_name, source_name)
            radio = ctk.CTkRadioButton(
                radio_container,
                text=display_name,
                variable=self.default_source_var,
                value=source_name,
                font=ctk.CTkFont(size=12),
                radiobutton_width=18,
                radiobutton_height=18
            )
            radio.pack(side="left", padx=(0, 20))

        # 根据初始状态设置单选按钮启用/禁用
        self._update_source_radios_state()

        # 保存按钮
        save_frame = ctk.CTkFrame(tab, fg_color="transparent")
        save_frame.pack(fill="x", padx=20, pady=(10, 0))

        save_btn = ctk.CTkButton(
            save_frame,
            text="💾 保存设置",
            command=self._save_general_settings,
            width=140,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        save_btn.pack(side="left")

        hint_label = ctk.CTkLabel(
            save_frame,
            text="提示: 修改设置后需要重启程序才能生效",
            font=ctk.CTkFont(size=11),
            text_color="#FF9800"
        )
        hint_label.pack(side="left", padx=15)

    def _on_skip_test_changed(self):
        """跳过测速选项改变时的回调"""
        self._update_source_radios_state()

    def _update_source_radios_state(self):
        """根据跳过测速开关状态更新源选择单选按钮的启用状态"""
        skip = self.skip_test_var.get()
        # 查找所有单选按钮并设置状态
        try:
            tab = self.tabview.tab("常规设置")
            for widget in tab.winfo_children():
                self._update_radios_recursive(widget, "normal" if skip else "disabled")
        except Exception:
            pass

    def _update_radios_recursive(self, widget, state):
        """递归更新单选按钮状态"""
        if isinstance(widget, ctk.CTkRadioButton):
            widget.configure(state=state)
        for child in widget.winfo_children():
            self._update_radios_recursive(child, state)

    def _save_general_settings(self):
        """保存常规设置到config.json"""
        try:
            from .. import config_loader
            import json

            # 读取当前配置
            config_path = config_loader._loader.config_path
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 确保settings节点存在
            if "settings" not in config:
                config["settings"] = {}

            # 更新设置
            config["settings"]["skip_speed_test"] = self.skip_test_var.get()
            config["settings"]["default_source"] = self.default_source_var.get()

            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("保存成功", "设置已保存！\n\n请重启程序使设置生效。")
            self.logger.info(f"常规设置已保存: skip_speed_test={self.skip_test_var.get()}, default_source={self.default_source_var.get()}")

        except Exception as e:
            error_msg = str(e)
            messagebox.showerror("保存失败", f"无法保存设置:\n{error_msg}")
            import logging
            logging.error(f"保存常规设置失败: {error_msg}", exc_info=True)

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
