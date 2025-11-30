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
from .source_manager import SourceManager


class DLCManager:
    """DLC管理类"""
    
    def __init__(self, game_path):
        """
        初始化DLC管理器
        
        参数:
            game_path: 游戏路径
        """
        self.game_path = game_path
        self.source_manager = SourceManager()
        
    def fetch_dlc_list(self):
        """
        从国内服务器获取DLC列表
        
        返回:
            list: DLC列表，每项包含 key, name, url, size
            
        抛出:
            Exception: 网络错误或数据格式错误
        """
        # 只从国内服务器获取DLC列表
        domestic_source = self.source_manager.get_source_by_name("domestic_cloud")
        if not domestic_source:
            raise Exception("未找到国内云服务器配置")
        
        data = self.source_manager.fetch_dlc_data_from_source(domestic_source)
        if not data:
            raise Exception("无法从国内服务器获取DLC数据")
        
        # 处理数据
        if STELLARIS_APP_ID not in data:
            raise Exception("服务器上暂无Stellaris的DLC数据")
        
        stellaris_data = data[STELLARIS_APP_ID]
        dlcs = stellaris_data.get("dlcs", {})
        
        if not dlcs:
            raise Exception("服务器上暂无可用DLC")
        
        dlc_list = []
        for key, info in dlcs.items():
            # 获取所有可用的下载URL（包括所有源的备用URL）
            url_tuples = self.source_manager.get_download_urls_for_dlc(key, info)
            
            # 分离主URL和备用URL
            if url_tuples:
                main_url = url_tuples[0][0]  # 主URL
                fallback_urls = url_tuples[1:]  # 备用URL元组列表
            else:
                main_url = ""
                fallback_urls = []
            
            dlc_list.append({
                "key": key,
                "name": info.get("name", key),
                "url": main_url,  # 主URL
                "urls": fallback_urls,  # 备用URL元组列表，用于fallback
                "size": info.get("size", "未知"),
                "source": info.get("_source", "unknown")
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
        
        返回:
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
                    # 提取DLC键名（如 dlc001_xxx -> dlc001）
                    # 支持格式：dlc001, dlc001_name, dlc001_name_xxx
                    if item.startswith('dlc'):
                        # 取下划线前的部分作为键名
                        key = item.split('_')[0]
                        installed.add(key)
            
            return installed
        except Exception:
            return set()
    
    def is_dlc_installed(self, dlc_key):
        """
        检查指定DLC是否已安装
        
        参数:
            dlc_key: DLC键名
            
        返回:
            bool: 是否已安装
        """
        dlc_folder = PathUtils.get_dlc_folder(self.game_path)
        dlc_path = os.path.join(dlc_folder, dlc_key)
        return os.path.exists(dlc_path) and os.path.isdir(dlc_path)
