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
        从多个服务器获取DLC列表并合并
        
        返回:
            list: DLC列表，每项包含 key, name, url, size
            
        抛出:
            Exception: 网络错误或数据格式错误
        """
        all_data = []
        
        # 从所有启用的源获取数据
        enabled_sources = self.source_manager.get_enabled_sources()
        if not enabled_sources:
            raise Exception("没有启用的下载源")
        
        for source in enabled_sources:
            data = self.source_manager.fetch_dlc_data_from_source(source)
            if data:
                all_data.append(data)
        
        if not all_data:
            raise Exception("所有下载源都无法访问")
        
        # 合并数据
        merged_data = self.source_manager.merge_dlc_data(all_data)
        
        if STELLARIS_APP_ID not in merged_data:
            raise Exception("服务器上暂无Stellaris的DLC数据")
        
        stellaris_data = merged_data[STELLARIS_APP_ID]
        dlcs = stellaris_data.get("dlcs", {})
        
        if not dlcs:
            raise Exception("服务器上暂无可用DLC")
        
        dlc_list = []
        for key, info in dlcs.items():
            # 获取所有可用的下载URL
            urls = self.source_manager.get_download_urls_for_dlc(key, info)
            
            dlc_list.append({
                "key": key,
                "name": info.get("name", key),
                "url": urls[0] if urls else "",  # 主URL
                "urls": urls,  # 所有可用URL，用于fallback
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
