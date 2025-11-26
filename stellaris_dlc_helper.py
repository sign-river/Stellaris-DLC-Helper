#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stellaris DLC Helper - 群星DLC一键解锁工具
专为Stellaris游戏设计的轻量级DLC管理工具

作者: sign-river
许可证: MIT License
项目地址: https://github.com/sign-river/Stellaris-DLC-Helper
"""

import os
import sys
import json
import hashlib
import zipfile
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import threading

# 版本号
VERSION = "1.0.0"

# Stellaris AppID (固定)
STELLARIS_APP_ID = "281990"

# DLC 服务器配置
DLC_SERVER_URL = "http://47.100.2.190/dlc/"
DLC_INDEX_URL = f"{DLC_SERVER_URL}index.json"

# 字体配置
FONT1 = ("Microsoft YaHei UI", 20, "bold")
FONT2 = ("Microsoft YaHei UI", 16, "bold")
FONT3 = ("Microsoft YaHei UI", 12)
FONT4 = ("Microsoft YaHei UI", 10)


class StellarisDLCHelper:
    """Stellaris DLC Helper 主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"Stellaris DLC Helper v{VERSION}")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 状态变量
        self.game_path = ""
        self.dlc_list = []
        self.dlc_vars = []
        
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
        
        # DLC列表区域
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
        
        # 进度标签
        self.progress_label = ttk.Label(self.root, text="", font=FONT4)
        self.progress_label.pack(pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)
        
        self.download_btn = ttk.Button(button_frame, text="下载并安装选中的DLC", 
                                       command=self.download_dlcs,
                                       state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        restore_btn = ttk.Button(button_frame, text="还原游戏", 
                                command=self.restore_game)
        restore_btn.pack(side=tk.LEFT, padx=5)
        
        # 日志区域（可折叠）
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding=5)
        log_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, 
                                                  font=("Consolas", 9),
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.X)
        
    def log(self, message):
        """写入日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def browse_game_path(self):
        """浏览选择游戏路径"""
        path = filedialog.askdirectory(title="选择Stellaris游戏根目录")
        if path:
            # 验证是否是Stellaris目录
            if not os.path.exists(os.path.join(path, "stellaris.exe")):
                messagebox.showwarning("警告", 
                    "所选目录似乎不是Stellaris游戏目录！\n"
                    "请确保选择包含 stellaris.exe 的文件夹。")
                return
            
            self.game_path = path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.log(f"已选择游戏路径: {path}")
            
    def load_dlc_list(self):
        """从服务器加载DLC列表"""
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
            
        self.status_label.config(text="正在从服务器获取DLC列表...")
        self.log("正在连接DLC服务器...")
        
        def fetch_thread():
            try:
                response = requests.get(DLC_INDEX_URL, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if STELLARIS_APP_ID not in data:
                    self.status_label.config(text="服务器上暂无Stellaris的DLC")
                    self.log("错误: 服务器上没有找到Stellaris的DLC数据")
                    return
                
                stellaris_data = data[STELLARIS_APP_ID]
                dlcs = stellaris_data.get("dlcs", {})
                
                if not dlcs:
                    self.status_label.config(text="服务器上暂无可用DLC")
                    self.log("服务器上暂无可用DLC")
                    return
                
                self.dlc_list = []
                for key, info in dlcs.items():
                    self.dlc_list.append({
                        "key": key,
                        "name": info.get("name", key),
                        "url": info.get("url", ""),
                        "size": info.get("size", "未知")
                    })
                
                # 按DLC编号排序
                self.dlc_list.sort(key=lambda x: self.extract_dlc_number(x["key"]))
                
                self.root.after(0, self.display_dlc_list)
                
            except Exception as e:
                self.status_label.config(text=f"加载失败: {str(e)}")
                self.log(f"错误: 无法加载DLC列表 - {str(e)}")
        
        threading.Thread(target=fetch_thread, daemon=True).start()
        
    def extract_dlc_number(self, dlc_key):
        """从DLC键名中提取编号用于排序"""
        import re
        match = re.search(r'dlc(\d+)', dlc_key)
        return int(match.group(1)) if match else 9999
        
    def display_dlc_list(self):
        """显示DLC列表"""
        # 清空现有列表
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.dlc_vars = []
        
        # 检查已安装的DLC
        installed_dlcs = self.check_installed_dlcs()
        
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
        self.log(f"DLC列表加载完成: 共{total}个，已安装{installed_count}个")
        
        # 启用下载按钮
        if available_count > 0:
            self.download_btn.config(state=tk.NORMAL)
        
    def check_installed_dlcs(self):
        """检查已安装的DLC"""
        try:
            dlc_folder = os.path.join(self.game_path, "dlc")
            if not os.path.exists(dlc_folder):
                return set()
            
            installed = set()
            for item in os.listdir(dlc_folder):
                item_path = os.path.join(dlc_folder, item)
                if os.path.isdir(item_path):
                    installed.add(item)
            
            return installed
        except Exception as e:
            self.log(f"检查已安装DLC时出错: {str(e)}")
            return set()
            
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
        self.log(f"\n开始下载 {len(selected)} 个DLC...")
        
        def download_thread():
            success = 0
            failed = 0
            
            for idx, dlc in enumerate(selected, 1):
                try:
                    self.log(f"\n{'='*50}")
                    self.log(f"[{idx}/{len(selected)}] {dlc['name']}")
                    
                    # 检查缓存
                    cache_path = self.get_cache_path(dlc['key'])
                    temp_path = os.path.join(self.get_cache_dir(), f"{dlc['key']}.zip")
                    
                    if os.path.exists(cache_path):
                        self.log("从本地缓存加载...")
                        temp_path = cache_path
                    else:
                        # 下载文件
                        self.root.after(0, lambda: self.progress_label.config(
                            text=f"下载中 {dlc['name']}..."))
                        
                        if self.download_file(dlc['url'], temp_path, dlc['name']):
                            self.log("下载完成")
                            # 保存到缓存
                            if temp_path != cache_path:
                                import shutil
                                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                                shutil.copy2(temp_path, cache_path)
                        else:
                            failed += 1
                            continue
                    
                    # 解压安装
                    self.root.after(0, lambda: self.progress_label.config(
                        text=f"安装中 {dlc['name']}..."))
                    
                    if self.install_dlc(temp_path, dlc['key'], dlc['name']):
                        self.log("✓ 安装成功")
                        success += 1
                    else:
                        self.log("✗ 安装失败")
                        failed += 1
                    
                    # 清理临时文件
                    if temp_path != cache_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                except Exception as e:
                    self.log(f"✗ 错误: {str(e)}")
                    failed += 1
            
            # 完成
            self.root.after(0, lambda: self.progress_label.config(text=""))
            self.root.after(0, lambda: self.status_label.config(
                text=f"下载完成！成功: {success}, 失败: {failed}"))
            self.log(f"\n{'='*50}")
            self.log(f"下载完成！成功: {success}, 失败: {failed}")
            
            # 重新加载DLC列表
            self.root.after(100, self.load_dlc_list)
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
        
        threading.Thread(target=download_thread, daemon=True).start()
        
    def download_file(self, url, dest_path, name):
        """下载文件"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            percent = (downloaded / total) * 100
                            self.root.after(0, lambda p=percent: 
                                self.progress_label.config(
                                    text=f"下载中 {name}: {p:.1f}%"))
            
            return True
        except Exception as e:
            self.log(f"下载失败: {str(e)}")
            return False
            
    def install_dlc(self, zip_path, dlc_key, dlc_name):
        """解压并安装DLC"""
        try:
            dlc_folder = os.path.join(self.game_path, "dlc")
            os.makedirs(dlc_folder, exist_ok=True)
            
            target_folder = os.path.join(dlc_folder, dlc_key)
            
            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_folder)
            
            # 记录操作
            self.add_operation("install_dlc", {
                "dlc_key": dlc_key,
                "dlc_name": dlc_name,
                "install_path": target_folder,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return True
        except Exception as e:
            self.log(f"安装失败: {str(e)}")
            return False
            
    def restore_game(self):
        """还原游戏（删除所有通过本工具安装的DLC）"""
        if not self.game_path:
            messagebox.showwarning("警告", "请先选择游戏路径！")
            return
        
        # 读取操作日志
        log = self.load_operation_log()
        operations = log.get("operations", [])
        
        if not operations:
            messagebox.showinfo("提示", "没有需要还原的操作")
            return
        
        result = messagebox.askyesno("确认", 
            f"即将删除通过本工具安装的 {len(operations)} 个DLC\n是否继续？")
        
        if not result:
            return
        
        self.log("\n开始还原游戏...")
        success = 0
        
        for op in reversed(operations):
            if op["type"] == "install_dlc":
                try:
                    dlc_path = op["details"]["install_path"]
                    if os.path.exists(dlc_path):
                        import shutil
                        shutil.rmtree(dlc_path)
                        self.log(f"✓ 已删除: {op['details']['dlc_name']}")
                        success += 1
                    else:
                        self.log(f"- 已不存在: {op['details']['dlc_name']}")
                except Exception as e:
                    self.log(f"✗ 删除失败: {str(e)}")
        
        # 清空操作日志
        self.clear_operation_log()
        
        self.log(f"\n还原完成！已删除 {success} 个DLC")
        messagebox.showinfo("完成", f"还原完成！已删除 {success} 个DLC")
        
        # 重新加载DLC列表
        self.load_dlc_list()
        
    # ===== 辅助函数 =====
    
    def get_cache_dir(self):
        """获取缓存目录"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        cache_dir = os.path.join(base_dir, "Stellaris_DLC_Cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
        
    def get_cache_path(self, dlc_key):
        """获取DLC缓存文件路径"""
        cache_dir = os.path.join(self.get_cache_dir(), "dlc", STELLARIS_APP_ID)
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{dlc_key}.zip")
        
    def get_log_path(self):
        """获取操作日志路径"""
        log_dir = os.path.join(self.get_cache_dir(), "operation_logs")
        os.makedirs(log_dir, exist_ok=True)
        
        path_hash = hashlib.md5(self.game_path.encode()).hexdigest()[:12]
        return os.path.join(log_dir, f"operations_{path_hash}.json")
        
    def load_operation_log(self):
        """加载操作日志"""
        log_path = self.get_log_path()
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"operations": [], "game_path": self.game_path}
        
    def save_operation_log(self, log):
        """保存操作日志"""
        log_path = self.get_log_path()
        log["game_path"] = self.game_path
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存日志失败: {str(e)}")
            
    def add_operation(self, op_type, details):
        """添加操作记录"""
        log = self.load_operation_log()
        log["operations"].append({
            "type": op_type,
            "details": details
        })
        self.save_operation_log(log)
        
    def clear_operation_log(self):
        """清空操作日志"""
        log_path = self.get_log_path()
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
            except:
                pass


def main():
    """主函数"""
    root = tk.Tk()
    app = StellarisDLCHelper(root)
    root.mainloop()


if __name__ == "__main__":
    main()
