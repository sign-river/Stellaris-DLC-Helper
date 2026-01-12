#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DLC管理模块
负责获取DLC列表、检查已安装的DLC
"""

import os
import json
import requests
from pathlib import Path
from ..config import STELLARIS_APP_ID, REQUEST_TIMEOUT
from ..utils import PathUtils


class DLCManager:
    """DLC管理类"""
    
    def __init__(self, game_path):
        """
        初始化DLC管理器
        
        参数:
            game_path: 游戏路径
        """
        self.game_path = game_path
        self.dlc_names = {}  # DLC名称映射表，从pairings.json动态加载
        self.game_version = None  # 游戏版本信息
        self._load_dlc_names()
    
    def _load_dlc_names(self):
        """从pairings.json加载DLC名称映射"""
        try:
            # 尝试从多个位置加载pairings.json
            base_dir = Path(__file__).parent.parent.parent
            pairings_paths = [
                base_dir / "pairings.json",
                Path(PathUtils.get_base_dir()) / "pairings.json"
            ]
            
            for path in pairings_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        # 读取映射：dlc001_symbols_of_domination.zip -> 001.zip
                        pairings = json.load(f)
                        
                        # 从文件名提取DLC名称
                        for full_name in pairings.keys():
                            if full_name.startswith('dlc') and '_' in full_name:
                                parts = full_name.replace('.zip', '').split('_', 1)
                                if len(parts) == 2:
                                    dlc_key = parts[0]  # dlc001
                                    name_part = parts[1]  # symbols_of_domination
                                    # 转换为可读名称
                                    readable_name = ' '.join(word.capitalize() for word in name_part.split('_'))
                                    self.dlc_names[dlc_key] = readable_name
                    break
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"加载DLC名称失败: {e}")
            self.dlc_names = {}
    
    def _get_dlc_name(self, dlc_key):
        """
        从DLC编号获取名称（从pairings.json动态提取）
        
        参数:
            dlc_key: DLC键名，如 'dlc001'
            
        返回:
            str: DLC名称
        """
        return self.dlc_names.get(dlc_key, dlc_key.replace('dlc', 'DLC '))
        
    def _fetch_from_gitlink_api(self):
        """
        从GitLink API获取DLC列表（主要方式）
        
        返回:
            list: DLC列表或None
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            api_url = "https://gitlink.org.cn/api/signriver/file-warehouse/releases.json"
            logger.info(f"正在从GitLink API获取DLC列表: {api_url}")
            
            response = requests.get(api_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            # 查找tag为"ste"的Release
            release = None
            for r in data.get("releases", []):
                if r.get("tag_name") == "ste":
                    release = r
                    break
            
            if not release:
                logger.warning("未找到tag为'ste'的Release")
                return None
            
            # 保存游戏版本信息（使用body字段）
            self.game_version = release.get('body', '未知版本').strip()
            
            # 构建DLC列表
            dlc_list = []
            for attachment in release.get("attachments", []):
                filename = attachment.get("title", "")
                if not filename.endswith(".zip"):
                    continue
                
                # 从文件名提取DLC编号：001.zip -> dlc001
                file_number = filename.replace(".zip", "")
                if not file_number.isdigit():
                    continue
                
                dlc_key = f"dlc{file_number}"
                
                # 从pairings.json动态获取名称
                dlc_name = self._get_dlc_name(dlc_key)
                
                # 构建完整URL
                base_url = "https://gitlink.org.cn"
                file_url = base_url + attachment.get("url", "")
                
                # 获取文件大小并格式化显示
                file_size_bytes = 0
                size_display = "未知"
                
                try:
                    size_str = attachment.get("filesize", "")
                    if size_str:
                        # GitLink API返回的是格式化字符串，如 "95.3 KB" 或 "28.5 MB"
                        import re
                        match = re.search(r'([\d.]+)\s*(B|KB|MB|GB)', str(size_str), re.IGNORECASE)
                        if match:
                            size_value = float(match.group(1))
                            unit = match.group(2).upper()
                            
                            # 转换为字节数
                            if unit == 'B':
                                file_size_bytes = int(size_value)
                            elif unit == 'KB':
                                file_size_bytes = int(size_value * 1024)
                            elif unit == 'MB':
                                file_size_bytes = int(size_value * 1024 * 1024)
                            elif unit == 'GB':
                                file_size_bytes = int(size_value * 1024 * 1024 * 1024)
                            
                            # 统一显示为MB（保留1位小数）
                            if file_size_bytes > 0:
                                size_mb = file_size_bytes / (1024 * 1024)
                                size_display = f"{size_mb:.1f} MB"
                except Exception as e:
                    logger.warning(f"解析文件大小失败 '{size_str}': {e}")
                    file_size_bytes = 0
                    size_display = "未知"
                
                dlc_list.append({
                    "key": dlc_key,
                    "name": dlc_name,
                    "url": file_url,
                    "source": "gitlink",
                    "size": size_display,  # 显示用的字符串
                    "size_bytes": file_size_bytes,  # 原始字节数
                    "number": int(file_number)  # 添加数字用于排序
                })
            
            # 按DLC编号排序（从小到大）
            dlc_list.sort(key=lambda x: x.get("number", 0))
            
            # 移除临时的number字段
            for dlc in dlc_list:
                dlc.pop("number", None)
            
            logger.info(f"✅ 从GitLink API成功获取 {len(dlc_list)} 个DLC（已排序）")
            return dlc_list
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"从GitLink API获取失败: {e}")
            return None
    
    def fetch_dlc_list(self):
        """
        获取DLC列表（从GitLink API）
        
        返回:
            list: DLC列表，每项包含 key, name, url, size
            
        抛出:
            Exception: 获取失败时抛出异常
        """
        import logging
        logger = logging.getLogger(__name__)
        
        dlc_list = self._fetch_from_gitlink_api()
        if dlc_list:
            return dlc_list
        
        raise Exception("无法获取DLC列表：GitLink API访问失败")
    
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
