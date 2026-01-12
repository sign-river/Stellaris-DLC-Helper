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
        self.dlc_names = {}  # DLC名称映射表，从pairings.json动态加载
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
                
                # 获取所有源的下载URL
                url_tuples = self.source_manager.get_download_urls_for_dlc(
                    dlc_key, 
                    {"name": dlc_name, "size": attachment.get("filesize", "未知")}
                )
                
                # 分离主URL和备用URL
                if url_tuples:
                    main_url = url_tuples[0][0]
                    main_source = url_tuples[0][1]
                    fallback_urls = url_tuples[1:]
                else:
                    main_url = file_url
                    main_source = "gitlink"
                    fallback_urls = []
                
                dlc_list.append({
                    "key": dlc_key,
                    "name": dlc_name,
                    "url": main_url,
                    "source": main_source,
                    "fallback_urls": fallback_urls,
                    "size": attachment.get("filesize", "未知")
                })
            
            logger.info(f"✅ 从GitLink API成功获取 {len(dlc_list)} 个DLC")
            return dlc_list
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"从GitLink API获取失败: {e}")
            return None
    
    def _fetch_from_index_json(self):
        """
        从index.json获取DLC列表（备用方式）
        
        返回:
            list: DLC列表或None
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("使用备用方式：从index.json获取DLC列表")
            
            domestic_source = self.source_manager.get_source_by_name("domestic_cloud")
            if not domestic_source:
                logger.warning("未找到国内云服务器配置")
                return None
            
            data = self.source_manager.fetch_dlc_data_from_source(domestic_source)
            if not data:
                return None
            
            if STELLARIS_APP_ID not in data:
                return None
            
            stellaris_data = data[STELLARIS_APP_ID]
            dlcs = stellaris_data.get("dlcs", {})
            
            if not dlcs:
                return None
            
            dlc_list = []
            for key, info in dlcs.items():
                url_tuples = self.source_manager.get_download_urls_for_dlc(key, info)
                
                if url_tuples:
                    main_url = url_tuples[0][0]
                    main_source = url_tuples[0][1]
                    fallback_urls = url_tuples[1:]
                else:
                    main_url = ""
                    main_source = "unknown"
                    fallback_urls = []
                
                dlc_list.append({
                    "key": key,
                    "name": info.get("name", key),
                    "url": main_url,
                    "source": main_source,
                    "fallback_urls": fallback_urls,
                    "size": info.get("size", "未知")
                })
            
            logger.info(f"✅ 从index.json成功获取 {len(dlc_list)} 个DLC")
            return dlc_list
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"从index.json获取失败: {e}")
            return None
    
    def fetch_dlc_list(self):
        """
        获取DLC列表（优先使用GitLink API，失败时使用index.json）
        
        返回:
            list: DLC列表，每项包含 key, name, url, size
            
        抛出:
            Exception: 所有方式都失败时抛出异常
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 方式1：优先使用GitLink API
        dlc_list = self._fetch_from_gitlink_api()
        if dlc_list:
            return dlc_list
        
        # 方式2：备用index.json
        dlc_list = self._fetch_from_index_json()
        if dlc_list:
            return dlc_list
        
        # 所有方式都失败
        raise Exception("无法获取DLC列表：GitLink API和index.json都失败了")
    
    def _original_fetch_dlc_list(self):
        """
        从国内服务器获取DLC列表
        
        返回:
            list: DLC列表，每项包含 key, name, url, size
            
        抛出:
            Exception: 网络错误或数据格式错误
        """
        import logging
        # 打印当前 SourceManager 的 sources（DEBUG级别）以便排查运行时的源配置
        logging.getLogger().debug(f"SourceManager.sources: {self.source_manager.sources}")
        # 只从国内服务器获取DLC列表
        domestic_source = self.source_manager.get_source_by_name("domestic_cloud")
        # 记录 domestic_source 的值以帮助调试（DEBUG级别）
        logging.getLogger().debug(f"domestic_source: {domestic_source}")
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
                main_source = url_tuples[0][1]  # 主URL对应的源
                fallback_urls = url_tuples[1:]  # 备用URL元组列表
            else:
                main_url = ""
                main_source = "unknown"
                fallback_urls = []
            
            dlc_list.append({
                "key": key,
                "name": info.get("name", key),
                "url": main_url,  # 主URL
                "source": main_source,  # 主URL对应的源名称
                "urls": fallback_urls,  # 备用URL元组列表，用于fallback
                "size": info.get("size", "未知"),
                "checksum": info.get("checksum") or info.get("sha256") or info.get("hash"),
                "_original_source": info.get("_source", "unknown")  # 原始源信息
            })
        
        # 按DLC编号排序
        dlc_list.sort(key=self._extract_dlc_number)
        # 构建 URL 映射表并写入缓存，便于调试
        try:
            url_map = self.source_manager.build_dlc_url_map(dlc_list)
            from ..utils import PathUtils
            import json
            cache_path = PathUtils.get_cache_dir()
            import os
            os.makedirs(cache_path, exist_ok=True)
            with open(os.path.join(cache_path, 'dlc_urls.json'), 'w', encoding='utf-8') as f:
                json.dump(url_map, f, ensure_ascii=False, indent=2)
            # 将 url_map 每个DLC的sources字典嵌入到对应 dlc_list 项
            for dlc in dlc_list:
                k = dlc.get('key')
                if k in url_map:
                    # 只将 sources 映射嵌入到每个 dlc，便于 UI 直接遍历 source->url
                    dlc['url_map'] = url_map[k].get('sources', {})
        except Exception:
            pass
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
