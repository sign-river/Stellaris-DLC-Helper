#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源下载管理模块
负责管理多个下载源的配置、优先级和切换逻辑
"""

import os
import time
import requests
import sys
from typing import List, Dict, Any, Optional, Tuple
from ..config import DLC_SOURCES, REQUEST_TIMEOUT, STELLARIS_APP_ID


class SourceManager:
    """多源管理器类"""
    
    def __init__(self):
        self.sources = self._load_sources()
        self.mappings = self._load_mappings()
        # 测速结果缓存：{source_name: (speed_mb, timestamp)}
        self._speed_cache = {}
        self._cache_validity = 300  # 缓存有效期5分钟
        self._last_best_source = None  # 上次选择的最佳源
        self._last_best_timestamp = 0  # 上次选择的时间
    
    def _load_sources(self) -> List[Dict[str, Any]]:
        """加载并验证源配置"""
        sources = []
        for source in DLC_SOURCES:
            if source.get("enabled", False):
                sources.append(source)

        # 按优先级排序（数字越小优先级越高）
        sources.sort(key=lambda x: x.get("priority", 999))
        return sources
    
    def _get_test_url_for_source(self, source_name: str, sources_by_name: Dict[str, Any]) -> Tuple[str, str]:
        """
        获取指定源的测试URL
        
        参数:
            source_name: 源名称
            sources_by_name: 源配置字典
            
        返回:
            tuple: (源名称, 测试URL)
        """
        source = sources_by_name.get(source_name)
        if not source:
            return source_name, ""
        
        # 使用与 get_best_download_source 相同的逻辑获取测试URL
        if source.get('test_url'):
            return source_name, source.get('test_url')
        
        base = source.get("url", "").rstrip('/')
        fmt = source.get('format', 'standard')
        
        # 默认固定测试路径
        if source_name == 'r2':
            return source_name, f"{base}/test/test2.bin"
        elif source_name == 'domestic_cloud':
            return source_name, f"{base}/test/test.bin"
        elif fmt in ['github_release', 'gitee_release']:
            if '/releases/download/' in base:
                parts = base.split('/releases/download/')
                prefix = parts[0] + '/releases/download/'
                return source_name, f"{prefix}test/test.bin"
            else:
                return source_name, f"{base}/test/test.bin"
        else:
            return source_name, f"{base}/test/test.bin"
    
    def _load_mappings(self) -> Dict[str, Dict[str, str]]:
        """加载文件名映射配置"""
        mappings = {}
        for source in DLC_SOURCES:  # 加载所有源的映射，包括禁用的
            if source.get("format") in ["github_release", "gitee_release"]:
                mapping_file = source.get("mapping_file")
                if mapping_file:
                    try:
                        import json
                        # 查找映射文件的候选路径，兼容开发模式和打包后的EXE
                        candidates = []
                        # 1. 当前工作目录
                        candidates.append(os.path.join(os.getcwd(), mapping_file))
                        # 2. 可执行文件所在目录
                        try:
                            exe_dir = os.path.dirname(sys.executable)
                            candidates.append(os.path.join(exe_dir, mapping_file))
                        except Exception:
                            pass
                        # 3. 模块文件目录的上级目录
                        try:
                            module_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                            candidates.append(os.path.join(module_dir, mapping_file))
                        except Exception:
                            pass
                        # 4. PyInstaller临时目录
                        meipass = getattr(sys, "_MEIPASS", None)
                        if meipass:
                            candidates.append(os.path.join(meipass, mapping_file))
                        
                        mapping_path = None
                        for candidate in candidates:
                            if os.path.exists(candidate):
                                mapping_path = candidate
                                break
                        
                        if mapping_path:
                            with open(mapping_path, 'r', encoding='utf-8') as f:
                                mappings[source.get("name")] = json.load(f)
                        else:
                            print(f"警告: 无法找到映射文件 {mapping_file}")
                            mappings[source.get("name")] = {}  # 空映射
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
        # 先获取当前所有可用源（包含禁用? - 这里使用启用的源以避免显示不需要的源）
        enabled_sources = self.get_enabled_sources()
        enabled_names = [s.get('name') for s in enabled_sources]

        for dlc in dlc_list:
            key = dlc.get('key')
            if not key:
                continue
            sources_map = {}
            # 为每个启用的源尝试获取 URL（如果可用），这样映射会明确包含 r2/domestic_cloud 等
            for s_name in enabled_names:
                try:
                    url = self.get_url_for_source(key, dlc, s_name)
                    if url:
                        sources_map[s_name] = url
                    else:
                        sources_map[s_name] = None
                except Exception:
                    sources_map[s_name] = None
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
                # 标准格式：从任一已知基址生成对应源的 URL（R2/domestic/其他）
                if "url" in dlc_info and dlc_info["url"]:
                    original_url = dlc_info["url"].rstrip("/")

                    # 尝试抽取相对路径（例如 '281990/dlc001...') 基于 '/dlc/' 路径段
                    relative_path = None
                    try:
                        # look for '/dlc/' marker and take everything after it
                        idx = original_url.find('/dlc/')
                        if idx >= 0:
                            relative_path = original_url[idx + len('/dlc/'):]
                        else:
                            # fallback: if original_url startswith source_url and contains '/281990/' pattern
                            # try to find '/281990/' and extract after it
                            import re
                            m = re.search(r'/\d{6,}/', original_url)
                            if m:
                                relative_path = original_url[m.start() + 1:]
                    except Exception:
                        relative_path = None

                    if relative_path:
                        new_url = f"{source_url}/{relative_path}"
                        if new_url not in [u for u, _ in urls]:
                            urls.append((new_url, source_name))
                    else:
                        # 如果没有找到相对路径，但当前源就是原始源，则直接使用原始 URL
                        if source_name == dlc_info.get("_source"):
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

    def measure_speed(self, url, description, threshold_mb, log_callback=None, max_seconds: float = 10.0, max_bytes: int = 100 * 1024 * 1024):
        """
        测速单个URL - 通过实际下载测试真实速度
        
        参数:
            url: 测试URL
            description: 描述信息
            threshold_mb: 速度阈值(MB/s)
            log_callback: 日志回调函数，用于输出到GUI
            max_seconds: 最大测试时间（秒），默认10秒以获取准确速度
            max_bytes: 最大下载字节数，默认100MB
            
        返回:
            tuple: (是否达标, 速度MB/s)
        """
        silent = getattr(self, '_silent_mode', False)
        
        # 总是显示测试开始信息（如果有log_callback）
        if log_callback:
            log_callback(f"━━━━ 开始测试 [{description}] ━━━━")
        elif not silent:
            print(f"正在测试 [{description}] ...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # 请求 200MB 数据
            "Range": "bytes=0-209715199" 
        }

        try:
            # 连接 5s 超时，读取 15s 超时（给足时间进行准确测速）
            with requests.get(url, headers=headers, stream=True, timeout=(5.0, 15.0)) as response:
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
                last_report_time = time.time()
                report_interval = 2.0  # 每2秒报告一次当前速度
                
                # 3. 开始下载循环
                total_read = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk: break
                    
                    if first_chunk:
                        first_chunk = False
                        start_time = time.time() # 真正的计时开始
                        last_report_time = start_time
                        continue

                    total_downloaded += len(chunk)
                    
                    current_time = time.time()
                    duration = current_time - start_time
                    
                    # 每2秒输出一次实时速度
                    if current_time - last_report_time >= report_interval:
                        current_speed = (total_downloaded / 1024 / 1024) / duration
                        progress_msg = f"[{description}] 测速中... {duration:.1f}秒 | 已下载: {total_downloaded/1024/1024:.2f} MB | 当前速度: {current_speed:.2f} MB/s"
                        if log_callback:
                            log_callback(progress_msg)
                        elif not silent:
                            print(f"   {progress_msg}")
                        last_report_time = current_time
                    
                    # --- 停止条件 ---
                    if duration >= max_seconds:
                        message = f"[{description}] 测速完成 (达到 {max_seconds:.0f} 秒时间限制)"
                        if log_callback:
                            log_callback(message)
                        elif not silent:
                            print(f"   [√] 停止原因: 满 {max_seconds:.0f} 秒时间到")
                        break
                    
                    total_read += len(chunk)
                    if total_downloaded >= max_bytes or total_read >= max_bytes:
                        message = f"[{description}] 测速完成 (达到 {max_bytes/1024/1024:.0f}MB 数据限制)"
                        if log_callback:
                            log_callback(message)
                        elif not silent:
                            print(f"   [√] 停止原因: 速度太快 (超过{max_bytes/1024/1024:.0f}MB)")
                        break
                else:
                    # 如果循环自然结束（即文件读完了，也没触发 break）
                    message = f"[{description}] 测速完成 (文件已下载完)"
                    if log_callback:
                        log_callback(message)
                    elif not silent:
                        print("   [!] 停止原因: 文件被下载完了")

                # 4. 计算结果
                final_duration = time.time() - start_time
                if final_duration <= 0.001: final_duration = 0.001

                speed_mb = (total_downloaded / 1024 / 1024) / final_duration
                
                # 总是显示测速结果（如果有log_callback）
                result_line = "━" * 50
                message1 = f"[{description}] 测试完成"
                message2 = f"  ⏱ 测试时长: {final_duration:.2f}秒"
                message3 = f"  📦 下载数据: {total_downloaded/1024/1024:.2f} MB"
                message4 = f"  🚀 平均速度: {speed_mb:.2f} MB/s"
                
                # 阈值为-1时（Gitee保底源），只记录速度不做判断
                if threshold_mb < 0:
                    status_msg = f"  ℹ️ 保底源: 已记录速度"
                    result = True
                elif speed_mb > threshold_mb:
                    status_msg = f"  ✅ 结果: 速度达标 (阈值: {threshold_mb:.1f} MB/s)"
                    result = True
                else:
                    status_msg = f"  ❌ 结果: 速度未达标 (阈值: {threshold_mb:.1f} MB/s)"
                    result = False
                
                if log_callback:
                    log_callback(result_line)
                    log_callback(message1)
                    log_callback(message2)
                    log_callback(message3)
                    log_callback(message4)
                    log_callback(status_msg)
                    log_callback(result_line)
                elif not silent:
                    print(f"\n   {message1}")
                    print(f"   {message2}")
                    print(f"   {message3}")
                    print(f"   {message4}")
                    print(f"   {status_msg}\n")
                
                return result, speed_mb

        except requests.exceptions.ConnectTimeout:
            message = f"❌ [{description}] 连接超时 (5秒内未连上)"
            if log_callback:
                log_callback(message)
            elif not silent:
                print("   [X] 连接超时 (5秒内未连上)\n")
            return False, 0.0
        except requests.exceptions.ReadTimeout:
            message = f"❌ [{description}] 读取超时 (网络传输中断)"
            if log_callback:
                log_callback(message)
            elif not silent:
                print("   [X] 读取超时\n")
            return False, 0.0
        except Exception as e:
            message = f"❌ [{description}] 测试失败: {str(e)[:100]}"
            if log_callback:
                log_callback(message)
            elif not silent:
                print(f"   [X] 发生错误: {e}\n")
            return False, 0.0

    def get_best_download_source(self, silent=False, log_callback=None, force_retest=False):
        """
        测速选择最佳下载源（带智能缓存）
        
        参数:
            silent: 是否静默模式（不输出到控制台）
            log_callback: 日志回调函数，用于输出到GUI
            force_retest: 是否强制重新测速（忽略缓存）
            
        返回:
            tuple: (最佳源名称, 测试URL) 或 (None, None) 如果全部失败
        """
        current_time = time.time()
        
        # 检查缓存：如果上次测速在5分钟内且不强制重测，直接使用缓存结果
        if not force_retest and self._last_best_source:
            cache_age = current_time - self._last_best_timestamp
            if cache_age < self._cache_validity:
                remaining_time = int(self._cache_validity - cache_age)
                if log_callback:
                    log_callback(f"⚡ 使用缓存的测速结果: {self._last_best_source} (缓存剩余 {remaining_time}秒)")
                elif not silent:
                    print(f"使用缓存的测速结果: {self._last_best_source}")
                
                # 返回缓存的最佳源和对应的测试URL
                sources_by_name = {source.get("name"): source for source in DLC_SOURCES}
                return self._get_test_url_for_source(self._last_best_source, sources_by_name)
        
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
        
        # 存储所有测速结果，用于找到最优源和保底源
        test_results = {}  # {source_name: (speed_mb, candidate_url)}
        domestic_cloud_data = None  # 国内云数据用于默认源
        gitee_data = None  # Gitee数据用于保底源
        
        for source_name in priority_order:
            if source_name in test_candidates:
                candidates = test_candidates[source_name]
                
                # 阈值设计理念：
                # - R2/GitHub：高阈值(2.5 MB/s) → 筛选有梯子的用户
                # - 国内云：高阈值(3.0 MB/s) → 避免拥挤时段的慢速
                # - Gitee：保留测速显示，但不参与正常选择（作为保底源）
                if source_name in ["r2", "github"]:
                    threshold = 2.5  # 筛选：有梯子的用户才用
                elif source_name == "domestic_cloud":
                    threshold = 3.0  # 高要求：避开拥挤
                else:  # gitee - 测速但不参与选择
                    threshold = -1  # 不进行阈值判断，只记录速度
                
                # 允许从源配置中覆盖阈值
                cfg = sources_by_name.get(source_name) if 'sources_by_name' in locals() else None
                if cfg and cfg.get('threshold_mb') and threshold >= 0:
                    threshold = cfg.get('threshold_mb')
                
                # 逐个 candidate 测试
                for candidate in candidates:
                    # Gitee不需要阈值判断，直接测速
                    if source_name == "gitee":
                        ok, speed = self.measure_speed(candidate, source_name, -1, log_callback)
                        self._speed_cache[source_name] = (speed, time.time())
                        gitee_data = (speed, candidate)
                    else:
                        ok, speed = self.measure_speed(candidate, source_name, threshold, log_callback)
                        self._speed_cache[source_name] = (speed, time.time())
                        
                        # 记录国内云数据用于默认源
                        if source_name == "domestic_cloud":
                            domestic_cloud_data = (speed, candidate)
                        
                        # 记录达标的源
                        if ok:
                            test_results[source_name] = (speed, candidate)
        
        # 选源逻辑：三层选择
        # 第一层：选择达标的源中速度最快的
        if test_results:
            best_source = max(test_results.items(), key=lambda x: x[1][0])
            source_name = best_source[0]
            speed, candidate = best_source[1]
            
            # 更新最佳源缓存
            self._last_best_source = source_name
            self._last_best_timestamp = time.time()
            
            if not silent:
                message = f"✅ 选择下载源: {source_name} (平均速度: {speed:.2f} MB/s)"
                print(message)
                if log_callback:
                    log_callback(message)
            elif log_callback:
                log_callback(f"✅ 选择下载源: {source_name} (平均速度: {speed:.2f} MB/s)")
            return source_name, candidate
        
        # 第二层：都不达标，使用默认源（国内云）
        if domestic_cloud_data:
            speed, candidate = domestic_cloud_data
            self._last_best_source = "domestic_cloud"
            self._last_best_timestamp = time.time()
            
            if not silent:
                message = f"⚠️ 所有源未达标，使用默认源: domestic_cloud (测速: {speed:.2f} MB/s)"
                print("-" * 40)
                print(message)
                if log_callback:
                    log_callback(message)
            elif log_callback:
                log_callback(f"⚠️ 使用默认源: domestic_cloud (测速: {speed:.2f} MB/s)")
            return "domestic_cloud", candidate
        
        # 第三层：连默认源都没测到（极少见），使用保底源（Gitee）
        if gitee_data:
            speed, candidate = gitee_data
            self._last_best_source = "gitee"
            self._last_best_timestamp = time.time()
            
            if not silent:
                message = f"⚠️ 默认源测速失败，使用保底源: gitee (测速: {speed:.2f} MB/s)"
                print("-" * 40)
                print(message)
                if log_callback:
                    log_callback(message)
            elif log_callback:
                log_callback(f"⚠️ 使用保底源: gitee (测速: {speed:.2f} MB/s)")
            return "gitee", candidate
        
        # 极端情况：所有源都无法测速，使用硬编码的保底URL
        if not silent:
            message = "❌ 所有源测速失败，使用硬编码保底URL"
            print("-" * 40)
            print(message)
            if log_callback:
                log_callback(message)
        elif log_callback:
            log_callback("❌ 所有源测速失败，使用硬编码保底URL")
        
        default_candidates = test_candidates.get("gitee", [])
        default_url = default_candidates[0] if default_candidates else "https://gitee.com/sign-river/Stellaris-DLC-Helper/releases/download/v1.0.0/test.bin"
        return "gitee", default_url

    def find_first_source_above(self, required_speed_mb: float, exclude: Optional[List[str]] = None, silent=False, log_callback=None, max_seconds: float = 2.0, max_bytes: int = 2 * 1024 * 1024) -> Optional[Tuple[str, str, float]]:
        """
        快速检测（轻量）其他源，返回第一个测速速度 > required_speed_mb 的源及测速 URL和速度

        参数:
            required_speed_mb: 需要超过的速度阈值（MB/s）
            exclude: 排除的源名称列表
            max_seconds: 单次测速最大秒数（默认 2s）
            max_bytes: 单次测速最大字节数（默认 2MB）
        返回:
            tuple: (source_name, test_url, speed_mb) 或 None
        """
        self._silent_mode = silent
        exclude = exclude or []
        sources_by_name = {source.get("name"): source for source in DLC_SOURCES}
        priority_order = ["r2", "github", "domestic_cloud", "gitee"]
        for source_name in priority_order:
            if source_name in exclude:
                continue
            source = sources_by_name.get(source_name)
            if not source or not source.get('enabled', False):
                continue
            # build candidate list - in our config we expect test_url
            candidates = []
            if source.get('test_url'):
                candidates.append(source.get('test_url'))
            else:
                base = source.get('url', '').rstrip('/')
                fmt = source.get('format', 'standard')
                if source_name == 'r2':
                    candidates.append(f"{base}/test/test2.bin")
                elif source_name == 'domestic_cloud':
                    candidates.append(f"{base}/test/test.bin")
                elif fmt in ['github_release', 'gitee_release']:
                    if '/releases/download/' in base:
                        parts = base.split('/releases/download/')
                        prefix = parts[0] + '/releases/download/'
                        candidates.append(f"{prefix}test/test.bin")
                    else:
                        candidates.append(f"{base}/test/test.bin")
                else:
                    candidates.append(f"{base}/test/test.bin")

            for candidate in candidates:
                # 记录一次 quick-test 的尝试信息
                try:
                    if log_callback:
                        log_callback(f"快速检测: {source_name} -> {candidate}")
                    else:
                        print(f"快速检测: {source_name} -> {candidate}")
                except Exception:
                    pass

                ok, speed = self.measure_speed(candidate, f"{source_name}", required_speed_mb, log_callback, max_seconds=max_seconds, max_bytes=max_bytes)

                # 记录此次候选的测速结果
                try:
                    msg = f"快速检测结果: {source_name} -> {candidate} => {speed:.2f} MB/s ({'达标' if ok else '未达标'})"
                    if log_callback:
                        log_callback(msg)
                    else:
                        print(msg)
                except Exception:
                    pass
                if ok and speed > required_speed_mb:
                    return source_name, candidate, speed
        return None