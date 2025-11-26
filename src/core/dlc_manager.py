#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DLC管理模块
负责获取DLC列表、检查已安装的DLC
"""

import os
import requests
from ..config import DLC_INDEX_URL, STELLARIS_APP_ID, REQUEST_TIMEOUT
from ..utils import PathUtils


class DLCManager:
    """DLC管理类"""
    
    def __init__(self, game_path):
        """
        初始化DLC管理器
        
        Args:
            game_path: 游戏路径
        """
        self.game_path = game_path
        
    def fetch_dlc_list(self):
        """
        从服务器获取DLC列表
        
        Returns:
            list: DLC列表，每项包含 key, name, url, size
            
        Raises:
            Exception: 网络错误或数据格式错误
        """
        response = requests.get(DLC_INDEX_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if STELLARIS_APP_ID not in data:
            raise Exception("服务器上暂无Stellaris的DLC数据")
        
        stellaris_data = data[STELLARIS_APP_ID]
        dlcs = stellaris_data.get("dlcs", {})
        
        if not dlcs:
            raise Exception("服务器上暂无可用DLC")
        
        dlc_list = []
        for key, info in dlcs.items():
            dlc_list.append({
                "key": key,
                "name": info.get("name", key),
                "url": info.get("url", ""),
                "size": info.get("size", "未知")
            })
        
        # 按DLC编号排序
        dlc_list.sort(key=self._extract_dlc_number)
        return dlc_list
    
    @staticmethod
    def _extract_dlc_number(dlc_item):
        """从DLC键名中提取编号用于排序"""
        import re
        match = re.search(r'dlc(\d+)', dlc_item["key"])
        return int(match.group(1)) if match else 9999
    
    def get_installed_dlcs(self):
        """
        获取已安装的DLC列表
        
        Returns:
            set: 已安装的DLC键名集合
        """
        try:
            dlc_folder = PathUtils.get_dlc_folder(self.game_path)
            if not os.path.exists(dlc_folder):
                return set()
            
            installed = set()
            for item in os.listdir(dlc_folder):
                item_path = os.path.join(dlc_folder, item)
                if os.path.isdir(item_path):
                    installed.add(item)
            
            return installed
        except Exception:
            return set()
    
    def is_dlc_installed(self, dlc_key):
        """
        检查指定DLC是否已安装
        
        Args:
            dlc_key: DLC键名
            
        Returns:
            bool: 是否已安装
        """
        dlc_folder = PathUtils.get_dlc_folder(self.game_path)
        dlc_path = os.path.join(dlc_folder, dlc_key)
        return os.path.exists(dlc_path) and os.path.isdir(dlc_path)
