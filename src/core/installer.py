#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装模块
负责安装和卸载DLC
"""

import os
import zipfile
import shutil
from datetime import datetime
from ..utils import PathUtils, OperationLog


class DLCInstaller:
    """DLC安装器类"""
    
    def __init__(self, game_path):
        """
        初始化安装器
        
        参数:
            game_path: 游戏路径
        """
        self.game_path = game_path
        self.operation_log = OperationLog(game_path)
        
    def install(self, zip_path, dlc_key, dlc_name):
        """
        安装DLC
        
        参数:
            zip_path: DLC压缩包路径
            dlc_key: DLC键名
            dlc_name: DLC名称
            
            返回:
            bool: 是否成功
            
        抛出:
            Exception: 安装失败
        """
        try:
            dlc_folder = PathUtils.get_dlc_folder(self.game_path)
            os.makedirs(dlc_folder, exist_ok=True)
            
            # 使用 DLC 的 key + 原始名称作为目标文件夹名，例如: dlc001_symbols_of_domination
            # 优先使用提供的 dlc_key 和 dlc_name（对 dlc_name 做 slug 化处理），以保证安装目录与 DLC 索引一致
            def _slugify(name: str) -> str:
                import re
                if not name:
                    return ""
                # 将非字母数字替换为下划线
                s = re.sub(r"[^0-9a-zA-Z]+", "_", name)
                # 合并下划线并转换为小写
                s = re.sub(r"_+", "_", s).strip("_")
                return s.lower()

            if dlc_key:
                if dlc_name:
                    folder_name = f"{dlc_key}_{_slugify(dlc_name)}"
                else:
                    folder_name = dlc_key
            else:
                # 作为保险回退使用 ZIP 名称（没有 dlc_key 的情况）
                folder_name = os.path.splitext(os.path.basename(zip_path))[0]
            target_folder = os.path.join(dlc_folder, folder_name)
            
            # 如果目标文件夹已存在，先删除
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder)
            
            # 创建临时解压目录
            temp_extract_dir = target_folder + "_temp"
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir)
            
            try:
                # 先解压到临时目录
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
                
                # 检查解压后的内容
                extracted_items = os.listdir(temp_extract_dir)
                
                if len(extracted_items) == 1:
                    # 如果只有一个项目，检查是否是文件夹
                    single_item = os.path.join(temp_extract_dir, extracted_items[0])
                    if os.path.isdir(single_item):
                        # 如果是文件夹，将其内容移动到目标目录
                        os.makedirs(target_folder, exist_ok=True)  # 确保目标目录存在
                        for item in os.listdir(single_item):
                            shutil.move(os.path.join(single_item, item), target_folder)
                    else:
                        # 如果是文件，直接移动
                        os.makedirs(target_folder, exist_ok=True)
                        shutil.move(single_item, target_folder)
                else:
                    # 如果有多个项目，直接移动所有内容
                    os.makedirs(target_folder, exist_ok=True)
                    for item in extracted_items:
                        shutil.move(os.path.join(temp_extract_dir, item), target_folder)
            
            finally:
                # 清理临时目录
                if os.path.exists(temp_extract_dir):
                    shutil.rmtree(temp_extract_dir)
            
            # 记录操作
            self.operation_log.add_operation("install_dlc", {
                "dlc_key": dlc_key,
                "dlc_name": dlc_name,
                "install_path": target_folder,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return True
        except Exception as e:
            raise Exception(f"安装失败: {str(e)}")
    
    def uninstall(self, dlc_key):
        """
        卸载DLC
        
        参数:
            dlc_key: DLC键名
            
        返回:
            bool: 是否成功
        """
        try:
            operations = self.operation_log.get_operations()
            for op in reversed(operations):
                if op["type"] == "install_dlc" and op["details"]["dlc_key"] == dlc_key:
                    dlc_path = op["details"]["install_path"]
                    if os.path.exists(dlc_path):
                        shutil.rmtree(dlc_path)
                        return True
            return False
        except Exception:
            return False
    
    def restore_game(self):
        """
        卸载DLC（删除所有通过本工具安装的DLC）
        
        Returns:
            tuple: (成功数量, 总数量)
        """
        operations = self.operation_log.get_operations()
        success = 0
        total = 0
        
        for op in reversed(operations):
            if op["type"] == "install_dlc":
                try:
                    dlc_path = op["details"]["install_path"]
                    if os.path.exists(dlc_path):
                        total += 1  # 只计算实际存在的 DLC
                        shutil.rmtree(dlc_path)
                        success += 1
                except Exception:
                    pass
        
        # 清空操作日志
        if success > 0 or len(operations) > 0:
            self.operation_log.clear()
        
        return success, total
