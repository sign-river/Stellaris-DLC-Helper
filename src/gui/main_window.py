#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块 - CustomTkinter 版本
逐步迁移原有功能到现代化界面
"""

import os
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from ..config import VERSION
from ..core import DLCManager, DLCDownloader, DLCInstaller, PatchManager
from ..utils import Logger, PathUtils


# 设置外观模式和颜色主题 - 清爽现代风格
ctk.set_appearance_mode("light")  # "dark" 或 "light" 或 "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"


class MainWindowCTk:
    """主窗口类 - CustomTkinter版本"""
    
    def __init__(self, root):
        """
        初始化主窗口
        
        Args:
            root: CustomTkinter根窗口
        """
        self.root = root
        self.root.title(f"Stellaris DLC Helper v{VERSION}")
        self.root.geometry("1000x750")
        
        # 设置清爽现代风格背景
        self.root.configure(fg_color="#F5F7FA")
        
        # 状态变量
        self.game_path = ""
        self.dlc_list = []
        self.dlc_checkboxes = []  # 存储复选框对象
        
        # 核心组件
        self.dlc_manager = None
        self.dlc_downloader = None
        self.dlc_installer = None
        self.patch_manager = None
        self.logger = Logger()
        
        # 初始化UI
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        # 配置网格布局
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 创建标题区域
        self._create_header()
        
        # 创建主内容区域
        self._create_content_area()
        
    def _create_header(self):
        """创建标题区域"""
        header_frame = ctk.CTkFrame(self.root, corner_radius=0, height=100, fg_color=["#3a7ebf", "#1f538d"])
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)
        
        # 标题
        title_label = ctk.CTkLabel(
            header_frame,
            text="🌟 Stellaris DLC Helper",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="white"
        )
        title_label.pack(pady=(25, 5))
        
        # 副标题
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="群星DLC一键解锁工具",
            font=ctk.CTkFont(size=14),
            text_color="#B0BEC5"  # 浅灰蓝色
        )
        subtitle_label.pack()
        
    def _create_content_area(self):
        """创建主内容区域"""
        # 主容器
        content_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content_frame.grid_rowconfigure(1, weight=5)  # DLC列表占更多空间
        content_frame.grid_rowconfigure(2, weight=1)  # 操作日志占少量空间
        content_frame.grid_columnconfigure(0, weight=1)
        
        # 游戏路径选择
        self._create_path_section(content_frame)
        
        # DLC列表区域
        self._create_dlc_section(content_frame)
        
        # 操作日志区域
        self._create_log_section(content_frame)
        
        # 按钮区域（固定在底部）
        self._create_button_section(content_frame)
        
    def _create_path_section(self, parent):
        """创建游戏路径选择区域"""
        path_frame = ctk.CTkFrame(
            parent, 
            corner_radius=10, 
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E0E0E0"
        )
        path_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        path_frame.grid_columnconfigure(0, weight=1)
        
        # 标签
        label = ctk.CTkLabel(
            path_frame,
            text="📁 游戏路径",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1976D2"  # 主色调蓝色
        )
        label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))
        
        # 输入框和按钮容器
        input_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        input_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        input_frame.grid_columnconfigure(0, weight=1)
        
        # 路径输入框
        self.path_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="请选择 Stellaris 游戏根目录...",
            height=40,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            fg_color="#FFFFFF",
            text_color="#212121",
            border_color="#BDBDBD",
            border_width=1
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # 浏览按钮
        browse_btn = ctk.CTkButton(
            input_frame,
            text="浏览",
            command=self.browse_game_path,
            width=100,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            fg_color="#1976D2",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        browse_btn.grid(row=0, column=1)
        
        # 加载DLC列表按钮
        load_btn = ctk.CTkButton(
            input_frame,
            text="加载DLC列表",
            command=self.load_dlc_list,
            width=120,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            fg_color="#1976D2",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        load_btn.grid(row=0, column=2, padx=(10, 0))
        
    def _create_dlc_section(self, parent):
        """创建DLC列表区域"""
        dlc_frame = ctk.CTkFrame(
            parent, 
            corner_radius=10, 
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E0E0E0"
        )
        dlc_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        dlc_frame.grid_rowconfigure(2, weight=1)
        dlc_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        label = ctk.CTkLabel(
            dlc_frame,
            text="📦 DLC列表",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1976D2"  # 主色调蓝色
        )
        label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))
        
        # 控制按钮区（右对齐）
        control_header_frame = ctk.CTkFrame(dlc_frame, fg_color="transparent")
        control_header_frame.grid(row=1, column=0, sticky="e", padx=15, pady=(0, 10))
        
        # 全选按钮（次要 - 浅蓝）
        self.select_all_btn = ctk.CTkButton(
            control_header_frame,
            text="全选",
            command=self.toggle_select_all,
            width=80,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        self.select_all_btn.pack(side="left", padx=(0, 10))
        
        # 反选按钮（次要 - 浅蓝）
        inverse_btn = ctk.CTkButton(
            control_header_frame,
            text="反选",
            command=self.inverse_selection,
            width=80,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        inverse_btn.pack(side="left")
        
        # 滚动框架（用于显示DLC列表）
        self.dlc_scrollable_frame = ctk.CTkScrollableFrame(
            dlc_frame,
            corner_radius=8,
            fg_color="#FAFAFA"
        )
        self.dlc_scrollable_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.dlc_scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # 显示初始提示
        hint_label = ctk.CTkLabel(
            self.dlc_scrollable_frame,
            text="请先选择游戏路径并加载DLC列表",
            font=ctk.CTkFont(size=13),
            text_color="#757575"
        )
        hint_label.pack(pady=20)
        
    def _create_button_section(self, parent):
        """创建按钮区域 - 固定在底部,分组对齐"""
        button_frame = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E0E0E0"
        )
        button_frame.grid(row=3, column=0, sticky="ew", pady=(0, 0))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # 进度标签
        self.progress_label = ctk.CTkLabel(
            button_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#1976D2"
        )
        self.progress_label.grid(row=0, column=0, columnspan=2, pady=(0, 8))
        
        # 左侧按钮组(危险/撤销区)
        left_btn_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_btn_container.grid(row=1, column=0, sticky="w", padx=(15, 10), pady=(0, 12))
        
        # 还原游戏按钮（次要 - 浅蓝）
        restore_btn = ctk.CTkButton(
            left_btn_container,
            text="🔄 还原游戏",
            command=self.restore_game,
            width=130,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        restore_btn.pack(side="left", padx=(0, 10))
        
        # 移除补丁按钮（次要 - 浅蓝）
        self.remove_patch_btn = ctk.CTkButton(
            left_btn_container,
            text="❌ 移除补丁",
            command=self.remove_patch,
            state="disabled",
            width=130,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        self.remove_patch_btn.pack(side="left")
        
        # 右侧按钮组(前进/执行区)
        right_btn_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_btn_container.grid(row=1, column=1, sticky="e", padx=(10, 15), pady=(0, 12))
        
        # 应用补丁按钮（重要 - 标准蓝）
        self.patch_btn = ctk.CTkButton(
            right_btn_container,
            text="🛠️ 应用补丁",
            command=self.apply_patch,
            state="disabled",
            width=130,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#1976D2",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        self.patch_btn.pack(side="left", padx=(0, 10))
        
        # 下载安装按钮（最重要 - 深蓝）
        self.download_btn = ctk.CTkButton(
            right_btn_container,
            text="📥 下载并安装选中的DLC",
            command=self.download_dlcs,
            state="disabled",
            width=220,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#0D47A1",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        self.download_btn.pack(side="left")
        
    def _create_log_section(self, parent):
        """创建日志区域"""
        log_frame = ctk.CTkFrame(
            parent, 
            corner_radius=10, 
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E0E0E0"
        )
        log_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        # 标题
        label = ctk.CTkLabel(
            log_frame,
            text="📋 操作日志",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1976D2"  # 主色调蓝色
        )
        label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))
        
        # 日志文本框
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=60,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            corner_radius=8,
            fg_color="#FAFAFA",
            text_color="#212121",
            border_color="#E0E0E0",
            border_width=1
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # 设置日志组件
        self.logger.set_widget(self.log_text)
        
    # ========== 以下是业务逻辑方法，将逐步从旧版本迁移 ==========
    
    def browse_game_path(self):
        """浏览选择游戏路径"""
        path = filedialog.askdirectory(title="选择Stellaris游戏根目录")
        if path:
            # 验证是否是Stellaris目录
            if not PathUtils.validate_stellaris_path(path):
                messagebox.showwarning("警告", 
                    "所选目录似乎不是Stellaris游戏目录！\n"
                    "请确保选择包含 stellaris.exe 的文件夹。")
                return
            
            self.game_path = path
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
            
            # 初始化核心组件
            self.dlc_manager = DLCManager(path)
            self.dlc_installer = DLCInstaller(path)
            self.patch_manager = PatchManager(path, self.logger)
            
            self.logger.info(f"已选择游戏路径: {path}")
            
            # 检查补丁状态
            self._check_patch_status()
        
    def load_dlc_list(self):
        """加载DLC列表"""
        if not self.game_path:
            # 在DLC列表框中显示提示
            for widget in self.dlc_scrollable_frame.winfo_children():
                widget.destroy()
            hint_label = ctk.CTkLabel(
                self.dlc_scrollable_frame,
                text="请先选择游戏路径并加载DLC列表",
                font=ctk.CTkFont(size=13),
                text_color="#757575"
            )
            hint_label.pack(pady=20)
            messagebox.showwarning("提示", "请先选择游戏路径！")
            return
        
        # 在DLC列表框中显示加载状态
        for widget in self.dlc_scrollable_frame.winfo_children():
            widget.destroy()
        loading_label = ctk.CTkLabel(
            self.dlc_scrollable_frame,
            text="正在从服务器获取DLC列表...",
            font=ctk.CTkFont(size=13),
            text_color="#757575"
        )
        loading_label.pack(pady=20)
        
        self.logger.info("正在连接DLC服务器...")
        
        def fetch_thread():
            try:
                # 获取DLC列表
                self.dlc_list = self.dlc_manager.fetch_dlc_list()
                self.after(0, self.display_dlc_list)
                
            except Exception as e:
                def show_error():
                    for widget in self.dlc_scrollable_frame.winfo_children():
                        widget.destroy()
                    error_label = ctk.CTkLabel(
                        self.dlc_scrollable_frame,
                        text=f"加载失败: {str(e)}",
                        font=ctk.CTkFont(size=13),
                        text_color="#D32F2F"
                    )
                    error_label.pack(pady=20)
                self.after(0, show_error)
                self.logger.error(f"无法加载DLC列表 - {str(e)}")
        
        threading.Thread(target=fetch_thread, daemon=True).start()
        
    def display_dlc_list(self):
        """显示DLC列表"""
        # 清空现有列表
        for widget in self.dlc_scrollable_frame.winfo_children():
            widget.destroy()
        self.dlc_vars = []
        
        # 检查已安装的DLC
        installed_dlcs = self.dlc_manager.get_installed_dlcs()
        
        # 创建DLC复选框
        for dlc in self.dlc_list:
            var = tk.BooleanVar(value=False)
            dlc_info = {
                "var": var,
                "key": dlc["key"],
                "name": dlc["name"],
                "url": dlc["url"],
                "size": dlc["size"]
            }
            
            frame = ctk.CTkFrame(self.dlc_scrollable_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2, padx=5)
            
            # 检查是否已安装
            is_installed = dlc["key"] in installed_dlcs
            
            if is_installed:
                # 已安装的DLC显示为禁用状态
                cb = ctk.CTkCheckBox(frame, text="", variable=var, 
                                     state="disabled", width=20)
                cb.pack(side="left")
                label_text = f"{dlc['name']} (已安装)"
                label = ctk.CTkLabel(frame, text=label_text, 
                                    text_color="#9E9E9E")  # 浅灰色
            else:
                cb = ctk.CTkCheckBox(frame, text="", variable=var, width=20,
                                     fg_color="#1976D2", hover_color="#1565C0")
                cb.pack(side="left")
                label_text = f"{dlc['name']} ({dlc['size']})"
                label = ctk.CTkLabel(frame, text=label_text, 
                                    text_color="#212121")  # 深色文字
            
            label.pack(side="left", padx=5)
            
            self.dlc_vars.append(dlc_info)
        
        # 更新状态
        total = len(self.dlc_list)
        installed_count = len(installed_dlcs)
        available_count = total - installed_count
        
        self.logger.info(f"DLC列表加载完成: 共{total}个，已安装{installed_count}个，可下载{available_count}个")
        
        # 启用下载按钮
        self.download_btn.configure(state="normal")
        
    def toggle_select_all(self):
        """全选/取消全选"""
        state = self.select_all_var.get()
        for dlc in self.dlc_vars:
            dlc["var"].set(state)
        
    def inverse_selection(self):
        """反选"""
        for dlc in self.dlc_vars:
            dlc["var"].set(not dlc["var"].get())
        
    def download_dlcs(self):
        """下载并安装选中的DLC"""
        selected = [d for d in self.dlc_vars if d["var"].get()]
        if not selected:
            messagebox.showinfo("提示", "请至少选择一个DLC！")
            return
        
        self.download_btn.configure(state="disabled")
        self.logger.info(f"\n开始下载 {len(selected)} 个DLC...")
        
        def progress_callback(percent, downloaded, total):
            """下载进度回调"""
            self.after(0, lambda: self.progress_label.configure(
                text=f"下载进度: {percent:.1f}%"))
        
        def download_thread():
            success = 0
            failed = 0
            
            # 初始化下载器
            downloader = DLCDownloader(progress_callback)
            
            for idx, dlc in enumerate(selected, 1):
                try:
                    self.logger.info(f"\n{'='*50}")
                    self.logger.info(f"[{idx}/{len(selected)}] {dlc['name']}")
                    
                    # 检查缓存并下载
                    if downloader.is_cached(dlc['key']):
                        self.logger.info("从本地缓存加载...")
                        cache_path = PathUtils.get_dlc_cache_path(dlc['key'])
                    else:
                        self.after(0, lambda: self.progress_label.configure(
                            text=f"下载中 {dlc['name']}..."))
                        cache_path = downloader.download_dlc(dlc['key'], dlc['url'])
                        self.logger.info("下载完成")
                    
                    # 安装
                    self.after(0, lambda: self.progress_label.configure(
                        text=f"安装中 {dlc['name']}..."))
                    
                    self.dlc_installer.install(cache_path, dlc['key'], dlc['name'])
                    self.logger.success("安装成功")
                    success += 1
                    
                except Exception as e:
                    self.logger.error(f"错误: {str(e)}")
                    failed += 1
            
            # 完成
            self.after(0, lambda: self.progress_label.configure(text=""))
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"下载完成！成功: {success}, 失败: {failed}")
            
            # 重新加载DLC列表
            self.after(100, self.load_dlc_list)
            self.after(0, lambda: self.download_btn.configure(state="normal"))
        
        threading.Thread(target=download_thread, daemon=True).start()
        
    def restore_game(self):
        """还原游戏（删除所有通过本工具安装的DLC）"""
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
        
        # 获取操作记录
        operations = self.dlc_installer.operation_log.get_operations()
        
        if not operations:
            messagebox.showinfo("提示", "没有需要还原的操作")
            return
        
        result = messagebox.askyesno("确认", 
            f"即将删除通过本工具安装的 {len(operations)} 个DLC\n是否继续？")
        
        if not result:
            return
        
        self.logger.info("\n开始还原游戏...")
        success, total = self.dlc_installer.restore_game()
        
        self.logger.info(f"\n还原完成！已删除 {success}/{total} 个DLC")
        messagebox.showinfo("完成", f"还原完成！已删除 {success}/{total} 个DLC")
        
        # 重新加载DLC列表
        self.load_dlc_list()
        
    def _check_patch_status(self):
        """检查并更新补丁按钮状态"""
        if not self.patch_manager:
            return
        
        try:
            status = self.patch_manager.check_patch_status()
            
            if status['patched']:
                self.patch_btn.configure(state="disabled")
                self.remove_patch_btn.configure(state="normal")
                self.logger.info("检测到已应用补丁")
            else:
                self.patch_btn.configure(state="normal")
                self.remove_patch_btn.configure(state="disabled")
        except Exception as e:
            # 如果检查失败，默认启用应用补丁按钮
            self.patch_btn.configure(state="normal")
            self.remove_patch_btn.configure(state="disabled")
        
    def apply_patch(self):
        """应用CreamAPI补丁"""
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
        
        # 如果没有加载DLC列表，先加载
        if not self.dlc_list:
            messagebox.showinfo("提示", "正在加载DLC列表，请稍候...")
            self.load_dlc_list()
            # 等待DLC列表加载完成后再应用补丁
            messagebox.showinfo("提示", "请在DLC列表加载完成后，再次点击应用补丁")
            return
        
        result = messagebox.askyesno("确认", 
            "即将应用 CreamAPI 补丁\n"
            "这将修改游戏的 steam_api.dll 文件\n"
            "原始文件会自动备份\n\n"
            "是否继续？")
        
        if not result:
            return
        
        self.patch_btn.configure(state="disabled")
        self.remove_patch_btn.configure(state="disabled")
        
        def patch_thread():
            try:
                success, failed = self.patch_manager.apply_patch(self.dlc_list)
                
                if success > 0 and failed == 0:
                    self.after(0, lambda: messagebox.showinfo("成功", 
                        f"补丁应用成功！\n"
                        f"已处理 {success} 个文件\n\n"
                        f"请重启游戏生效"))
                elif success > 0:
                    self.after(0, lambda: messagebox.showwarning("部分成功", 
                        f"补丁应用部分成功\n"
                        f"成功: {success}, 失败: {failed}\n"
                        f"详情请查看日志"))
                else:
                    self.after(0, lambda: messagebox.showerror("失败", 
                        "补丁应用失败！\n详情请查看日志"))
                
                # 更新按钮状态
                self.after(0, self._check_patch_status)
                
            except Exception as e:
                self.logger.error(f"应用补丁时发生错误: {str(e)}")
                self.after(0, lambda: messagebox.showerror("错误", 
                    f"应用补丁时发生错误:\n{str(e)}"))
                self.after(0, lambda: self.patch_btn.configure(state="normal"))
        
        threading.Thread(target=patch_thread, daemon=True).start()
        
    def remove_patch(self):
        """移除CreamAPI补丁"""
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
        
        result = messagebox.askyesno("确认", 
            "即将移除 CreamAPI 补丁\n"
            "这将还原游戏的原始文件\n\n"
            "是否继续？")
        
        if not result:
            return
        
        self.patch_btn.configure(state="disabled")
        self.remove_patch_btn.configure(state="disabled")
        
        def remove_thread():
            try:
                success, failed = self.patch_manager.remove_patch()
                
                if success > 0 and failed == 0:
                    self.after(0, lambda: messagebox.showinfo("成功", 
                        f"补丁移除成功！\n"
                        f"已还原 {success} 个文件"))
                elif success > 0:
                    self.after(0, lambda: messagebox.showwarning("部分成功", 
                        f"补丁移除部分成功\n"
                        f"成功: {success}, 失败: {failed}\n"
                        f"详情请查看日志"))
                else:
                    self.after(0, lambda: messagebox.showwarning("提示", 
                        "未找到需要还原的补丁文件"))
                
                # 更新按钮状态
                self.after(0, self._check_patch_status)
                
            except Exception as e:
                self.logger.error(f"移除补丁时发生错误: {str(e)}")
                self.after(0, lambda: messagebox.showerror("错误", 
                    f"移除补丁时发生错误:\n{str(e)}"))
                self.after(0, lambda: self.remove_patch_btn.configure(state="normal"))
        
        threading.Thread(target=remove_thread, daemon=True).start()
