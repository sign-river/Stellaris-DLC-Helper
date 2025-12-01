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
from pathlib import Path
from PIL import Image
import requests
from ..config import VERSION
from ..core import DLCManager, DLCDownloader, DLCInstaller, PatchManager
from ..core.updater import AutoUpdater
from .update_dialog import UpdateDialog
from ..utils import Logger, PathUtils, SteamUtils


# 设置外观模式和颜色主题 - 清爽现代风格
ctk.set_appearance_mode("light")  # "dark" 或 "light" 或 "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"


class MainWindowCTk:
    """主窗口类 - CustomTkinter版本"""
    
    def __init__(self, root):
        """
        初始化主窗口
        
        参数:
            root: CustomTkinter根窗口
        """
        self.root = root
        self.root.title(f"Stellaris DLC Helper v{VERSION}")
        self.root.geometry("1000x750")
        
        # 设置窗口图标
        try:
            from ..utils.path_utils import PathUtils
            icon_path = PathUtils.get_resource_path("assets/images/tea_Gray.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            import logging
            logging.warning(f"设置窗口图标失败: {e}")
        
        # 设置清爽现代风格背景
        self.root.configure(fg_color="#F5F7FA")
        
        # 绑定窗口事件以改善重绘问题
        self.root.bind("<Map>", self._on_window_map)
        self.root.bind("<FocusIn>", self._on_window_focus)
        
        # 状态变量
        self.game_path = ""
        self.dlc_list = []
        self.dlc_vars = []  # 存储DLC变量
        self.dlc_checkboxes = []  # 存储复选框对象
        self.is_downloading = False  # 下载状态
        self.download_paused = False  # 暂停状态
        self.current_downloader = None  # 当前下载器实例
        self.current_download_url = None  # 当前下载URL
        # 状态锁，保护多线程访问的状态变量
        self._state_lock = threading.Lock()
        # 一键解锁流程状态：
        # - _one_click_flow:  标记当前操作由“一键解锁”触发，用于在流程结束时统一展示成功弹窗（避免重复弹窗）
        # - _one_click_patch_applied: 标记在本次一键流程里是否实际应用了补丁（用于决定最终弹窗内容）
        self._one_click_flow = False
        self._one_click_patch_applied = False
        
        # 核心组件
        self.dlc_manager = None
        self.dlc_downloader = None
        self.dlc_installer = None
        self.patch_manager = None
        self.logger = Logger(root=self.root)
        
        # 初始化统一错误处理器
        from ..utils import set_gui_logger
        set_gui_logger(self.logger)
        
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
        
        # 自动检测游戏路径并加载DLC列表
        self.root.after(100, self.auto_detect_and_load)

        # 检查是否刚刚完成更新
        self.root.after(500, self._check_recent_update)

        # 延迟检查更新（避免启动时卡顿）
        self.root.after(2000, self._auto_check_update)
        
        # 将 GUI 日志处理器附加到根日志记录器，以便标准日志转发到 GUI
        try:
            import logging
            handler = self.logger.get_logging_handler()
            logging.getLogger().addHandler(handler)
        except Exception:
            pass

    def _open_error_docs(self, event=None):
        """在用户默认浏览器中打开在线错误/调试文档。

        此函数由标题栏的 “遇到报错？” 链接调用，不应阻塞 UI 线程。
        """
        try:
            import webbrowser
            webbrowser.open("https://www.kdocs.cn/l/cdVvg4OgHMzj", new=2)
        except Exception as e:
            # 如果无法打开浏览器，记录异常并忽略（避免 UI 崩溃）
            self.logger.log_exception("无法打开帮助文档链接", e)
        
    def _create_header(self):
        """创建标题区域"""
        header_frame = ctk.CTkFrame(self.root, corner_radius=0, height=130, fg_color=["#3a7ebf", "#1f538d"])
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)
        
        # 左上角图标
        try:
            icon_path = PathUtils.get_resource_path("assets/images/tea_Gray.png")
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
                # 调整图标大小
                icon_image = icon_image.resize((80, 80), Image.Resampling.LANCZOS)
                icon_photo = ctk.CTkImage(light_image=icon_image, dark_image=icon_image, size=(80, 80))
                icon_label = ctk.CTkLabel(
                    header_frame,
                    image=icon_photo,
                    text=""
                )
                icon_label.place(x=40, y=25)  # 固定在左上角
                # 保存引用避免被垃圾回收
                self._header_icon = icon_label
        except Exception as e:
            import logging
            logging.warning(f"加载左上角图标失败: {e}")
        
        # 主标题 - 放大字号，纯白色
        title_label = ctk.CTkLabel(
            header_frame,
            text="S T E L L A R I S   D L C   H E L P E R",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(pady=(18, 8))
        
        # 副标题 - 纯白色
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="群星 DLC 一键解锁工具  |  该程序为免费开源项目，如付费获得请立即要求商家退款",
            font=ctk.CTkFont(size=14),
            text_color="#FFFFFF"
        )
        subtitle_label.pack(pady=(0, 4))

        # 信息行容器：中间居中显示作者/QQ群/图标，右侧显示“遇到报错？”帮助链接
        info_row_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_row_frame.pack(fill="x", pady=(0, 6))

        # 使用 grid 布局对 info_row_frame 做 5 列布局（索引0..4）:
        # - 0,1: 左侧占位（0 为可扩展占位）
        # - 2: 中间（文本组：作者, QQ）
        # - 3: 中间（图标组：GitHub, B站）
        # - 4: 最右侧（遇到报错？ 链接）
        # 只让左侧第0列与右侧第4列可拉伸，保证第2列（中间文本组）始终处于水平居中
        info_row_frame.grid_columnconfigure(0, weight=1)
        info_row_frame.grid_columnconfigure(1, weight=0)
        info_row_frame.grid_columnconfigure(2, weight=0)
        info_row_frame.grid_columnconfigure(3, weight=0)
        info_row_frame.grid_columnconfigure(4, weight=1)

        # 中间文本容器放在第3列（index=2）
        center_container = ctk.CTkFrame(info_row_frame, fg_color="transparent")
        center_container.grid(row=0, column=2)
        # 确保 center_container 处于列的水平中间，不拉伸

        # 中部内层容器：用来组合作者/QQ群/图标并使其整体居中
        center_inner = ctk.CTkFrame(center_container, fg_color="transparent")
        center_inner.pack(anchor="center")

        author_label = ctk.CTkLabel(
            center_inner,
            text="by 唏嘘南溪",
            font=ctk.CTkFont(size=12),
            text_color="#FFFFFF"
        )
        author_label.pack(side="left", padx=(0, 20))
        
        # QQ群信息 - 分为文字和可复制的号码
        qq_text_label = ctk.CTkLabel(
            center_inner,
            text="QQ群: ",
            font=ctk.CTkFont(size=12),
            text_color="#FFFFFF"
        )
        qq_text_label.pack(side="left")
        
        # QQ群号 - 使用Entry实现可选中复制
        self.qq_entry = ctk.CTkEntry(
            center_inner,
            width=100,
            height=24,
            fg_color="transparent",
            border_width=0,
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=12)
        )
        self.qq_entry.insert(0, "1051774780")
        self.qq_entry.configure(state="readonly")  # 只读但可选中
        self.qq_entry.pack(side="left", padx=(0, 20))
        
        # 绑定单击事件
        self.qq_entry.bind("<Button-1>", lambda e: self._copy_qq_to_clipboard())
        
        # 图标容器放在第4列（index=3） - 提前创建以便后续 icon 元素使用
        icons_container = ctk.CTkFrame(info_row_frame, fg_color="transparent")
        icons_container.grid(row=0, column=3)

        # GitHub图标按钮
        try:
            github_icon_path = PathUtils.get_resource_path("assets/images/github.png")
            if os.path.exists(github_icon_path):
                github_image = Image.open(github_icon_path)
                github_photo = ctk.CTkImage(light_image=github_image, dark_image=github_image, size=(20, 20))
                github_btn = ctk.CTkButton(
                    icons_container,
                    image=github_photo,
                    text="",
                    fg_color="transparent",
                    hover_color="#2563A8",
                    width=28,
                    height=28,
                    corner_radius=4,
                    command=self._open_github
                )
                github_btn.pack(side="left", padx=(0, 5))
            else:
                # 降级为文字按钮
                github_btn = ctk.CTkButton(
                    icons_container,
                    text="⚙ GitHub",
                    font=ctk.CTkFont(size=11),
                    text_color="#FFFFFF",
                    fg_color="transparent",
                    hover_color="#2563A8",
                    width=80,
                    height=24,
                    corner_radius=4,
                    command=self._open_github
                )
                github_btn.pack(side="left", padx=(0, 5))
        except Exception as e:
            import logging
            logging.warning(f"加载GitHub图标失败: {e}")
            # 降级为文字按钮
            github_btn = ctk.CTkButton(
                icons_container,
                text="⚙ GitHub",
                font=ctk.CTkFont(size=11),
                text_color="#FFFFFF",
                fg_color="transparent",
                hover_color="#2563A8",
                width=80,
                height=24,
                corner_radius=4,
                command=self._open_github
            )
            github_btn.pack(side="left", padx=(0, 5))
        
        # (icons_container already created above)

        # 添加“遇到报错？”链接在第5列（index=4），并右对齐
        error_link_label = ctk.CTkLabel(
            info_row_frame,
            text="遇到报错？",
            font=ctk.CTkFont(size=12, underline=True),
            text_color="#FFFFFF",
            cursor="hand2"
        )
        error_link_label.bind("<Button-1>", lambda e: self._open_error_docs())
        error_link_label.grid(row=0, column=4, sticky="e", padx=(0, 20), pady=(0, 6))

        # B站图标按钮
        try:
            bilibili_icon_path = PathUtils.get_resource_path("assets/images/bilibili.png")
            if os.path.exists(bilibili_icon_path):
                bilibili_image = Image.open(bilibili_icon_path)
                bilibili_photo = ctk.CTkImage(light_image=bilibili_image, dark_image=bilibili_image, size=(20, 20))
                bilibili_btn = ctk.CTkButton(
                    icons_container,
                    image=bilibili_photo,
                    text="",
                    fg_color="transparent",
                    hover_color="#2563A8",
                    width=28,
                    height=28,
                    corner_radius=4,
                    command=self._open_bilibili
                )
                bilibili_btn.pack(side="left")
        except Exception as e:
            import logging
            logging.warning(f"加载B站图标失败: {e}")
    
    def _open_github(self):
        """打开 GitHub 链接"""
        import webbrowser
        webbrowser.open("https://github.com/sign-river/Stellaris-DLC-Helper")
    
    def _open_bilibili(self):
        """打开 B站视频链接"""
        import webbrowser
        webbrowser.open("https://www.bilibili.com/video/BV12pbrzSEQY/?spm_id_from=333.1387.homepage.video_card.click&vd_source=19dcf32d8641182f1f159b50887e0cf8")
    
    def _copy_qq_to_clipboard(self):
        """复制QQ群号到剪贴板"""
        qq_number = "1051774780"
        self.root.clipboard_clear()
        self.root.clipboard_append(qq_number)
        self.root.update()  # 确保剪贴板更新
        self.logger.info(f"已复制QQ群号: {qq_number}")
        messagebox.showinfo("提示", f"QQ群号已复制: {qq_number}")
    
    def _rgba_color(self, hex_color, opacity):
        """
        将十六进制颜色转换为带透明度的格式
        CustomTkinter 使用 hex 颜色，这里通过调整亮度模拟透明度效果
        
        参数:
            hex_color: 十六进制颜色 (如 "#FFFFFF")
            opacity: 不透明度 0.0-1.0
            
        返回:
            调整后的颜色字符串
        """
        # 对于白色文字在深色背景上，通过降低亮度模拟透明度
        # 简化处理：直接返回对应灰度的白色
        if opacity >= 1.0:
            return "#FFFFFF"
        elif opacity >= 0.85:
            return "#D9D9D9"  # 约 85% 白色
        elif opacity >= 0.6:
            return "#999999"  # 约 60% 白色
        else:
            return "#808080"  # 50% 灰色
        
    def _create_content_area(self):
        """创建主内容区域"""
        # 主容器
        content_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content_frame.grid_rowconfigure(1, weight=3)  # DLC列表 - 降低权重
        content_frame.grid_rowconfigure(2, weight=2)  # 操作日志 - 提高权重
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
        dlc_frame.grid_rowconfigure(1, weight=1)
        dlc_frame.grid_columnconfigure(0, weight=1)
        
        # 标题行（9列布局：DLC标题 | 下载信息 | 进度条 | 速度 | 下载源 | 全选按钮）
        header_frame = ctk.CTkFrame(dlc_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        
        # 配置列权重：第0列固定，第1-2列下载信息，第3-6列进度条，第7列固定
        header_frame.grid_columnconfigure(0, weight=0, minsize=100)  # DLC列表标题
        header_frame.grid_columnconfigure(1, weight=0, minsize=10)   # 间隔
        header_frame.grid_columnconfigure(2, weight=0, minsize=150)  # 下载信息
        header_frame.grid_columnconfigure(3, weight=1)               # 进度条（弹性）
        header_frame.grid_columnconfigure(4, weight=0, minsize=100)  # 速度显示
        header_frame.grid_columnconfigure(5, weight=0, minsize=10)   # 间隔
        header_frame.grid_columnconfigure(6, weight=0, minsize=120)  # 下载源显示
        header_frame.grid_columnconfigure(7, weight=0, minsize=10)   # 间隔
        header_frame.grid_columnconfigure(8, weight=0, minsize=80)   # 全选按钮
        
        # 第0列：DLC列表标题
        label = ctk.CTkLabel(
            header_frame,
            text="📦 DLC列表",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1976D2"
        )
        label.grid(row=0, column=0, sticky="w")
        
        # 第2列：正在下载的DLC名称（默认隐藏）
        self.downloading_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#757575",
            anchor="w"
        )
        self.downloading_label.grid(row=0, column=2, sticky="ew", padx=(10, 0))
        self.downloading_label.grid_remove()  # 初始隐藏
        
        # 第3列：进度条（默认隐藏）
        self.progress_bar = ctk.CTkProgressBar(
            header_frame,
            height=20,
            corner_radius=10,
            progress_color="#1976D2",
            fg_color="#E3F2FD"
        )
        self.progress_bar.grid(row=0, column=3, sticky="ew", padx=(10, 10))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()  # 初始隐藏
        
        # 第4列：下载速度（默认隐藏）
        self.speed_label = ctk.CTkLabel(
            header_frame,
            text="0.00 MB/s",
            font=ctk.CTkFont(size=11),
            text_color="#1976D2",
            width=80
        )
        self.speed_label.grid(row=0, column=4, sticky="e")
        self.speed_label.grid_remove()  # 初始隐藏
        
        # 第6列：当前下载源（默认隐藏）
        self.source_label = ctk.CTkLabel(
            header_frame,
            text="下载源: 未知",
            font=ctk.CTkFont(size=11),
            text_color="#1976D2",
            width=100
        )
        self.source_label.grid(row=0, column=6, sticky="w")
        self.source_label.grid_remove()  # 初始隐藏

        # 第6.1列：重测/暂停状态标签（默认隐藏）
        self.retest_status_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#1976D2",
            width=160,
            anchor="w"
        )
        self.retest_status_label.grid(row=0, column=7, sticky="w")
        self.retest_status_label.grid_remove()
        
        # 第5列：服务器状态文本（默认隐藏）
        self.server_status_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FF5722",
            anchor="center"
        )
        self.server_status_label.grid(row=0, column=3, sticky="ew", padx=(10, 10))
        self.server_status_label.grid_remove()  # 初始隐藏
        
        # 第8列：全选按钮
        self.select_all_btn = ctk.CTkButton(
            header_frame,
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
        self.select_all_btn.grid(row=0, column=8, sticky="e")
        
        # 滚动框架（用于显示DLC列表）
        self.dlc_scrollable_frame = ctk.CTkScrollableFrame(
            dlc_frame,
            corner_radius=8,
            fg_color="#FAFAFA",
            height=220  # 设置固定高度，降低DLC区域高度
        )
        self.dlc_scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
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
        
        # 左侧按钮组(危险/撤销区)
        left_btn_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_btn_container.grid(row=0, column=0, sticky="w", padx=(15, 10), pady=(12, 12))
        
        # 卸载DLC按钮（次要 - 浅蓝）
        restore_btn = ctk.CTkButton(
            left_btn_container,
            text="🔄 卸载DLC",
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
        self.remove_patch_btn.pack(side="left", padx=(0, 10))
        
        # 清理缓存按钮（次要 - 浅蓝）
        self.clear_cache_btn = ctk.CTkButton(
            left_btn_container,
            text="🗑️ 清理缓存",
            command=self._clear_cache,
            width=130,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        self.clear_cache_btn.pack(side="left")
        
        # 右侧按钮组(前进/执行区)
        right_btn_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_btn_container.grid(row=0, column=1, sticky="e", padx=(10, 15), pady=(12, 12))
        
        # 更新按钮
        self.update_btn = ctk.CTkButton(
            right_btn_container,
            text="🔄 检查更新",
            command=self.check_update,
            width=130,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        self.update_btn.pack(side="left", padx=(0, 10))
        
        # 执行按钮（合并补丁 & 下载功能）
        self.execute_btn = ctk.CTkButton(
            right_btn_container,
            text="🔓 一键解锁",
            command=self.toggle_execute,
            state="disabled",
            width=280,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#1976D2",
            hover_color="#1565C0",
            text_color="#FFFFFF"
        )
        self.execute_btn.pack(side="left", padx=(0, 10))
        
        # 下载安装按钮的行为已合并到 execute_btn 中，此按钮移除
        
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
        
        # 标题栏（包含标题和复制按钮）
        log_title_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_title_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        log_title_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        label = ctk.CTkLabel(
            log_title_frame,
            text="📋 操作日志",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1976D2"  # 主色调蓝色
        )
        label.pack(side="left")
        
        # 设置按钮（最先添加，这样pack side="right"时会在最右边）
        try:
            set_icon_path = PathUtils.get_resource_path("assets/images/set.png")
            if os.path.exists(set_icon_path):
                set_image = Image.open(set_icon_path)
                set_photo = ctk.CTkImage(light_image=set_image, dark_image=set_image, size=(20, 20))
                settings_btn = ctk.CTkButton(
                    log_title_frame,
                    image=set_photo,
                    text="",
                    fg_color="#42A5F5",
                    hover_color="#1E88E5",
                    width=28,
                    height=28,
                    corner_radius=6,
                    command=self._open_settings
                )
                settings_btn.pack(side="right")
            else:
                # 降级为文字按钮
                settings_btn = ctk.CTkButton(
                    log_title_frame,
                    text="⚙️",
                    font=ctk.CTkFont(size=14),
                    text_color="#FFFFFF",
                    fg_color="#42A5F5",
                    hover_color="#1E88E5",
                    width=28,
                    height=28,
                    corner_radius=6,
                    command=self._open_settings
                )
                settings_btn.pack(side="right")
        except Exception as e:
            import logging
            logging.warning(f"加载设置图标失败: {e}")
        
        # 导出日志按钮
        export_log_btn = ctk.CTkButton(
            log_title_frame,
            text="💾 导出日志",
            command=self._export_log,
            width=100,
            height=28,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        export_log_btn.pack(side="right", padx=(0, 10))
        
        # 复制日志按钮
        copy_log_btn = ctk.CTkButton(
            log_title_frame,
            text="📋 复制日志",
            command=self._copy_log,
            width=100,
            height=28,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            fg_color="#42A5F5",
            hover_color="#1E88E5",
            text_color="#FFFFFF"
        )
        copy_log_btn.pack(side="right", padx=(0, 10))
        
        # 日志文本框
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=150,  # 从60提高到180，增加日志显示空间
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
        self.logger.set_widget(self.log_text, self.root)

    # --------------------- UI helpers: re-test spinner ---------------------
    def _show_friendly_error(self, error_type: str, exception: Exception, context: str = ""):
        """
        显示友好的错误提示
        
        参数:
            error_type: 错误类型 ('network', 'disk', 'permission', 'file', 'unknown')
            exception: 异常对象
            context: 错误上下文描述
        """
        error_messages = {
            'network': {
                'title': '网络连接失败',
                'message': '无法连接到服务器\n\n可能的原因：\n• 网络连接不稳定\n• 服务器暂时不可用\n• 防火墙阻止了连接\n\n建议：\n• 检查网络连接\n• 稍后重试\n• 尝试切换下载源'
            },
            'disk': {
                'title': '磁盘空间不足',
                'message': '磁盘空间不足，无法完成操作\n\n建议：\n• 清理磁盘空间\n• 更换安装目录\n• 使用「清理缓存」功能释放空间'
            },
            'permission': {
                'title': '权限不足',
                'message': '没有足够的权限执行此操作\n\n建议：\n• 以管理员身份运行程序\n• 检查文件/文件夹权限\n• 确保文件未被其他程序占用'
            },
            'file': {
                'title': '文件操作失败',
                'message': '文件操作失败\n\n可能的原因：\n• 文件被其他程序占用\n• 文件损坏\n• 路径包含特殊字符\n\n建议：\n• 关闭相关程序后重试\n• 检查文件路径'
            },
            'unknown': {
                'title': '操作失败',
                'message': '操作执行失败'
            }
        }
        
        error_info = error_messages.get(error_type, error_messages['unknown'])
        
        # 构建完整错误消息
        full_message = error_info['message']
        if context:
            full_message = f"{context}\n\n{full_message}"
        
        # 添加详细错误信息（可选）
        if str(exception):
            full_message += f"\n\n详细信息：\n{str(exception)}"
        
        messagebox.showerror(error_info['title'], full_message)
    
    def _start_retest_ui(self, text: str = "正在测速..."):
        """开始显示测速/暂停状态，并启动文本动画（spinner）。"""
        try:
            self.retest_status_text = text
            self.retest_spinner_running = True
            self.retest_spinner_idx = 0
            self.root.after(0, lambda: self.retest_status_label.grid())
            self._retest_spinner_step()
        except Exception:
            pass

    def _retest_spinner_step(self):
        if not getattr(self, 'retest_spinner_running', False):
            return
        try:
            chars = ['|', '/', '-', '\\']
            idx = getattr(self, 'retest_spinner_idx', 0) % len(chars)
            ch = chars[idx]
            txt = f"{ch} {getattr(self, 'retest_status_text', '')}"
            self.retest_status_label.configure(text=txt)
            self.retest_spinner_idx = idx + 1
            self._retest_spinner_after_id = self.root.after(250, self._retest_spinner_step)
        except Exception:
            pass

    def _stop_retest_ui(self):
        """停止显示测速状态并清理 spinner 定时任务。"""
        try:
            self.retest_spinner_running = False
            if hasattr(self, '_retest_spinner_after_id'):
                try:
                    self.root.after_cancel(self._retest_spinner_after_id)
                except Exception:
                    pass
            self.root.after(0, lambda: self.retest_status_label.grid_remove())
        except Exception:
            pass
        
    # ========== 以下是业务逻辑方法，将逐步从旧版本迁移 ==========
    
    def auto_detect_and_load(self):
        """自动检测游戏路径并加载DLC列表"""
        self.logger.info("正在自动检测 Stellaris 游戏路径...")
        
        # 检查是否有未完成的下载需要恢复
        self._check_pending_download_state()
        
        def detect_and_load_thread():
            try:
                # 1. 自动检测游戏路径
                game_path = SteamUtils.auto_detect_stellaris()
                
                if game_path:
                    # 在主线程中更新路径
                    self.root.after(0, lambda: self._set_game_path(game_path))
                    self.root.after(0, lambda: self.logger.success(f"已找到游戏: {game_path}"))
                    
                    # 2. 自动加载DLC列表
                    self.root.after(100, lambda: self._auto_load_dlc_list())
                else:
                    self.root.after(0, lambda: self.logger.warning(
                        "未能自动检测到游戏路径\n"
                        "请点击「浏览」按钮手动选择游戏目录"
                    ))
            except Exception as e:
                # 在主线程中记录异常并写入错误日志
                self.root.after(0, lambda e=e: self.logger.log_exception("自动检测失败", e))
        
        threading.Thread(target=detect_and_load_thread, daemon=True).start()
    
    def _check_pending_download_state(self):
        """检查是否有未完成的下载需要恢复"""
        try:
            import json
            from pathlib import Path
            from ..utils import PathUtils

            state_file = Path(PathUtils.get_cache_dir()) / "download_state.json"
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                if state.get("download_paused", False):
                    self.logger.info("检测到未完成的下载，将按钮设置为暂停状态")
                    # 设置下载暂停状态
                    self.download_paused = True
                    # 更新按钮文本
                    self.execute_btn.configure(text="▶️ 继续下载")
                    # 删除状态文件
                    state_file.unlink()
                    self.logger.info("下载状态已恢复")
        except Exception as e:
            self.logger.warning(f"检查下载状态失败: {e}")
    
    def _clear_download_state(self):
        """清除下载状态文件"""
        try:
            from pathlib import Path
            from ..utils import PathUtils

            state_file = Path(PathUtils.get_cache_dir()) / "download_state.json"
            if state_file.exists():
                state_file.unlink()
                self.logger.debug("下载状态文件已清除")
        except Exception as e:
            self.logger.warning(f"清除下载状态文件失败: {e}")
    
    def _auto_load_dlc_list(self):
        """自动加载DLC列表（内部方法，不弹窗提示）"""
        if not self.game_path:
            return
        
        self.logger.info("正在从服务器获取DLC列表...")
        
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
        
        def fetch_thread():
            try:
                # 获取DLC列表
                self.dlc_list = self.dlc_manager.fetch_dlc_list()
                self.root.after(0, self.display_dlc_list)
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
                self.root.after(0, show_error)
                # 记录并写入异常日志
                self.logger.log_exception("无法加载DLC列表", e)
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def auto_detect_path(self):
        """自动检测游戏路径"""
        self.logger.info("正在自动检测 Stellaris 游戏路径...")
        
        # 在后台线程中执行检测
        def detect_thread():
            try:
                game_path = SteamUtils.auto_detect_stellaris()
                
                if game_path:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self._set_game_path(game_path))
                    self.root.after(0, lambda: self.logger.success(f"自动检测成功: {game_path}"))
                else:
                    self.root.after(0, lambda: self.logger.warning(
                        "未能自动检测到 Stellaris 游戏路径\n"
                        "请确保:\n"
                        "1. 已通过 Steam 安装 Stellaris\n"
                        "2. Steam 已正确安装\n"
                        "或者点击「浏览」按钮手动选择游戏目录"
                    ))
                    self.root.after(0, lambda: messagebox.showinfo(
                        "未找到游戏",
                        "未能自动检测到 Stellaris 游戏路径\n\n"
                        "请点击「浏览」按钮手动选择游戏目录"
                    ))
            except Exception as e:
                # 在主线程中记录异常并写入错误日志
                self.root.after(0, lambda e=e: self.logger.log_exception("自动检测失败", e))
                self.root.after(0, lambda: messagebox.showerror(
                    "检测失败",
                    f"自动检测时发生错误:\n{str(e)}\n\n请手动选择游戏目录"
                ))
        
        threading.Thread(target=detect_thread, daemon=True).start()
    
    def _set_game_path(self, path: str):
        """设置游戏路径（内部方法）"""
        self.game_path = path
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path)
        
        # 初始化核心组件
        self.dlc_manager = DLCManager(path)
        self.dlc_installer = DLCInstaller(path)
        self.patch_manager = PatchManager(path, self.logger)
        
        # 检查补丁状态
        self._check_patch_status()
    
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
            
            self._set_game_path(path)
            self.logger.info(f"已选择游戏路径: {path}")
            
            # 自动加载DLC列表
            self.root.after(100, self._auto_load_dlc_list)
        
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
                self.root.after(0, self.display_dlc_list)
                
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
                self.root.after(0, show_error)
                # 在主线程中记录异常并写入错误日志
                self.root.after(0, lambda e=e: self.logger.log_exception("无法加载DLC列表", e))
        
        threading.Thread(target=fetch_thread, daemon=True).start()
        
    def display_dlc_list(self):
        """显示DLC列表 - 两列布局"""
        # 清空现有列表
        for widget in self.dlc_scrollable_frame.winfo_children():
            widget.destroy()
        self.dlc_vars = []
        
        # 检查已安装的DLC
        installed_dlcs = self.dlc_manager.get_installed_dlcs()
        
        # 创建DLC复选框 - 两列布局
        row_frame = None
        for idx, dlc in enumerate(self.dlc_list):
            # 检查是否已安装
            is_installed = dlc["key"] in installed_dlcs
            
            # 默认选中未安装的DLC
            var = tk.BooleanVar(value=not is_installed)
            
            dlc_info = {
                "var": var,
                "key": dlc["key"],
                "name": dlc["name"],
                "url": dlc["url"],
                "source": dlc.get("source", "unknown"),
                "urls": dlc.get("urls", []),
                "size": dlc["size"],
                "installed": is_installed
            }
            
            # 每三个创建一个新行
            if idx % 3 == 0:
                row_frame = ctk.CTkFrame(self.dlc_scrollable_frame, fg_color="transparent", height=22)
                row_frame.pack(fill="x", pady=0, padx=5)
                row_frame.grid_columnconfigure(0, weight=1, uniform="dlc_col")
                row_frame.grid_columnconfigure(1, weight=1, uniform="dlc_col")
                row_frame.grid_columnconfigure(2, weight=1, uniform="dlc_col")
            
            # 确定列位置
            col = idx % 3
            
            # 创建DLC项容器
            item_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            item_frame.grid(row=0, column=col, sticky="w", padx=(0, 8) if col < 2 else 0)
            
            if is_installed:
                # 已安装的DLC显示为禁用状态
                cb = ctk.CTkCheckBox(item_frame, text="", variable=var, 
                                     state="disabled", width=16, height=16,
                                     checkbox_width=16, checkbox_height=16)
                cb.pack(side="left", pady=2)
                label_text = f"{dlc['name']} (已安装)"
                label = ctk.CTkLabel(item_frame, text=label_text,
                                    font=ctk.CTkFont(size=11),
                                    text_color="#9E9E9E",
                                    height=20)  # 浅灰色
            else:
                cb = ctk.CTkCheckBox(item_frame, text="", variable=var, width=16, height=16,
                                     checkbox_width=16, checkbox_height=16,
                                     fg_color="#1976D2", hover_color="#1565C0")
                cb.pack(side="left", pady=2)
                label_text = f"{dlc['name']} ({dlc['size']})"
                label = ctk.CTkLabel(item_frame, text=label_text,
                                    font=ctk.CTkFont(size=11),
                                    text_color="#212121",
                                    height=20)  # 深色文字
            
            label.pack(side="left", padx=5, pady=2)
            # 移除每个 DLC 后面的 "源:" 标签（已由顶部状态显示），并将点击 DLC 名称绑定为输出 URL 映射到操作日志
            # 添加查看 URL 映射的操作（不弹窗，只写入操作日志）
            def _show_urls(key=dlc['key'], d=dlc):
                try:
                    urls = d.get('url_map', {})
                    if not urls:
                        message = "未找到 URL 映射信息（可能是旧版索引或未启用其它源）"
                    else:
                        message_lines = []
                        for src, u in urls.items():
                            message_lines.append(f"{src}: {u if u else 'N/A'}")
                        message = "\n".join(message_lines)
                    checksum = d.get('checksum') or d.get('sha256') or d.get('hash')
                    if checksum:
                        message = f"校验哈希: {checksum}\n\n" + message
                    # 记录到操作日志（不弹窗）
                    self.logger.info(f"DLC {d.get('name')} 的 URL 映射:\n{message}")
                except Exception as e:
                    self.logger.log_exception("显示 URL 映射失败", e)

            # 将 DLC 名称绑定点击事件，输出 URL 映射到操作日志
            try:
                # 事件处理器：写入日志
                def _label_click(event=None, key=dlc['key'], d=dlc):
                    _show_urls(key=key, d=d)
                label.bind("<Button-1>", _label_click)
            except Exception:
                pass
            
            self.dlc_vars.append(dlc_info)
        
        # 更新状态
        total = len(self.dlc_list)
        installed_count = len(installed_dlcs)
        available_count = total - installed_count
        
        self.logger.info(f"DLC列表加载完成: 共{total}个，已安装{installed_count}个，可下载{available_count}个")
        
        # 启用执行按钮（执行补丁/下载）
        self.execute_btn.configure(state="normal")

        # 更新补丁按钮状态显示（自动检测）
        self._check_patch_status()
        
        # 如果有未安装的DLC被默认选中，更新全选按钮文本
        if available_count > 0:
            self.select_all_btn.configure(text="取消全选")
        else:
            self.select_all_btn.configure(text="全选")
        
    def toggle_select_all(self):
        """全选/取消全选（智能切换）"""
        # 检查是否有可选的DLC（未安装的）
        available_dlcs = [dlc for dlc in self.dlc_vars if not dlc.get("installed", False)]
        
        # 如果没有可选项，直接返回
        if not available_dlcs:
            return
        
        # 检查当前是否有选中项
        has_selected = any(dlc["var"].get() for dlc in available_dlcs)
        
        # 如果有选中项，则取消全选；否则全选
        new_state = not has_selected
        
        for dlc in available_dlcs:
            dlc["var"].set(new_state)
        
        # 更新按钮文本
        self.select_all_btn.configure(text="取消全选" if new_state else "全选")
    
    def toggle_download(self):
        """切换下载状态：开始/暂停/继续"""
        if not self.is_downloading:
            # 开始下载
            self.start_download()
        elif self.download_paused:
            # 继续下载
            self.resume_download()
        else:
            # 暂停下载
            self.pause_download()

    def toggle_execute(self):
        """切换执行状态：开始/暂停/继续

        当未下载时，先检查是否需要应用补丁（若未应用），然后开始下载。
        当正在下载时，则切换为暂停/继续行为。
        """
        if not self.is_downloading:
            # 开始执行（补丁 + 下载）
            self.start_execute()
        elif self.download_paused:
            # 继续下载
            self.resume_download()
        else:
            # 暂停下载
            self.pause_download()

    def start_execute(self):
        """开始执行：先应用补丁（如有需要），再下载选中的DLC"""
        # 检查是否已经在执行中，防止重复点击
        if self.is_downloading:
            self.logger.warning("操作已在进行中，请等待完成后再操作")
            return
            
        # 确保游戏路径已设置
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return

        # 确保 DLC 列表已加载
        if not self.dlc_list:
            messagebox.showinfo("提示", "正在加载DLC列表，请稍候...")
            self.load_dlc_list()
            messagebox.showinfo("提示", "请在DLC列表加载完成后，再次点击执行按钮")
            return

        # 不要过早要求选择：如果补丁尚未应用，应允许只执行补丁操作
        # 当未选择任何 DLC 时（用户意图仅应用补丁）
        selected = [d for d in self.dlc_vars if d["var"].get()]

        # 检查补丁状态
        try:
            patched_status = self.patch_manager.check_patch_status()
        except Exception:
            patched_status = {'patched': False}

        # 如果未打补丁则决定自动应用补丁（不弹确认对话）
        should_patch = not patched_status.get('patched', False)

        # 确定被选中且实际需要下载的 DLC（即尚未安装）
        # 过滤掉已安装的 DLC，只尝试下载缺失项
        selected_to_download = [d for d in selected if not d.get('installed', False)]

        # 如果既不应用补丁且未选择任何 DLC，则无需执行任何操作
        if not should_patch and not selected:
            # 如果补丁已应用且所有DLC已安装，告诉用户已全部解锁
            all_installed = all(d.get("installed", False) for d in self.dlc_vars) if self.dlc_vars else False
            if patched_status.get('patched', False) and not selected_to_download and all_installed:
                messagebox.showinfo("提示", "已全部解锁！所有 DLC 均已安装")
            else:
                messagebox.showinfo("提示", "请至少选择一个DLC！")
            return

        def execute_thread():
            # 如果未打补丁，询问用户是否应用补丁
            try:
                # 使用标识指示该执行由“一键解锁”触发，
                # 以便在流程结束时统一显示成功弹窗（和避免重复通知）
                self._one_click_flow = True
                self._one_click_patch_applied = False
                if should_patch:
                    # 在打补丁时禁用执行按钮
                    self.root.after(0, lambda: self.execute_btn.configure(state="disabled"))
                    success, failed = self.patch_manager.apply_patch(self.dlc_list)
                    if success > 0:
                        # 记录补丁是否在本次一键解锁流程内被成功应用（用于最终统一弹窗的判断）
                        self._one_click_patch_applied = True
                    # 组合通知并在未选择 DLC 时避免重复消息
                    if success > 0 and failed == 0:
                        # 如果处于一键流程，延迟成功通知并在统一成功模态中展示
                        if not self._one_click_flow:
                            msg = f"补丁应用成功！已处理 {success} 个文件"
                            if not selected:
                                msg += "\n\n已应用补丁，没有选中 DLC，下载流程已跳过"
                            self.root.after(0, lambda m=msg: messagebox.showinfo("成功", m))
                    elif success > 0:
                        # 部分成功：即使在一键流程中也显示警告
                        msg = f"补丁应用部分成功，成功: {success}, 失败: {failed}"
                        if not selected:
                            msg += "\n\n已应用补丁，没有选中 DLC，下载流程已跳过"
                        self.root.after(0, lambda m=msg: messagebox.showwarning("部分成功", m))
                    else:
                        self.root.after(0, lambda: messagebox.showwarning("提示", "补丁应用失败或无变更，请查看日志"))
                    # 重新检查补丁状态
                    self.root.after(0, self._check_patch_status)
                # 在打补丁后或已打补丁情况下开始下载
                if selected_to_download:
                    # 使用一键标志以便在下载完成时显示统一成功弹窗
                    self._one_click_flow = True
                    self.root.after(0, lambda: self.start_download())
                else:
                    # 如果未选择 DLC：
                    # 如果我们刚刚应用了补丁且成功，则显示统一成功模态
                    if self._one_click_patch_applied:
                        self.root.after(0, lambda: messagebox.showinfo("成功", "解锁成功！"))
                        # 重置标志
                        self._one_click_patch_applied = False
                        self._one_click_flow = False
            finally:
                # 确保执行按钮启用
                self.root.after(0, lambda: self.execute_btn.configure(state="normal"))

        threading.Thread(target=execute_thread, daemon=True).start()
    
    def start_download(self):
        """开始下载"""
        # 检查是否已经在下载中，防止重复点击
        if self.is_downloading:
            self.logger.warning("下载已在进行中，请等待完成后再操作")
            return
            
        selected = [d for d in self.dlc_vars if d["var"].get()]
        if not selected:
            messagebox.showinfo("提示", "请至少选择一个DLC！")
            return
        
        # 设置下载状态
        self.is_downloading = True
        self.execute_btn.configure(text="⏸️ 暂停下载", state="normal")
        
        # 在后台线程中进行测速选择最佳源
        def speed_test_thread():
            try:
                best_source, test_url = self.dlc_manager.source_manager.get_best_download_source(
                    silent=False,  # 允许显示详细信息到控制台，但GUI会通过log_callback显示
                    log_callback=self.logger.info
                )
                self.best_download_source = best_source
                # 选择结果已在get_best_download_source中通过log_callback输出，这里不再重复
            except Exception as e:
                self.logger.warning(f"测速失败，使用默认源: {e}")
                self.best_download_source = "domestic_cloud"
            
            # 测速完成后，在主线程中继续下载流程
            self.root.after(0, lambda: self._continue_download_after_speed_test(selected))
        
        # 启动测速线程
        import threading
        threading.Thread(target=speed_test_thread, daemon=True).start()
    
    def _continue_download_after_speed_test(self, selected):
        """测速完成后继续下载流程"""
        # 清除旧的下载状态文件
        self._clear_download_state()
        
        self.is_downloading = True
        self.download_paused = False
        self.execute_btn.configure(text="⏸️ 暂停下载")
        self.logger.info(f"\n开始下载 {len(selected)} 个DLC...")
        # 在下载开始前，将当前选择的最佳源显示在UI（若已选择）
        try:
            display_map = {
                "r2": "R2云存储",
                "domestic_cloud": "国内云服务器",
                "gitee": "Gitee",
                "github": "GitHub"
            }
            best = getattr(self, 'best_download_source', None)
            if best:
                display_name = display_map.get(best, best)
                self.root.after(0, lambda: self.source_label.configure(text=f"下载源: {display_name}"))
                self.root.after(0, lambda: self.source_label.grid())
        except Exception:
            pass
        
        def progress_callback(percent, downloaded, total):
            """下载进度回调"""
            # 初始化变量
            if not hasattr(progress_callback, 'last_time'):
                progress_callback.last_time = None
                progress_callback.last_downloaded = 0
                progress_callback.last_speed_update = 0
                progress_callback.last_speed_downloaded = 0  # 用于速度计算的下载基准点
                progress_callback.slow_speed_count = 0  # 连续慢速计数
                progress_callback.server_issue_detected = False  # 服务器问题标志
                progress_callback.last_server_check = 0  # 上次服务器检查时间
                progress_callback.download_start_time = None
                
                # 添加更新下载源的方法
                def update_source(source_name):
                    self.root.after(0, lambda: self.source_label.configure(text=f"下载源: {source_name}"))
                    self.root.after(0, lambda: self.source_label.grid())
                
                progress_callback.update_source = update_source
                # 为下载器提供日志记录方法（便于在下载时显示 URL / 错误信息）
                progress_callback.log_message = lambda msg: self.logger.info(msg)
            
            import time
            import requests
            current_time = time.time()
            
                # 进度条实时更新（不限制频率）
            # 仅当 percent 有效时更新进度条（total 未知时 percent=None）
            try:
                if percent is not None:
                    self.root.after(0, lambda: self.progress_bar.set(percent / 100))
            except Exception:
                pass
            
            # 速度信息每0.5秒更新一次（提高更新频率以获得更准确的数据）
            # 初次回调时初始化速度相关时间点，避免过大的首次时间差
            if progress_callback.last_time is None:
                progress_callback.last_time = current_time
                progress_callback.last_speed_update = current_time
                progress_callback.last_speed_downloaded = downloaded
                progress_callback.download_start_time = current_time
                # 重置 EMA，避免从上一个下载继承值
                if hasattr(progress_callback, 'previous_ema'):
                    delattr = False
                    try:
                        del progress_callback.previous_ema
                    except Exception:
                        pass
                # 初次回调不计算速度
            else:
                time_diff = current_time - progress_callback.last_time
                
                # 检查是否到达更新时间（0.5秒）
                if current_time - progress_callback.last_speed_update >= 0.5:
                    # 计算从上次速度更新到这次的速度
                    speed_time_diff = current_time - progress_callback.last_speed_update
                    speed_bytes_diff = downloaded - progress_callback.last_speed_downloaded
                    
                    # 确保时间差和字节差有效
                    if speed_time_diff >= 0.1 and speed_bytes_diff >= 0:
                        # 计算瞬时速度
                        instant_speed = (speed_bytes_diff / speed_time_diff) / (1024 * 1024)  # MB/秒
                        
                        # 使用指数移动平均（EMA）来平滑速度，避免简单平均导致的速度逐渐下降
                        # EMA公式: ema = alpha * current + (1 - alpha) * previous_ema
                        # alpha = 0.3 表示对新值更敏感
                        if not hasattr(progress_callback, 'previous_ema'):
                            progress_callback.previous_ema = instant_speed
                            display_speed = instant_speed
                        else:
                            alpha = 0.3
                            display_speed = alpha * instant_speed + (1 - alpha) * progress_callback.previous_ema
                            progress_callback.previous_ema = display_speed
                        
                        # 限制速度显示范围，避免异常值（0.01 - 100 MB/s）
                        if display_speed < 0.01:
                            display_speed = 0.00
                        elif display_speed > 100:
                            display_speed = 99.99
                        
                        # 服务器质量检测逻辑
                        # 只有在下载时间超过5秒后才开始检测服务器问题，避免小文件误判
                        # 使用 download_start_time 计算实际下载时长
                        download_duration = current_time - (progress_callback.download_start_time or progress_callback.last_time)
                        # 如果速度低于 1.0 MB/s（变更要求），视为慢速
                        if not self.download_paused and download_duration > 5.0 and display_speed < 1.0:
                            progress_callback.slow_speed_count += 1
                            
                            # 如果连续3次慢速，检测服务器连接
                            if progress_callback.slow_speed_count >= 3 and not progress_callback.server_issue_detected:
                                # 每10秒最多检查一次服务器
                                if current_time - progress_callback.last_server_check >= 10:
                                    progress_callback.last_server_check = current_time
                                    
                                    # 检测服务器连接质量
                                    if self._check_server_connection(self.current_download_url):
                                        # 服务器正常，重置计数
                                        progress_callback.slow_speed_count = 0
                                    else:
                                        # 服务器有问题，重新测速并切换源
                                        progress_callback.server_issue_detected = True
                                        self.logger.warning("检测到当前下载源速度异常，正在重新测速选择新源...")
                                        
                                        # 在后台线程中重新测速
                                        def retest_thread():
                                            try:
                                                # 在 UI 上显示测速状态并暂停当前下载，以免并发状态冲突
                                                try:
                                                    self.root.after(0, lambda: self._start_retest_ui("正在测速..."))
                                                    if hasattr(self, 'current_downloader') and self.current_downloader:
                                                        try:
                                                            self.current_downloader.pause()
                                                        except Exception:
                                                            pass
                                                except Exception:
                                                    pass

                                                new_source, new_test_url = self.dlc_manager.source_manager.get_best_download_source(
                                                    silent=True,
                                                    log_callback=self.logger.info
                                                )
                                                # 结束 re-test UI
                                                try:
                                                    self.root.after(0, self._stop_retest_ui)
                                                except Exception:
                                                    pass

                                                if new_source != self.best_download_source:
                                                    self.best_download_source = new_source
                                                    self.logger.info(f"切换到新下载源: {new_source}")
                                                    # 通知UI更新源显示
                                                    if hasattr(progress_callback, 'update_source'):
                                                        display_name = {
                                                            "r2": "R2云存储",
                                                            "domestic_cloud": "国内云服务器", 
                                                            "gitee": "Gitee",
                                                            "github": "GitHub"
                                                        }.get(new_source, new_source)
                                                        progress_callback.update_source(display_name)
                                                    
                                                    # 标记 pending switch, 停止当前下载器，让它重新开始
                                                    try:
                                                        self._pending_switch_url = new_test_url
                                                        self._pending_switch_source = new_source
                                                    except Exception:
                                                        pass
                                                    if hasattr(self, 'current_downloader') and self.current_downloader:
                                                        # 停止当前下载器（但保留 session），保留当前 file 的 tmp 以便尝试续传
                                                        self.current_downloader.stop()
                                                        # 尝试保留当前下载文件的 tmp
                                                        try:
                                                            if self.current_download_url:
                                                                preserve_filename = self.current_download_url.split('/')[-1]
                                                            else:
                                                                preserve_filename = None
                                                        except Exception:
                                                            preserve_filename = None
                                                        # 清理其它未完成临时文件，但保留当前文件的临时文件
                                                        self._cleanup_partial_downloads(preserve_filename=preserve_filename)
                                                    
                                                    # 重置服务器问题标志
                                                    progress_callback.server_issue_detected = False
                                                    progress_callback.slow_speed_count = 0
                                                else:
                                                    # 测速结果相同，显示服务器错误
                                                    self.root.after(0, self._show_server_error)
                                            except Exception as e:
                                                self.logger.error(f"重新测速失败: {e}")
                                                self.root.after(0, self._show_server_error)
                                        
                                        import threading
                                        threading.Thread(target=retest_thread, daemon=True).start()
                        else:
                            # 速度恢复正常，重置计数
                            if progress_callback.slow_speed_count > 0:
                                progress_callback.slow_speed_count -= 1
                            
                            # 如果之前检测到服务器问题，现在检查是否恢复
                            if progress_callback.server_issue_detected and display_speed >= 0.5:
                                # 速度恢复到0.5 MB/s以上，认为服务器恢复正常
                                progress_callback.server_issue_detected = False
                                self.root.after(0, self._hide_server_error)
                        
                        # 更新速度显示
                        self.root.after(0, lambda s=display_speed: self.speed_label.configure(text=f"{s:.2f} MB/s"))
                        
                        # 更新速度计算基准点
                        progress_callback.last_speed_update = current_time
                        progress_callback.last_speed_downloaded = downloaded
            
            progress_callback.last_time = current_time
            progress_callback.last_downloaded = downloaded
        
        def download_thread():
            success = 0
            failed = 0
            
            # 显示进度组件
            self.root.after(0, lambda: self.downloading_label.grid())
            self.root.after(0, lambda: self.progress_bar.grid())
            self.root.after(0, lambda: self.speed_label.grid())
            self.root.after(0, lambda: self.source_label.grid())
            self.root.after(0, lambda: self.progress_bar.set(0))
            self.root.after(0, lambda: self.speed_label.configure(text="0.00 MB/s"))
            self.root.after(0, lambda: self.source_label.configure(text="下载源: 连接中..."))
            
            # 初始化下载器将在每次尝试中创建，确保 stop/close 不会影响后续尝试
            
            # pending switch info used to perform controlled switch after re-test
            self._pending_switch_url = None
            self._pending_switch_source = None

            for idx, dlc in enumerate(selected, 1):
                # 检查是否需要重新选择源（在下载过程中可能因测速而改变）
                current_source = getattr(self, 'best_download_source', 'domestic_cloud')
                # 支持在下载过程中自动重试并切换源
                attempt = 0
                max_attempts = 3
                last_exception = None
                while attempt < max_attempts:
                    attempt += 1
                    # 每次尝试都创建新的 downloader，以避免 stop() 的副作用
                    try:
                        # 如果之前因为重测而暂停了下载，则在开始新尝试前恢复UI和状态
                        if getattr(self, 'download_paused', False):
                            try:
                                self.download_paused = False
                                self.root.after(0, lambda: self.execute_btn.configure(text='⏸️ 暂停下载'))
                                self.logger.info('重新开始下载')
                            except Exception:
                                pass
                        # 关闭并清理旧的 downloader（如存在）
                        if hasattr(self, 'current_downloader') and self.current_downloader:
                            try:
                                self.current_downloader.close()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    downloader = DLCDownloader(progress_callback)
                    self.current_downloader = downloader  # 保存当前尝试的下载器
                    self.logger.info(f"\n{'='*50}")
                    self.logger.info(f"[{idx}/{len(selected)}] {dlc['name']}")
                    
                    # 更新当前下载DLC名称
                    self.root.after(0, lambda name=dlc['name']: self.downloading_label.configure(text=f"正在处理: {name}"))
                    
                    # 根据当前最佳源选择URL
                    selected_url = dlc['url']  # 默认使用主URL
                    selected_fallback_urls = dlc.get('urls', [])  # 默认备用URL
                    
                    # 构建完整的URL列表：主URL + 备用URL
                    all_urls = [(dlc['url'], dlc.get('source', 'unknown'))] + dlc.get('urls', [])
                    
                    # 优先使用当前最佳源的URL
                    for url, source_name in all_urls:
                        if source_name == current_source:
                            selected_url = url
                            # 将其他源作为备用URL
                            selected_fallback_urls = [(u, s) for u, s in all_urls if s != current_source]
                            break
                    
                    # 设置当前下载URL
                    self.current_download_url = selected_url
                    # 同步显示当前下载源（确保即时刷新，而不依赖于 progress_callback 的回调）
                    try:
                        display_map = {
                            "r2": "R2云存储",
                            "domestic_cloud": "国内云服务器",
                            "gitee": "Gitee",
                            "github": "GitHub"
                        }
                        display_name = display_map.get(current_source, current_source)
                        self.root.after(0, lambda: self.source_label.configure(text=f"下载源: {display_name}"))
                        self.root.after(0, lambda: self.source_label.grid())
                    except Exception:
                        pass

                    # 如果当前选定的是 Gitee 源，启动一个后台线程在下载过程中定期快速检测其它源速度（不影响当前下载）
                    # 如果发现更快的源（例如速度 > 5MB/s），则切换到该源
                    gitee_fast_switch_event = None
                    gitee_retest_thread = None
                    if current_source == 'gitee':
                        import threading
                        gitee_fast_switch_event = threading.Event()

                        def _gitee_quick_retest(stop_event: threading.Event, dlc_key=dlc['key'], current_source_name=current_source):
                            try:
                                # 每次检查间隔 (秒)
                                check_interval = 10
                                required_speed = 5.0
                                while not stop_event.is_set():
                                    try:
                                        res = self.dlc_manager.source_manager.find_first_source_above(required_speed, exclude=[current_source_name], silent=True, log_callback=self.logger.info, max_seconds=2.0, max_bytes=2*1024*1024)
                                        if res:
                                            new_source, new_url, measured_speed = res
                                            # 如果找到更快的源，记录并触发切换
                                            if new_source and new_source != getattr(self, 'best_download_source', None):
                                                self.logger.info(f"检测到更快源: {new_source} ({measured_speed:.2f} MB/s)，准备切换")
                                                self.best_download_source = new_source
                                                # 记录等待切换的信息，先暂停当前下载器
                                                try:
                                                    self._pending_switch_url = new_url
                                                    self._pending_switch_source = new_source
                                                    if hasattr(self, 'current_downloader') and self.current_downloader:
                                                        try:
                                                            # 标记 UI 为暂停状态
                                                            self.download_paused = True
                                                            self.current_downloader.pause()
                                                            self.root.after(0, lambda: self.execute_btn.configure(text='▶️ 继续下载'))
                                                            # 显示重测状态
                                                            self.root.after(0, lambda: self._start_retest_ui("暂停并测速..."))
                                                            self.logger.info('下载已暂停，正在切换源...')
                                                        except Exception:
                                                            pass
                                                except Exception:
                                                    pass
                                                # 现在开始停止以便主线程在下一次重试时重新创建 downloader 并使用新 URL
                                                if hasattr(self, 'current_downloader') and self.current_downloader:
                                                    try:
                                                        self.current_downloader.stop()
                                                    except Exception:
                                                        pass
                                                # 结束重测 UI（由主线程恢复状态）
                                                try:
                                                    self.root.after(0, self._stop_retest_ui)
                                                except Exception:
                                                    pass
                                                return
                                            else:
                                                # 没有找到更快的源，恢复暂停的下载，并显示服务器错误
                                                try:
                                                    if hasattr(self, 'current_downloader') and self.current_downloader:
                                                        try:
                                                            self.logger.info('未发现更快源，恢复当前下载')
                                                            self.current_downloader.resume()
                                                            self.download_paused = False
                                                            self.root.after(0, lambda: self.execute_btn.configure(text='⏸️ 暂停下载'))
                                                            # 恢复UI状态
                                                            self.root.after(0, self._hide_server_error)
                                                            # 结束重测UI
                                                            try:
                                                                self.root.after(0, self._stop_retest_ui)
                                                            except Exception:
                                                                pass
                                                        except Exception:
                                                            pass
                                                except Exception:
                                                    pass
                                    except Exception as _e:
                                        # 记录异常但继续循环
                                        self.logger.debug(f"gitee quick re-test 错误: {_e}")
                                        # 等待下一次检测
                                    for _ in range(int(check_interval)):
                                        if stop_event.is_set():
                                            break
                                        time.sleep(1)
                            except Exception as e:
                                self.logger.debug(f"gitee quick re-test 线程终止: {e}")

                        import time
                        gitee_retest_thread = threading.Thread(target=_gitee_quick_retest, args=(gitee_fast_switch_event,), daemon=True)
                        gitee_retest_thread.start()
                    
                    # 在每次下载前重置进度回调相关状态，避免连续多个小文件之间共享计数导致误判
                    try:
                        progress_callback.last_time = None
                        progress_callback.last_downloaded = 0
                        progress_callback.last_speed_update = 0
                        progress_callback.last_speed_downloaded = 0
                        progress_callback.slow_speed_count = 0
                        progress_callback.server_issue_detected = False
                        progress_callback.last_server_check = 0
                        progress_callback.download_start_time = None
                        if hasattr(progress_callback, 'previous_ema'):
                            try:
                                del progress_callback.previous_ema
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # 如果有 pending switch URL（来自 gitee_retest 线程），使用新的 test url 并重置 pending 信息
                    try:
                        if getattr(self, '_pending_switch_url', None):
                            sel = self._pending_switch_url
                            src = self._pending_switch_source
                            # 将新 source 放到 selected_url 和备选中
                            selected_url = sel
                            selected_fallback_urls = [(u, s) for u, s in all_urls if s != src]
                            # 重置 pending 标志
                            self._pending_switch_url = None
                            self._pending_switch_source = None
                            self.logger.info(f"切换到新下载 URL: {selected_url}")
                    except Exception:
                        pass

                    # 下载DLC
                    try:
                        self.logger.info(f"正在下载: {dlc['name']} (使用源: {self.best_download_source})... URL: {selected_url}")
                        expected_hash = dlc.get('checksum') or dlc.get('sha256') or dlc.get('hash')
                        cache_path = downloader.download_dlc(dlc['key'], selected_url, selected_fallback_urls, expected_hash=expected_hash, primary_source_name=current_source)
                        if os.path.exists(cache_path):
                            self.logger.info("从本地缓存加载...")
                        else:
                            self.logger.info("\n下载完成")
                        
                        # 验证下载文件完整性
                        if os.path.exists(cache_path):
                            file_size = os.path.getsize(cache_path)
                            size_mb = file_size / (1024 * 1024)
                            self.logger.info(f"文件大小: {size_mb:.2f} MB")
                            
                            # 如果文件太小，可能下载不完整
                            if file_size < 1024:  # 小于1KB
                                raise Exception(f"下载文件异常：文件大小仅 {file_size} 字节，可能下载不完整")
                            
                            # 显示哈希验证信息（如果有期望哈希）
                            if expected_hash:
                                self.logger.info(f"✓ 文件完整性校验通过 (SHA256)")
                        
                        # 安装
                        self.logger.info(f"正在安装: {dlc['name']}...")
                        self.dlc_installer.install(cache_path, dlc['key'], dlc['name'])
                        self.logger.success("安装成功")
                        success += 1
                        # 成功则停止 gitee 线程（如有）并跳出重试循环
                        try:
                            if gitee_fast_switch_event:
                                gitee_fast_switch_event.set()
                        except Exception:
                            pass
                        # 下载成功则跳出重试循环
                        break
                    except Exception as e:
                        last_exception = e
                        # 结束时确保快速重测线程（gitee）停止，避免其跨文件持续运行
                        try:
                            if gitee_fast_switch_event:
                                gitee_fast_switch_event.set()
                        except Exception:
                            pass

                        # 如果是停止导致的异常（通过 stop() 发起），尝试刷新最佳源并继续重试
                        err_str = str(e)
                        # 检测 stop 情况或连接异常
                        if "下载已停止" in err_str or "Connection aborted" in err_str or "Read timed out" in err_str:
                            # 重新测速选择源，如果选择了新源则尝试继续
                            try:
                                new_source, _ = self.dlc_manager.source_manager.get_best_download_source(
                                    silent=True, log_callback=self.logger.info
                                )
                                if new_source and new_source != getattr(self, 'best_download_source', None):
                                    self.best_download_source = new_source
                                    self.logger.info(f"重试: 切换到新下载源: {new_source}")
                                    # 更新 selected_url 和 fallback_urls
                                    new_url = self.dlc_manager.source_manager.get_url_for_source(dlc['key'], dlc, new_source)
                                    if new_url:
                                        selected_url = new_url
                                        selected_fallback_urls = [(u, s) for u, s in all_urls if s != new_source]
                                        # 清理可能的残留临时文件并换源进行下一次重试
                                        if hasattr(self, 'current_downloader') and self.current_downloader:
                                            self.current_downloader.stop()
                                            try:
                                                if self.current_download_url:
                                                    preserve_filename = self.current_download_url.split('/')[-1]
                                                else:
                                                    preserve_filename = None
                                            except Exception:
                                                preserve_filename = None
                                            self._cleanup_partial_downloads(preserve_filename=preserve_filename)
                                        # 继续下一次重试（attempt 增加）
                                        continue
                            except Exception as _e:
                                self.logger.warning(f"重试测速选择源失败: {_e}")
                        # 不是停止/切换导致的，或者没有找到新源则记录并进一步重试
                        self.logger.warning(f"尝试下载第 {attempt} 次失败: {e}")
                        if attempt >= max_attempts:
                            raise
                        # 小延时后重试
                        import time
                        time.sleep(0.8)
                    # 记录完整异常堆栈到错误日志，并在 GUI 日志中显示
                    error_str = str(e) if e else "未知错误"

                    # 提供更友好的错误信息
                    if "校验失败" in error_str or "哈希" in error_str:
                        friendly_msg = f"下载失败: {dlc['name']} - 文件完整性校验失败，尝试其他源或联系开发者"
                    elif "400 Bad Request" in error_str or "URL可能已过期" in error_str:
                        friendly_msg = f"下载失败: {dlc['name']} - 服务器URL配置问题，请稍后重试或联系开发者"
                    elif "网络" in error_str or "连接" in error_str:
                        friendly_msg = f"下载失败: {dlc['name']} - 网络连接问题，请检查网络设置"
                    else:
                        friendly_msg = f"下载失败: {dlc['name']} - {error_str}"
                    
                    self.logger.error(friendly_msg)
                    self.root.after(0, lambda e=e, msg=friendly_msg: self.logger.log_exception(msg, e))
                    # 如果循环结束但仍有异常，计入失败
                    if attempt >= max_attempts and last_exception:
                        e = last_exception
                        # 记录完整异常堆栈到错误日志，并在 GUI 日志中显示
                        error_str = str(e) if e else "未知错误"
                        if "400 Bad Request" in error_str or "URL可能已过期" in error_str:
                            friendly_msg = f"下载失败: {dlc['name']} - 服务器URL配置问题，请稍后重试或联系开发者"
                        elif "网络" in error_str or "连接" in error_str:
                            friendly_msg = f"下载失败: {dlc['name']} - 网络连接问题，请检查网络设置"
                        else:
                            friendly_msg = f"下载失败: {dlc['name']} - {error_str}"
                        self.logger.error(friendly_msg)
                        self.root.after(0, lambda e=e, msg=friendly_msg: self.logger.log_exception(msg, e))
                        failed += 1
            
            # 停止任何仍在运行的 gitee 快速重测线程（如果存在）
            try:
                if 'gitee_fast_switch_event' in locals() and gitee_fast_switch_event:
                    gitee_fast_switch_event.set()
                if 'gitee_retest_thread' in locals() and gitee_retest_thread and gitee_retest_thread.is_alive():
                    try:
                        gitee_retest_thread.join(timeout=1)
                    except Exception:
                        pass
            except Exception:
                pass

            # 完成，隐藏进度组件
            self.root.after(0, lambda: self.downloading_label.grid_remove())
            self.root.after(0, lambda: self.progress_bar.grid_remove())
            self.root.after(0, lambda: self.speed_label.grid_remove())
            self.root.after(0, lambda: self.source_label.grid_remove())
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"下载完成！成功: {success}, 失败: {failed}")
            
            # 清除当前下载URL
            self.current_download_url = None
            
            # 一键流程的统一最终模态：
            # - If downloads succeeded (success>0) during one-click flow, show a unified success message.
            # - This complements the patch-success path which, if patch was applied but no download occurred,
            #   已在 start_execute() 中触发过统一成功消息。
            if (self._one_click_flow) and success > 0:
                self.root.after(0, lambda: messagebox.showinfo("成功", "解锁成功！"))
            # 重置下载状态
            self.is_downloading = False
            self.download_paused = False
            self.current_downloader = None
            # 在展示最终模态后清除一键流程标志
            if self._one_click_flow:
                self._one_click_flow = False
            
            # 重新加载DLC列表
            self.root.after(100, self.load_dlc_list)
            self.root.after(0, lambda: self.execute_btn.configure(
                text="🔓 一键解锁", 
                state="normal"
            ))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def pause_download(self):
        """暂停下载"""
        if self.current_downloader:
            self.current_downloader.pause()
            self.download_paused = True
            self.execute_btn.configure(text="▶️ 继续下载")
            self.logger.info("下载已暂停")
    
    def resume_download(self):
        """继续下载"""
        if self.current_downloader:
            self.current_downloader.resume()
            self.download_paused = False
            self.execute_btn.configure(text="⏸️ 暂停下载")
            self.logger.info("继续下载...")
        
    def restore_game(self):
        """卸载DLC（删除所有通过本工具安装的DLC）"""
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
        
        # 获取操作记录
        operations = self.dlc_installer.operation_log.get_operations()
        
        if not operations:
            messagebox.showinfo("提示", "没有需要卸载的DLC")
            return
        
        result = messagebox.askyesno("确认", 
            f"即将删除通过本工具安装的 {len(operations)} 个DLC\n是否继续？")
        
        if not result:
            return
        
        self.logger.info("\n开始卸载DLC...")
        success, total = self.dlc_installer.restore_game()
        
        self.logger.info(f"\n卸载完成！已删除 {success}/{total} 个DLC")
        messagebox.showinfo("完成", f"卸载完成！已删除 {success}/{total} 个DLC")
        
        # 重新加载DLC列表
        self.load_dlc_list()
        
    def _check_patch_status(self):
        """检查并更新补丁按钮状态"""
        if not self.patch_manager:
            return
        
        try:
            status = self.patch_manager.check_patch_status()
            
            if status['patched']:
                # 若已打补丁，execute_btn 应允许下载（无补丁操作）
                self.execute_btn.configure(text="🔓 一键解锁", state="normal")
                self.remove_patch_btn.configure(state="normal")
                self.logger.info("检测到已应用补丁")
            else:
                self.execute_btn.configure(text="🔓 一键解锁", state="normal")
                self.remove_patch_btn.configure(state="disabled")
        except Exception as e:
            # 如果检查失败，默认启用应用补丁按钮
            self.execute_btn.configure(state="normal")
            self.remove_patch_btn.configure(state="disabled")
        
    def apply_patch(self):
        """应用CreamAPI补丁"""
        # UI 入口：用户点击“应用补丁”按钮时触发。
        # 注意：与一键解锁流程不同，此方法保留了交互式确认（askyesno），
        # 因此适合需要手动确认的场景（例如仅想单独应用补丁而不下载 DLC）。
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
            "即将应用补丁\n"
            "这将修改游戏的 steam_api64.dll 文件\n"
            "原始文件会自动备份。若游戏目录中缺失该文件，程序将尝试从补丁目录中创建一个目标文件以便处理。\n\n"
            "是否继续？")
        
        if not result:
            return

        self.execute_btn.configure(state="disabled")
        self.remove_patch_btn.configure(state="disabled")
        
        def patch_thread():
            try:
                success, failed = self.patch_manager.apply_patch(self.dlc_list)
                
                if success > 0 and failed == 0:
                    self.root.after(0, lambda: messagebox.showinfo("成功", 
                        f"补丁应用成功！\n"
                        f"已处理 {success} 个文件\n\n"
                        f"请重启游戏生效"))
                elif success > 0:
                    self.root.after(0, lambda: messagebox.showwarning("部分成功", 
                        f"补丁应用部分成功\n"
                        f"成功: {success}, 失败: {failed}\n"
                        f"详情请查看日志"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("失败", 
                        "补丁应用失败！\n详情请查看日志"))
                
                # 更新按钮状态
                self.root.after(0, self._check_patch_status)
                
            except Exception as e:
                # 在主线程中记录完整异常信息并写入错误日志
                self.root.after(0, lambda e=e: self.logger.log_exception("应用补丁时发生错误", e))
                self.root.after(0, lambda: messagebox.showerror("错误", 
                    f"应用补丁时发生错误:\n{str(e)}"))
                self.root.after(0, lambda: self.execute_btn.configure(state="normal"))
        
        threading.Thread(target=patch_thread, daemon=True).start()
        
    def remove_patch(self):
        """移除CreamAPI补丁"""
        # UI 入口：用户点击“移除补丁”按钮触发。
        # 注意：此方法会尝试从本地备份或補丁目录还原原始 DLL，并删除 `cream_api.ini`。
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
        
        result = messagebox.askyesno("确认", 
            "即将移除补丁，是否继续？")
        
        if not result:
            return
        
        self.execute_btn.configure(state="disabled")
        self.remove_patch_btn.configure(state="disabled")
        
        def remove_thread():
            try:
                success, failed = self.patch_manager.remove_patch()
                
                if success > 0 and failed == 0:
                    self.root.after(0, lambda: messagebox.showinfo("成功", "补丁移除成功！"))
                elif success > 0:
                    self.root.after(0, lambda: messagebox.showwarning("部分成功", 
                        f"补丁移除部分成功\n"
                        f"成功: {success}, 失败: {failed}\n"
                        f"详情请查看日志"))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("提示", 
                        "未找到需要还原的补丁文件"))
                
                # 更新按钮状态
                self.root.after(0, self._check_patch_status)
                
            except Exception as e:
                # 在主线程中记录完整异常信息并写入错误日志
                self.root.after(0, lambda e=e: self.logger.log_exception("移除补丁时发生错误", e))
                self.root.after(0, lambda: messagebox.showerror("错误", 
                    f"移除补丁时发生错误:\n{str(e)}"))
                self.root.after(0, lambda: self.remove_patch_btn.configure(state="normal"))
        
        threading.Thread(target=remove_thread, daemon=True).start()
    
    def _clear_cache(self):
        """清理DLC缓存"""
        try:
            from ..utils import PathUtils
            import shutil
            from pathlib import Path
            
            # 获取缓存目录
            cache_dir = Path(PathUtils.get_cache_dir())
            dlc_cache_dir = cache_dir / "dlc"
            
            if not dlc_cache_dir.exists():
                messagebox.showinfo("提示", "缓存目录不存在或已经是空的")
                return
            
            # 计算缓存大小
            total_size = 0
            file_count = 0
            for item in dlc_cache_dir.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
            
            if file_count == 0:
                messagebox.showinfo("提示", "缓存目录是空的")
                return
            
            # 转换为易读的大小
            size_mb = total_size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb/1024:.2f} GB"
            
            # 确认清理
            result = messagebox.askyesno(
                "确认清理缓存",
                f"即将清理DLC缓存目录\n\n"
                f"文件数量: {file_count}\n"
                f"占用空间: {size_str}\n\n"
                f"清理后下次下载DLC需要重新从服务器获取。\n"
                f"是否继续？"
            )
            
            if not result:
                return
            
            # 执行清理
            self.logger.info(f"开始清理缓存: {file_count}个文件, {size_str}")
            
            try:
                shutil.rmtree(dlc_cache_dir)
                dlc_cache_dir.mkdir(parents=True, exist_ok=True)
                self.logger.success(f"缓存清理成功！释放空间: {size_str}")
                messagebox.showinfo("成功", f"缓存清理完成！\n释放空间: {size_str}")
            except Exception as e:
                from ..utils import handle_error
                handle_error(f"清理缓存失败", exc=e)
                messagebox.showerror("错误", f"清理缓存失败:\n{str(e)}")
                
        except Exception as e:
            from ..utils import handle_error
            handle_error("获取缓存信息失败", exc=e)
            messagebox.showerror("错误", f"操作失败:\n{str(e)}")
    
    def _copy_log(self):
        """复制操作日志到剪贴板"""
        try:
            # 获取日志文本内容
            log_content = self.log_text.get("1.0", "end-1c")
            
            if not log_content.strip():
                messagebox.showinfo("提示", "日志内容为空")
                return
            
            # 复制到剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            self.root.update()  # 更新剪贴板
            
            self.logger.success("日志已复制到剪贴板")
            messagebox.showinfo("成功", "日志内容已复制到剪贴板！")
            
        except Exception as e:
            from ..utils import handle_error
            handle_error("复制日志失败", exc=e)
            messagebox.showerror("错误", f"复制失败:\n{str(e)}")
    
    def _export_log(self):
        """导出操作日志到文件"""
        try:
            from tkinter import filedialog
            from datetime import datetime
            import json
            
            # 获取日志文本内容
            log_content = self.log_text.get("1.0", "end-1c")
            
            if not log_content.strip():
                messagebox.showinfo("提示", "日志内容为空")
                return
            
            # 生成默认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"stellaris_dlc_log_{timestamp}.txt"
            
            # 选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="导出日志",
                defaultextension=".txt",
                initialfile=default_filename,
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("JSON文件", "*.json"),
                    ("所有文件", "*.*")
                ]
            )
            
            if not file_path:
                return  # 用户取消
            
            # 导出日志
            if file_path.endswith('.json'):
                # 导出为JSON格式，包含系统信息
                import platform
                from ..config import VERSION
                
                log_data = {
                    "version": VERSION,
                    "export_time": datetime.now().isoformat(),
                    "system_info": {
                        "os": platform.system(),
                        "os_version": platform.version(),
                        "python_version": platform.python_version(),
                        "architecture": platform.machine()
                    },
                    "log_content": log_content
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, indent=2, ensure_ascii=False)
            else:
                # 导出为文本格式
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Stellaris DLC Helper - 操作日志\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*80 + "\n\n")
                    f.write(log_content)
            
            self.logger.success(f"日志已导出到: {file_path}")
            messagebox.showinfo("成功", f"日志已导出到:\n{file_path}")
            
        except Exception as e:
            from ..utils import handle_error
            handle_error("导出日志失败", exc=e)
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")
    
    def _open_settings(self):
        """打开设置对话框"""
        try:
            from .settings_dialog import SettingsDialog
            
            # 创建设置对话框，传入logger以便错误能显示在主窗口
            settings = SettingsDialog(
                self.root, 
                source_manager=self.dlc_manager.source_manager if self.dlc_manager else None,
                main_logger=self.logger
            )
            
        except Exception as e:
            from ..utils import handle_error
            handle_error("打开设置失败", exc=e)
            messagebox.showerror("错误", f"打开设置失败:\n{str(e)}")
    
    def _check_recent_update(self):
        """检查是否刚刚完成更新，如果是则显示提示"""
        try:
            import json
            from ..utils import PathUtils
            
            # 检查更新标记文件
            update_marker = PathUtils.get_cache_dir() / "update_completed.json"
            if update_marker.exists():
                try:
                    with open(update_marker, 'r', encoding='utf-8') as f:
                        marker_data = json.load(f)
                    
                    old_version = marker_data.get('old_version', '未知')
                    new_version = marker_data.get('new_version', VERSION)
                    update_time = marker_data.get('timestamp', '')
                    
                    # 显示更新成功提示
                    message = f"✅ 更新成功！\n\n"
                    message += f"原版本：{old_version}\n"
                    message += f"当前版本：{new_version}\n\n"
                    message += f"程序已成功更新到最新版本。"
                    
                    messagebox.showinfo("更新成功", message)
                    
                    # 删除标记文件
                    update_marker.unlink()
                    
                except Exception as e:
                    self.logger.log_exception("读取更新标记失败", e)
                    # 仍然删除标记文件
                    try:
                        update_marker.unlink()
                    except:
                        pass
        except Exception as e:
            # 静默失败，不影响程序正常启动
            pass
    
    def _auto_check_update(self):
        """自动检查更新（启动时调用）"""
        def on_update_check_complete(update_info, announcement):
            # 如果有强制更新或有公告，显示对话框
            if update_info and update_info.is_force_update(VERSION):
                # 强制更新，显示对话框（无论是否有公告）
                UpdateDialog(self.root, update_info, announcement)
            elif announcement:
                # 没有强制更新但有公告，显示公告对话框
                UpdateDialog(self.root, None, announcement)
            # 非强制更新且无公告时不显示弹窗，避免打扰用户

        updater = AutoUpdater()
        updater.check_for_updates(on_update_check_complete)
    
    def check_update(self):
        """检查程序更新"""
        # 显示检查中提示
        self.update_btn.configure(state="disabled", text="🔄 检查中...")
        self.root.update()

        def on_update_check_complete(update_info, announcement):
            self.update_btn.configure(state="normal", text="🔄 检查更新")

            if update_info or announcement:
                # 有更新或有公告，显示对话框
                UpdateDialog(self.root, update_info, announcement)
            else:
                # 没有更新且没有公告
                messagebox.showinfo("检查更新", "当前已是最新版本，也没有新的系统公告")

        # 创建更新器并检查更新
        updater = AutoUpdater()
        updater.check_for_updates(on_update_check_complete)
    
    def _on_window_map(self, event=None):
        """窗口映射事件处理 - 改善最小化恢复时的重绘"""
        if event.widget == self.root:
            self.root.update_idletasks()
    
    def _on_window_focus(self, event=None):
        """窗口获得焦点事件处理 - 强制重绘"""
        self.root.update_idletasks()
    
    def _check_server_connection(self, current_url=None):
        """检测服务器连接质量"""
        try:
            import requests
            import time
            from ..config import REQUEST_TIMEOUT
            
            # 如果有当前下载URL，优先检测该服务器
            if current_url:
                try:
                    # 提取服务器域名
                    from urllib.parse import urlparse
                    parsed_url = urlparse(current_url)
                    server_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    
                    # 方法1：多次HEAD请求测试连接稳定性
                    success_count = 0
                    total_tests = 4
                    response_times = []
                    
                    for i in range(total_tests):
                        try:
                            start_time = time.time()
                            response = requests.head(server_url, timeout=3, allow_redirects=True)
                            end_time = time.time()
                            
                            if response.status_code in [200, 301, 302, 403, 404]:
                                success_count += 1
                                response_times.append(end_time - start_time)
                        except (requests.RequestException, OSError):
                            pass
                        
                        # 测试间隔
                        if i < total_tests - 1:
                            time.sleep(0.1)
                    
                    # 计算成功率和平均响应时间
                    success_rate = success_count / total_tests
                    avg_response_time = sum(response_times) / len(response_times) if response_times else float('inf')
                    
                    # 网络质量判断标准：
                    # 1. 成功率 >= 50% (至少一半请求成功)
                    # 2. 平均响应时间 < 2秒
                    if success_rate >= 0.5 and avg_response_time < 2.0:
                        self.logger.debug(f"服务器连接质量良好: 成功率={success_rate:.1%}, 平均响应={avg_response_time:.2f}s")
                        return True
                    else:
                        self.logger.warning(f"服务器连接质量差: 成功率={success_rate:.1%}, 平均响应={avg_response_time:.2f}s")
                        return False
                    
                except Exception as e:
                    self.logger.debug(f"检测当前下载服务器失败: {e}")
                    # 当前服务器检测失败，继续检测通用服务器
            
            # 备用检测：使用通用服务器测试网络连通性
            test_urls = [
                "https://github.com/",
                "https://www.google.com/",
                "https://httpbin.org/status/200"
            ]
            
            for url in test_urls:
                try:
                    response = requests.head(url, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        return True  # 网络连接正常
                except (requests.RequestException, OSError):
                    continue
            
            return False  # 所有测试都失败
            
        except Exception as e:
            self.logger.warning(f"服务器连接检测失败: {e}")
            return False
    
    def _show_server_error(self):
        """显示服务器错误状态"""
        # 隐藏进度条
        self.progress_bar.grid_remove()
        # 显示服务器状态文本
        self.server_status_label.configure(text="啊哦，服务器好像出问题了，请稍后再试吧！")
        self.server_status_label.grid()
        # 隐藏速度标签
        self.speed_label.grid_remove()
        self.logger.warning("检测到服务器连接问题，已暂停进度显示")
    
    def _hide_server_error(self):
        """隐藏服务器错误状态，恢复进度条"""
        # 隐藏服务器状态文本
        self.server_status_label.grid_remove()
        # 显示进度条
        self.progress_bar.grid()
        # 显示速度标签
        self.speed_label.grid()
        self.logger.info("服务器连接恢复正常，已恢复进度显示")
    
    def _cleanup_partial_downloads(self, preserve_filename: str = None):
        """清理未完成的下载临时文件"""
        try:
            from ..utils import PathUtils
            cache_dir = PathUtils.get_dlc_cache_dir()
            if os.path.exists(cache_dir):
                for file in os.listdir(cache_dir):
                    if file.endswith('.tmp'):
                        # 如果请求保留一个文件，则跳过该 .tmp
                        if preserve_filename and file == f"{preserve_filename}.tmp":
                            self.logger.debug(f"保留临时文件: {file}")
                            continue
                        file_path = os.path.join(cache_dir, file)
                        try:
                            os.remove(file_path)
                            self.logger.info(f"清理未完成下载文件: {file}")
                        except Exception as e:
                            self.logger.warning(f"无法清理文件 {file}: {e}")
        except Exception as e:
            self.logger.error(f"清理下载文件时出错: {e}")
