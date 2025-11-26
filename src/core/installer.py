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
        
        Args:
            game_path: 游戏路径
        """
        self.game_path = game_path
        self.operation_log = OperationLog(game_path)
        
    def install(self, zip_path, dlc_key, dlc_name):
        """
        安装DLC
        
        Args:
            zip_path: DLC压缩包路径
            dlc_key: DLC键名
            dlc_name: DLC名称
            
        Returns:
            bool: 是否成功
            
        Raises:
            Exception: 安装失败
        """
        try:
            dlc_folder = PathUtils.get_dlc_folder(self.game_path)
            os.makedirs(dlc_folder, exist_ok=True)
            
            target_folder = os.path.join(dlc_folder, dlc_key)
            
            # 如果目标文件夹已存在，先删除
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder)
            
            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_folder)
            
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
        
        Args:
            dlc_key: DLC键名
            
        Returns:
            bool: 是否成功
        """
        try:
            dlc_folder = PathUtils.get_dlc_folder(self.game_path)
            target_folder = os.path.join(dlc_folder, dlc_key)
            
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder)
                return True
            return False
        except Exception:
            return False
    
    def restore_game(self):
        """
        还原游戏（删除所有通过本工具安装的DLC）
        
        Returns:
            tuple: (成功数量, 总数量)
        """
        operations = self.operation_log.get_operations()
        success = 0
        total = 0
        
        for op in reversed(operations):
            if op["type"] == "install_dlc":
                total += 1
                try:
                    dlc_path = op["details"]["install_path"]
                    if os.path.exists(dlc_path):
                        shutil.rmtree(dlc_path)
                        success += 1
                except Exception:
                    pass
        
        # 清空操作日志
        if total > 0:
            self.operation_log.clear()
        
        return success, total
