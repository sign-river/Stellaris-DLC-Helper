#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源下载管理模块
负责管理多个下载源的配置、优先级和切换逻辑
"""

import os
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
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
        for source in DLC_SOURCES:  # 加载所有源的映射，包括禁用的
            if source.get("format") in ["github_release", "gitee_release"]:
                mapping_file = source.get("mapping_file")
                if mapping_file:
                    try:
                        import json
                        mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), mapping_file)
                        with open(mapping_path, 'r', encoding='utf-8') as f:
                            mappings[source.get("name")] = json.load(f)
                    except Exception as e:
                        print(f"警告: 无法加载映射文件 {mapping_file}: {e}")
                        mappings[source.get("name")] = {}  # 空映射
        return mappings

    def get_sources_by_name(self) -> Dict[str, Dict[str, Any]]:
        """返回按名称索引的源配置映射（只包含启用的源）"""
        return {s.get("name"): s for s in self.sources}

    def get_source_base_url(self, source_name: str) -> str:
        """根据源名称返回其基础URL（去掉尾部斜杠）；未找到返回空字符串"""
        sources = self.get_sources_by_name()
        source = sources.get(source_name)
        return source.get("url", "").rstrip("/") if source else ""
    
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

    def get_url_for_source(self, dlc_key: str, dlc_info: Dict[str, Any], source_name: str) -> Optional[str]:
        """
        返回指定DLC在指定源下可用的下载URL（如果存在），否则返回 None
        """
        url_tuples = self.get_download_urls_for_dlc(dlc_key, dlc_info)
        for url, name in url_tuples:
            if name == source_name:
                return url
        return None

    def build_dlc_url_map(self, dlc_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        为一组 DLC 构建一个完整的 URL 映射表，格式:
        {
          dlc_key: {
             "name": name, "size": size, "sources": { source_name: url }
           }
        }
        """
        mapping = {}
        for dlc in dlc_list:
            key = dlc.get('key')
            if not key:
                continue
            sources_map = {}
            urls = self.get_download_urls_for_dlc(key, dlc)
            for url, name in urls:
                sources_map[name] = url
            mapping[key] = {
                'name': dlc.get('name', key),
                'size': dlc.get('size', '未知'),
                'sources': sources_map
            }
            # 复制 checksum 信息到映射表中，便于调试/校验
            if dlc.get('checksum'):
                mapping[key]['checksum'] = dlc.get('checksum')
        return mapping

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

    def get_download_urls_for_dlc(self, dlc_key: str, dlc_info: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        获取指定DLC的所有可用下载URL（按优先级排序）

        参数:
            dlc_key: DLC键名
            dlc_info: DLC信息字典

        返回:
            (URL, 源名称) 元组列表
        """
        urls = []

        # 按固定优先级顺序生成下载URL：R2 -> GitHub -> 国内云 -> Gitee
        priority_order = ["r2", "github", "domestic_cloud", "gitee"]
        
        # 获取所有源配置（包括禁用的）
        sources_by_name = {source.get("name"): source for source in DLC_SOURCES}
        
        for source_name in priority_order:
            if source_name in sources_by_name:
                source = sources_by_name[source_name]
                source_url = source.get("url", "").rstrip("/")
                format_type = source.get("format", "standard")
            else:
                # 忽略未配置的源
                continue

            if format_type == "standard":
                # 标准格式：从国内服务器URL生成对应源的URL
                if "url" in dlc_info and dlc_info["url"]:
                    original_url = dlc_info["url"].rstrip("/")

                    # 尝试将已知的国内服务器基址（配置里的 domestic_cloud）替换为目标源基址
                    domestic_base = None
                    for s in DLC_SOURCES:
                        if s.get("name") == "domestic_cloud":
                            domestic_base = s.get("url", "").rstrip("/")
                            break

                    if domestic_base and original_url.startswith(domestic_base):
                        relative_path = original_url[len(domestic_base):].lstrip('/')
                        new_url = f"{source_url}/{relative_path}"
                        if new_url not in [url for url, _ in urls]:
                            urls.append((new_url, source_name))
                    # 如果原始 URL 就属于当前源，直接使用（例如该 DLC 本来来自 R2）
                    elif source_name == dlc_info.get("_source"):
                        if original_url not in [url for url, _ in urls]:
                            urls.append((original_url, source_name))
            elif format_type == "gitee_release":
                # Gitee release asset URL格式
                if "url" in dlc_info:
                    # 从原始URL中提取文件名
                    original_url = dlc_info["url"]
                    filename = original_url.split('/')[-1]  # 获取文件名，如 dlc001_symbols_of_domination.zip
                    
                    # 尝试使用映射表查找对应的Gitee文件名
                    mapping = self.mappings.get(source_name, {})
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
                                gitee_url = f"{source_url}/{selected_tag}/{gitee_filename}"
                                if gitee_url not in [url for url, _ in urls]:
                                    urls.append((gitee_url, source_name))
                        except (ValueError, IndexError) as e:
                            print(f"警告: 无法解析Gitee文件名编号 {gitee_filename}: {e}")
            elif format_type == "github_release":
                # GitHub release asset URL格式
                if "url" in dlc_info:
                    # 从原始URL中提取文件名
                    original_url = dlc_info["url"]
                    filename = original_url.split('/')[-1]  # 获取文件名，如 dlc001_symbols_of_domination.zip
                    
                    # 尝试使用映射表查找对应的GitHub文件名
                    mapping = self.mappings.get(source_name, {})
                    if filename in mapping:
                        github_filename = mapping[filename]
                        github_url = f"{source_url}/{github_filename}"
                        if github_url not in [url for url, _ in urls]:
                            urls.append((github_url, source_name))
            elif format_type == "custom":
                # 自定义格式
                # TODO: 根据实际需求实现
                pass

        return urls

    def measure_speed(self, url, description, threshold_mb, log_callback=None):
        """
        测速单个URL
        
        参数:
            url: 测试URL
            description: 描述信息
            threshold_mb: 速度阈值(MB/s)
            log_callback: 日志回调函数，用于输出到GUI
            
        返回:
            tuple: (是否达标, 速度MB/s)
        """
        silent = getattr(self, '_silent_mode', False)
        
        # 总是显示测试开始信息（如果有log_callback）
        if log_callback:
            log_callback(f"正在测试 [{description}] ...")
        elif not silent:
            print(f"正在测试 [{description}] ...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # 请求 200MB 数据
            "Range": "bytes=0-209715199" 
        }

        try:
            # 连接 3s 超时，读取 8s 超时
            with requests.get(url, headers=headers, stream=True, timeout=(3.0, 8.0)) as response:
                # 1. 检查状态码
                if not response.ok:
                    message = f"测试 [{description}] 失败: 服务器返回状态码 {response.status_code}"
                    if log_callback:
                        log_callback(message)
                    elif not silent:
                        print(f"   [X] 失败: 服务器返回状态码 {response.status_code}")
                    return False, 0.0

                # 2. 检查 Content-Length (诊断文件是否变小了)
                content_length = response.headers.get('Content-Length')
                if content_length:
                    mb_size = int(content_length) / 1024 / 1024
                    message = f"[{description}] 服务器响应大小: {mb_size:.2f} MB"
                    if log_callback:
                        log_callback(message)
                    elif not silent:
                        print(f"   [i] 服务器响应大小: {mb_size:.2f} MB")
                elif not silent:
                    message = f"[{description}] 服务器未返回文件大小 (可能是分块传输)"
                    if log_callback:
                        log_callback(message)
                    elif not silent:
                        print(f"   [i] 服务器未返回文件大小 (可能是分块传输)")

                total_downloaded = 0
                start_time = time.time()
                first_chunk = True
                
                # 3. 开始下载循环
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk: break
                    
                    if first_chunk:
                        first_chunk = False
                        start_time = time.time() # 真正的计时开始
                        continue

                    total_downloaded += len(chunk)
                    
                    current_time = time.time()
                    duration = current_time - start_time
                    
                    # --- 停止条件诊断 ---
                    if duration >= 5.0:
                        message = f"[{description}] 测速完成: 满 5 秒时间到"
                        if log_callback:
                            log_callback(message)
                        elif not silent:
                            print("   [√] 停止原因: 满 5 秒时间到")
                        break
                    
                    if total_downloaded >= 70 * 1024 * 1024:
                        message = f"[{description}] 测速完成: 速度太快 (超过70MB)"
                        if log_callback:
                            log_callback(message)
                        elif not silent:
                            print("   [√] 停止原因: 速度太快 (超过70MB)")
                        break
                else:
                    # 如果循环自然结束（即文件读完了，也没触发 break）
                    message = f"[{description}] 测速完成: 文件被下载完了 (文件太小?)"
                    if log_callback:
                        log_callback(message)
                    elif not silent:
                        print("   [!] 停止原因: 文件被下载完了 (文件太小?)")

                # 4. 计算结果
                final_duration = time.time() - start_time
                if final_duration <= 0.001: final_duration = 0.001

                speed_mb = (total_downloaded / 1024 / 1024) / final_duration
                
                # 总是显示测速结果（如果有log_callback）
                message1 = f"[{description}] 耗时: {final_duration:.2f}秒 | 下载量: {total_downloaded/1024/1024:.2f} MB"
                message2 = f"[{description}] 最终速度: {speed_mb:.2f} MB/s"
                if log_callback:
                    log_callback(message1)
                    log_callback(message2)
                elif not silent:
                    print(f"   [i] 耗时: {final_duration:.2f}秒 | 下载量: {total_downloaded/1024/1024:.2f} MB")
                    print(f"   >>> 最终速度: {speed_mb:.2f} MB/s", end="")
                
                if speed_mb > threshold_mb:
                    message = f"[{description}] 达标 (>{threshold_mb} MB/s)"
                    if log_callback:
                        log_callback(message)
                    elif not silent:
                        print(f" -> 达标 (>{threshold_mb} MB/s)\n")
                    return True, speed_mb
                else:
                    message = f"[{description}] 未达标 (<={threshold_mb} MB/s)"
                    if log_callback:
                        log_callback(message)
                    elif not silent:
                        print(" -> 未达标\n")
                    return False, speed_mb

        except requests.exceptions.ConnectTimeout:
            message = f"[{description}] 连接超时 (3秒内未连上)"
            if log_callback:
                log_callback(message)
            elif not silent:
                print("   [X] 连接超时 (3秒内未连上)\n")
            return False, 0.0
        except Exception as e:
            message = f"[{description}] 发生错误: {e}"
            if log_callback:
                log_callback(message)
            elif not silent:
                print(f"   [X] 发生错误: {e}\n")
            return False, 0.0

    def get_best_download_source(self, silent=False, log_callback=None):
        """
        测速选择最佳下载源
        
        参数:
            silent: 是否静默模式（不输出到控制台）
            log_callback: 日志回调函数，用于输出到GUI
            
        返回:
            tuple: (最佳源名称, 测试URL) 或 (None, None) 如果全部失败
        """
        # 设置静默模式
        self._silent_mode = silent
        
        # 获取启用源的配置（按名称索引）
        sources_by_name = {source.get("name"): source for source in DLC_SOURCES}
        # 获取测试 URL：优先使用源配置中的 test_url，若未配置则使用默认固定路径
        test_candidates = {}
        for source in DLC_SOURCES:
            if not source.get("enabled", False):
                continue
            name = source.get("name")
            # Use only the explicit test_url if present, otherwise fallback to fixed default
            candidates = []
            if source.get('test_url'):
                candidates.append(source.get('test_url'))
            else:
                base = source.get("url", "").rstrip('/')
                fmt = source.get('format', 'standard')
                # Default per-source fixed test paths
                if name == 'r2':
                    candidates.append(f"{base}/test/test2.bin")
                elif name == 'domestic_cloud':
                    candidates.append(f"{base}/test/test.bin")
                elif fmt in ['github_release', 'gitee_release']:
                    # For release sources without a configured test_url, try a single logical default
                    # NOTE: We do not attempt multiple URL patterns; the user requested fixed test paths
                    # We'll use a safe form combining prefix + 'test/test.bin'
                    if '/releases/download/' in base:
                        # drop any tag and use tag 'test'
                        parts = base.split('/releases/download/')
                        prefix = parts[0] + '/releases/download/'
                        candidates.append(f"{prefix}test/test.bin")
                    else:
                        candidates.append(f"{base}/test/test.bin")
                else:
                    candidates.append(f"{base}/test/test.bin")

            # 去重并过滤空项
            seen = set()
            filtered = []
            for c in candidates:
                if c and c not in seen:
                    seen.add(c)
                    filtered.append(c)
            test_candidates[name] = filtered

        if not silent:
            message = "开始测速选择最佳下载源..."
            print("=" * 40)
            print(message)
            print("=" * 40)
            if log_callback:
                log_callback(message)
        elif log_callback:
            # 即使silent，也要在GUI中显示开始信息
            log_callback("开始测速选择最佳下载源...")
        
        # 按优先级顺序测试（与get_download_urls_for_dlc保持一致）
        priority_order = ["r2", "github", "domestic_cloud", "gitee"]
        
        for source_name in priority_order:
            if source_name in test_candidates:
                candidates = test_candidates[source_name]
                threshold = 3.0 if source_name in ["r2", "domestic_cloud"] else 2.0
                # 允许从源配置中覆盖阈值
                cfg = sources_by_name.get(source_name) if 'sources_by_name' in locals() else None
                if cfg and cfg.get('threshold_mb'):
                    threshold = cfg.get('threshold_mb')
                # 逐个 candidate 测试
                for candidate in candidates:
                    ok, speed = self.measure_speed(candidate, f"{source_name}", threshold, log_callback)
                    if ok:
                        if not silent:
                            message = f"选择下载源: {source_name} (速度: {speed:.2f} MB/s) -> {candidate}"
                            print(message)
                            if log_callback:
                                log_callback(message)
                        elif log_callback:
                            log_callback(f"选择下载源: {source_name} (速度: {speed:.2f} MB/s) -> {candidate}")
                        return source_name, candidate
                    # 如果不达标则继续测试下一个 candidate
                    continue

        if not silent:
            message = "所有源测速均未达标，使用默认源"
            print("-" * 40)
            print(message)
            if log_callback:
                log_callback(message)
        elif log_callback:
            # 即使silent，也要在GUI中显示默认源信息
            log_callback("所有源测速均未达标，使用默认源")
        # 所有候选都未达标，返回默认的 test url（优先取配置中定义的候选）
        default_candidates = test_candidates.get("domestic_cloud", [])
        default_url = default_candidates[0] if default_candidates else "http://47.100.2.190/dlc/test/test.bin"
        return "domestic_cloud", default_url