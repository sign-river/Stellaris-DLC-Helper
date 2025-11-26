#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from ..config import VERSION, FONT1, FONT2, FONT3, FONT4
from ..core import DLCManager, DLCDownloader, DLCInstaller, PatchManager
from ..utils import Logger, PathUtils


class MainWindow:
    """主窗口类"""
    
    def __init__(self, root):
        """
        初始化主窗口
        
        Args:
            root: Tkinter根窗口
        """
        self.root = root
        self.root.title(f"Stellaris DLC Helper v{VERSION}")
        self.root.geometry("900x700")  # 增大窗口尺寸
        self.root.resizable(True, True)
        
        # 状态变量
        self.game_path = ""
        self.dlc_list = []
        self.dlc_vars = []
        
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
        # 标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=10)
        
        ttk.Label(title_frame, text="🌟 Stellaris DLC Helper", 
                 font=FONT1).pack()
        ttk.Label(title_frame, text="群星DLC一键解锁工具", 
                 font=FONT4, foreground='#666666').pack()
        
        # 分隔线
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # 游戏路径选择区域
        self._create_path_selection()
        
        # DLC列表区域
        self._create_dlc_list_area()
        
        # 进度标签
        self.progress_label = ttk.Label(self.root, text="", font=FONT4)
        self.progress_label.pack(pady=5)
        
        # 按钮区域
        self._create_button_area()
        
        # 日志区域
        self._create_log_area()
        
    def _create_path_selection(self):
        """创建游戏路径选择区域"""
        path_frame = ttk.LabelFrame(self.root, text="游戏路径", padding=10)
        path_frame.pack(fill=tk.X, padx=20, pady=10)
        
        path_input_frame = ttk.Frame(path_frame)
        path_input_frame.pack(fill=tk.X)
        
        self.path_entry = ttk.Entry(path_input_frame, font=FONT4)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_btn = ttk.Button(path_input_frame, text="浏览", 
                               command=self.browse_game_path)
        browse_btn.pack(side=tk.LEFT)
        
        load_btn = ttk.Button(path_input_frame, text="加载DLC列表", 
                             command=self.load_dlc_list)
        load_btn.pack(side=tk.LEFT, padx=(10, 0))
        
    def _create_dlc_list_area(self):
        """创建DLC列表区域"""
        dlc_frame = ttk.LabelFrame(self.root, text="可用DLC", padding=10)
        dlc_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 状态标签
        self.status_label = ttk.Label(dlc_frame, text="请先选择游戏路径并加载DLC列表", 
                                     font=FONT4, foreground='#666666')
        self.status_label.pack(pady=5)
        
        # 全选复选框
        select_frame = ttk.Frame(dlc_frame)
        select_frame.pack(fill=tk.X, pady=5)
        
        self.select_all_var = tk.BooleanVar(value=False)
        select_all_cb = ttk.Checkbutton(select_frame, text="全选", 
                                       variable=self.select_all_var,
                                       command=self.toggle_select_all)
        select_all_cb.pack(side=tk.LEFT)
        
        inverse_btn = ttk.Button(select_frame, text="反选", 
                                command=self.inverse_selection)
        inverse_btn.pack(side=tk.LEFT, padx=10)
        
        # 分隔线
        ttk.Separator(dlc_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # DLC列表（滚动区域）
        list_container = ttk.Frame(dlc_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(list_container)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", 
                                 command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind("<Configure>", 
                                  lambda e: self.canvas.configure(
                                      scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 鼠标滚轮支持
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        
    def _create_button_area(self):
        """创建按钮区域"""
        # 添加分隔线
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=20, pady=10)
        
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=15)  # 增加上下间距
        
        self.download_btn = ttk.Button(button_frame, text="下载并安装选中的DLC", 
                                       command=self.download_dlcs,
                                       state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.patch_btn = ttk.Button(button_frame, text="应用补丁", 
                                    command=self.apply_patch,
                                    state=tk.DISABLED)
        self.patch_btn.pack(side=tk.LEFT, padx=5)
        
        self.remove_patch_btn = ttk.Button(button_frame, text="移除补丁", 
                                           command=self.remove_patch,
                                           state=tk.DISABLED)
        self.remove_patch_btn.pack(side=tk.LEFT, padx=5)
        
        restore_btn = ttk.Button(button_frame, text="还原游戏", 
                                command=self.restore_game)
        restore_btn.pack(side=tk.LEFT, padx=5)
        
    def _create_log_area(self):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding=5)
        log_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, 
                                                  font=("Consolas", 9),
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.X)
        
        # 设置日志组件
        self.logger.set_widget(self.log_text)
        
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
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            
            # 初始化核心组件
            self.dlc_manager = DLCManager(path)
            self.dlc_installer = DLCInstaller(path)
            self.patch_manager = PatchManager(path, self.logger)
            
            self.logger.info(f"已选择游戏路径: {path}")
            
            # 检查补丁状态
            self._check_patch_status()
            
    def load_dlc_list(self):
        """从服务器加载DLC列表"""
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
            
        self.status_label.config(text="正在从服务器获取DLC列表...")
        self.logger.info("正在连接DLC服务器...")
        
        def fetch_thread():
            try:
                # 获取DLC列表
                self.dlc_list = self.dlc_manager.fetch_dlc_list()
                self.root.after(0, self.display_dlc_list)
                
            except Exception as e:
                self.status_label.config(text=f"加载失败: {str(e)}")
                self.logger.error(f"无法加载DLC列表 - {str(e)}")
        
        threading.Thread(target=fetch_thread, daemon=True).start()
        
    def display_dlc_list(self):
        """显示DLC列表"""
        # 清空现有列表
        for widget in self.scrollable_frame.winfo_children():
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
            
            frame = ttk.Frame(self.scrollable_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # 检查是否已安装
            is_installed = dlc["key"] in installed_dlcs
            
            if is_installed:
                # 已安装的DLC显示为禁用状态
                cb = ttk.Checkbutton(frame, variable=var, state=tk.DISABLED)
                cb.pack(side=tk.LEFT)
                label_text = f"{dlc['name']} (已安装)"
                label = ttk.Label(frame, text=label_text, font=FONT4, 
                                 foreground='#999999')
            else:
                cb = ttk.Checkbutton(frame, variable=var)
                cb.pack(side=tk.LEFT)
                label_text = f"{dlc['name']} ({dlc['size']})"
                label = ttk.Label(frame, text=label_text, font=FONT4)
            
            label.pack(side=tk.LEFT, padx=5)
            
            self.dlc_vars.append(dlc_info)
        
        # 更新状态
        total = len(self.dlc_list)
        installed_count = len(installed_dlcs)
        available_count = total - installed_count
        
        self.status_label.config(
            text=f"共 {total} 个DLC | 已安装: {installed_count} | 可下载: {available_count}")
        self.logger.info(f"DLC列表加载完成: 共{total}个，已安装{installed_count}个")
        
        # 启用下载按钮
        if available_count > 0:
            self.download_btn.config(state=tk.NORMAL)
            
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
        
        self.download_btn.config(state=tk.DISABLED)
        self.status_label.config(text="准备下载...")
        self.logger.info(f"\n开始下载 {len(selected)} 个DLC...")
        
        def progress_callback(percent, downloaded, total):
            """下载进度回调"""
            self.root.after(0, lambda: self.progress_label.config(
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
                        self.root.after(0, lambda: self.progress_label.config(
                            text=f"下载中 {dlc['name']}..."))
                        cache_path = downloader.download_dlc(dlc['key'], dlc['url'])
                        self.logger.info("下载完成")
                    
                    # 安装
                    self.root.after(0, lambda: self.progress_label.config(
                        text=f"安装中 {dlc['name']}..."))
                    
                    self.dlc_installer.install(cache_path, dlc['key'], dlc['name'])
                    self.logger.success("安装成功")
                    success += 1
                    
                except Exception as e:
                    self.logger.error(f"错误: {str(e)}")
                    failed += 1
            
            # 完成
            self.root.after(0, lambda: self.progress_label.config(text=""))
            self.root.after(0, lambda: self.status_label.config(
                text=f"下载完成！成功: {success}, 失败: {failed}"))
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"下载完成！成功: {success}, 失败: {failed}")
            
            # 重新加载DLC列表
            self.root.after(100, self.load_dlc_list)
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
        
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
                self.patch_btn.config(state=tk.DISABLED)
                self.remove_patch_btn.config(state=tk.NORMAL)
                self.logger.info("检测到已应用补丁")
            else:
                self.patch_btn.config(state=tk.NORMAL)
                self.remove_patch_btn.config(state=tk.DISABLED)
        except Exception as e:
            # 如果检查失败，默认启用应用补丁按钮
            self.patch_btn.config(state=tk.NORMAL)
            self.remove_patch_btn.config(state=tk.DISABLED)
    
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
        
        self.patch_btn.config(state=tk.DISABLED)
        self.remove_patch_btn.config(state=tk.DISABLED)
        
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
                self.logger.error(f"应用补丁时发生错误: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("错误", 
                    f"应用补丁时发生错误:\n{str(e)}"))
                self.root.after(0, lambda: self.patch_btn.config(state=tk.NORMAL))
        
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
        
        self.patch_btn.config(state=tk.DISABLED)
        self.remove_patch_btn.config(state=tk.DISABLED)
        
        def remove_thread():
            try:
                success, failed = self.patch_manager.remove_patch()
                
                if success > 0 and failed == 0:
                    self.root.after(0, lambda: messagebox.showinfo("成功", 
                        f"补丁移除成功！\n"
                        f"已还原 {success} 个文件"))
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
                self.logger.error(f"移除补丁时发生错误: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("错误", 
                    f"移除补丁时发生错误:\n{str(e)}"))
                self.root.after(0, lambda: self.remove_patch_btn.config(state=tk.NORMAL))
        
        threading.Thread(target=remove_thread, daemon=True).start()
