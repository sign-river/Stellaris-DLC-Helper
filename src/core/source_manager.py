#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源下载管理模块
负责管理多个下载源的配置、优先级和切换逻辑
"""

import os
import requests
from typing import List, Dict, Any, Optional
from ..config import DLC_SOURCES, REQUEST_TIMEOUT, STELLARIS_APP_ID


class SourceManager:
    """多源管理器类"""
    
    def __init__(self):
        self.sources = self._load_sources()
        self.mappings = self._load_mappings()
    
    def _load_sources(self) -> List[Dict[str, Any]]:
        """加载并验证源配置"""
        sources = []
        for source in DLC_SOURCES:
            if source.get("enabled", False):
                sources.append(source)

        # 按优先级排序（数字越小优先级越高）
        sources.sort(key=lambda x: x.get("priority", 999))
        return sources
    
    def _load_mappings(self) -> Dict[str, Dict[str, str]]:
        """加载文件名映射配置"""
        mappings = {}
        for source in DLC_SOURCES:
            if source.get("enabled", False) and source.get("format") in ["github_release", "gitee_release"]:
                mapping_file = source.get("mapping_file")
                if mapping_file:
                    try:
                        import json
                        mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), mapping_file)
                        with open(mapping_path, 'r', encoding='utf-8') as f:
                            mappings[source.get("name")] = json.load(f)
                    except Exception as e:
                        print(f"警告: 无法加载映射文件 {mapping_file}: {e}")
        return mappings
    
    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        """获取所有启用的源"""
        return [s for s in self.sources if s.get("enabled", False)]

    def get_source_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取源配置"""
        for source in self.sources:
            if source.get("name") == name:
                return source
        return None

    def get_index_urls(self) -> List[str]:
        """获取所有源的index.json URL"""
        urls = []
        for source in self.sources:
            if source.get("enabled", False):
                base_url = source.get("url", "").rstrip("/")
                urls.append(f"{base_url}/index.json")
        return urls

    def fetch_dlc_data_from_source(self, source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从指定源获取DLC数据

        参数:
            source: 源配置字典

        返回:
            DLC数据字典或None（如果获取失败）
        """
        format_type = source.get("format", "standard")
        
        # 对于github_release和gitee_release格式，不需要获取index.json，直接返回成功
        # 因为DLC列表从其他源获取，这些只作为下载源
        if format_type in ["github_release", "gitee_release"]:
            print(f"{format_type.upper()}源 '{source.get('name')}' 配置成功（无需index.json）")
            return {STELLARIS_APP_ID: {"dlcs": {}}}
        
        try:
            base_url = source.get("url", "").rstrip("/")
            index_url = f"{base_url}/index.json"
            format_type = source.get("format", "standard")

            response = requests.get(index_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            # 根据格式类型处理数据
            if format_type == "standard":
                return self._process_standard_format(data, source)
            elif format_type == "gitee_release":
                return self._process_gitee_format(data, source)
            elif format_type == "custom":
                return self._process_custom_format(data, source)
            else:
                print(f"警告: 未知的格式类型 '{format_type}'，使用标准格式处理")
                return self._process_standard_format(data, source)

        except Exception as e:
            print(f"从源 '{source.get('name')}' 获取数据失败: {e}")
            return None

    def _process_standard_format(self, data: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """处理标准格式的DLC数据"""
        if STELLARIS_APP_ID not in data:
            return {}

        stellaris_data = data[STELLARIS_APP_ID]
        dlcs = stellaris_data.get("dlcs", {})

        # 为每个DLC添加源信息
        processed_dlcs = {}
        for key, info in dlcs.items():
            processed_dlcs[key] = {
                **info,
                "_source": source.get("name"),
                "_source_url": source.get("url")
            }

        return {STELLARIS_APP_ID: {"dlcs": processed_dlcs}}

    def _process_gitee_format(self, data: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """处理Gitee Release格式的DLC数据"""
        # TODO: 根据Gitee API格式实现
        # Gitee releases API 返回格式可能不同
        print(f"Gitee格式处理待实现: {source.get('name')}")
        return {}

    def _process_github_format(self, data: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """处理GitHub Release格式的DLC数据"""
        # TODO: 根据GitHub API格式实现
        # GitHub releases API 返回格式可能不同
        print(f"GitHub格式处理待实现: {source.get('name')}")
        return {}

    def _process_custom_format(self, data: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """处理自定义格式的DLC数据"""
        # TODO: 根据具体需求实现
        print(f"自定义格式处理待实现: {source.get('name')}")
        return {}

    def merge_dlc_data(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个源的DLC数据

        参数:
            data_list: 各源的DLC数据列表

        返回:
            合并后的DLC数据
        """
        merged = {STELLARIS_APP_ID: {"dlcs": {}}}

        for data in data_list:
            if not data or STELLARIS_APP_ID not in data:
                continue

            stellaris_data = data[STELLARIS_APP_ID]
            dlcs = stellaris_data.get("dlcs", {})

            for key, info in dlcs.items():
                if key not in merged[STELLARIS_APP_ID]["dlcs"]:
                    # 新DLC，直接添加
                    merged[STELLARIS_APP_ID]["dlcs"][key] = info
                else:
                    # 已存在的DLC，可以根据优先级或其他逻辑选择
                    existing = merged[STELLARIS_APP_ID]["dlcs"][key]
                    # TODO: 实现更复杂的合并逻辑，比如比较版本、优先级等
                    # 目前简单保留第一个找到的
                    pass

        return merged

    def get_download_urls_for_dlc(self, dlc_key: str, dlc_info: Dict[str, Any]) -> List[str]:
        """
        获取指定DLC的所有可用下载URL（按优先级排序）

        参数:
            dlc_key: DLC键名
            dlc_info: DLC信息字典

        返回:
            下载URL列表
        """
        urls = []

        # 为所有启用的源生成下载URL
        enabled_sources = self.get_enabled_sources()

        for source in enabled_sources:
            source_name = source.get("name")
            source_url = source.get("url", "").rstrip("/")
            format_type = source.get("format", "standard")

            if format_type == "standard":
                # 标准格式：直接使用DLC信息中的URL，但替换域名部分
                if "url" in dlc_info and dlc_info["url"]:
                    # 从原始URL中提取相对路径
                    original_url = dlc_info["url"]
                    # 替换基础URL部分
                    # 例如：https://dlc.dlchelper.top/dlc/281990/dlc001.zip -> http://47.100.2.190/dlc/281990/dlc001.zip
                    if original_url.startswith("https://dlc.dlchelper.top/dlc/"):
                        relative_path = original_url[len("https://dlc.dlchelper.top/dlc/"):]
                        new_url = f"{source_url}/{relative_path}"
                        if new_url not in urls:  # 避免重复
                            urls.append(new_url)
                    else:
                        # 如果不是标准R2 URL，直接使用原始URL（但只对当前源）
                        if source_name == dlc_info.get("_source"):
                            urls.append(original_url)
            elif format_type == "gitee_release":
                # Gitee release asset URL格式
                if source_name in self.mappings and "url" in dlc_info:
                    # 从原始URL中提取文件名
                    original_url = dlc_info["url"]
                    filename = original_url.split('/')[-1]  # 获取文件名，如 dlc001_symbols_of_domination.zip
                    
                    # 使用映射表查找对应的Gitee文件名
                    mapping = self.mappings[source_name]
                    if filename in mapping:
                        gitee_filename = mapping[filename]
                        
                        # 根据文件名中的编号选择正确的release tag
                        # 例如：001.zip -> 1, 034.zip -> 34
                        try:
                            file_num = int(gitee_filename.split('.')[0])  # 提取数字部分
                            releases = source.get("releases", {})
                            
                            # 找到匹配的release tag
                            selected_tag = None
                            for tag, range_info in releases.items():
                                min_num = range_info.get("min", 0)
                                max_num = range_info.get("max", 999)
                                if min_num <= file_num <= max_num:
                                    selected_tag = tag
                                    break
                            
                            if selected_tag:
                                gitee_url = f"{source_url}{selected_tag}/{gitee_filename}"
                                if gitee_url not in urls:
                                    urls.append(gitee_url)
                        except (ValueError, IndexError) as e:
                            print(f"警告: 无法解析Gitee文件名编号 {gitee_filename}: {e}")
            elif format_type == "github_release":
                # GitHub release asset URL格式
                if source_name in self.mappings and "url" in dlc_info:
                    # 从原始URL中提取文件名
                    original_url = dlc_info["url"]
                    filename = original_url.split('/')[-1]  # 获取文件名，如 dlc001_symbols_of_domination.zip
                    
                    # 使用映射表查找对应的GitHub文件名
                    mapping = self.mappings[source_name]
                    if filename in mapping:
                        github_filename = mapping[filename]
                        github_url = f"{source_url}/{github_filename}"
                        if github_url not in urls:
                            urls.append(github_url)
            elif format_type == "custom":
                # 自定义格式
                # TODO: 根据实际需求实现
                pass

        return urls