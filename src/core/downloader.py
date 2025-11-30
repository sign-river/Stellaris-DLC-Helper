#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载模块
负责下载DLC文件，支持断点续传
"""

import os
import time
import requests
from ..config import REQUEST_TIMEOUT, CHUNK_SIZE, RETRY_TIMES
from ..utils import PathUtils


class DLCDownloader:
    """DLC下载器类"""
    
    def __init__(self, progress_callback=None):
        """
        初始化下载器
        
        参数:
            progress_callback: 进度回调函数 callback(percent, downloaded, total)
        """
        self.progress_callback = progress_callback
        self.paused = False  # 暂停标志
        self.stopped = False  # 停止标志
        
        # 创建SourceManager实例用于检查启用的源
        from .source_manager import SourceManager
        self.source_manager = SourceManager()
        
        # 创建会话以复用连接
        self.session = requests.Session()
        # 设置合理的超时和重试
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0,  # 我们自己处理重试
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
    def pause(self):
        """暂停下载"""
        self.paused = True
    
    def resume(self):
        """恢复下载"""
        self.paused = False
    
    def stop(self):
        """停止下载"""
        self.stopped = True
        self.paused = False
        # 注意：不在 stop 中关闭 session，这样可在切换后进行重试
        # 如果需要彻底释放资源，请调用 close()

    def close(self):
        """彻底关闭下载器并释放会话"""
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except Exception:
                pass
    
    def download(self, url, dest_path, fallback_urls=None, expected_hash: str = None, primary_source_name: str = None):
        """
        下载文件（支持断点续传、重试和多源fallback）
        
        参数:
            url: 主下载URL
            dest_path: 目标文件路径
            fallback_urls: 备用URL列表（可选）
            
        返回:
            bool: 是否成功
            
        抛出:
            Exception: 下载失败
        """
        # 使用所有URL，但只尝试启用的源
        urls_to_try = []
        # 添加主 URL（如果指定 primary_source_name，则附带源名称）
        if primary_source_name:
            urls_to_try.append((url, primary_source_name))
        else:
            urls_to_try.append((url, None))

        if fallback_urls:
            # 检查哪些源是启用的
            enabled_source_names = set()
            if hasattr(self, 'source_manager') and self.source_manager:
                enabled_sources = self.source_manager.get_enabled_sources()
                enabled_source_names = {s.get("name") for s in enabled_sources}
            
            # 只添加启用的源
            for url, source_name in fallback_urls:
                if source_name in enabled_source_names:
                    urls_to_try.append((url, source_name))
        
        # 如果没有启用的源可用（按 enable 检查），确保有 perferred main url尝试
        if not urls_to_try:
            urls_to_try = [(url, primary_source_name or "domestic_cloud")]  # 默认使用国内云
        
        last_exception = None
        
        # 尝试每个URL
        for current_url, source_name in urls_to_try:
            try:
                print(f"尝试从 {source_name} 下载...")
                # 记录完整 URL 到日志（有助于调试 URL 映射是否正确）
                # 尝试将 URL 记录到 progress_callback（如果可调用）和标准输出
                # 尝试通过 progress_callback.log_message 或 progress_callback 提供的记录方式输出 URL
                if hasattr(self, 'progress_callback'):
                    try:
                        if hasattr(self.progress_callback, 'log_message') and callable(self.progress_callback.log_message):
                            self.progress_callback.log_message(f"尝试 URL: {current_url}")
                        elif callable(self.progress_callback):
                            # 不要乱用 progress_callback，避免破坏其预期签名；不直接调用它
                            pass
                    except Exception:
                        pass
                # 控制台也输出，便于 CLI 调试
                print(f"尝试 URL: {current_url}")
                # 如果有UI回调，更新当前下载源显示
                if hasattr(self, 'progress_callback') and self.progress_callback:
                    # 确保progress_callback已初始化
                    if not hasattr(self.progress_callback, 'update_source'):
                        # 调用一次progress_callback来初始化它
                        try:
                            self.progress_callback(0, 0, 100)
                        except:
                            pass  # 忽略初始化错误
                    
                    # 现在调用update_source
                    if hasattr(self.progress_callback, 'update_source'):
                        # 源名称映射为用户友好的显示名称
                        display_name = {
                            "r2": "R2云存储",
                            "domestic_cloud": "国内云服务器", 
                            "gitee": "Gitee",
                            "github": "GitHub"
                        }.get(source_name, source_name)
                        self.progress_callback.update_source(display_name)
                result = self._download_single_attempt(current_url, dest_path)
                # 验证哈希（如果提供）
                if result and expected_hash:
                    try:
                        ok = self._verify_file_hash(dest_path, expected_hash)
                        if not ok:
                            # 校验失败，记录并抛出错误以便 trigger fallback
                            raise Exception("校验失败: 文件哈希与期望值不匹配")
                        # 校验通过日志
                        try:
                            if hasattr(self, 'progress_callback') and getattr(self.progress_callback, 'log_message', None):
                                self.progress_callback.log_message(f"文件校验通过: {dest_path}")
                        except Exception:
                            pass
                    except Exception as e:
                        # 删除错误文件并尝试下一源
                        try:
                            if os.path.exists(dest_path):
                                os.remove(dest_path)
                        except Exception:
                            pass
                        raise
                return result
            except Exception as e:
                last_exception = e
                print(f"从 {source_name} 下载失败: {str(e)}")
                if (current_url, source_name) != urls_to_try[-1]:  # 不是最后一个URL
                    print("尝试下一个源...")
                    continue
        
        # 所有URL都失败了
        raise Exception(f"所有下载源都失败，最后一次错误: {str(last_exception)}")
    
    def _download_single_attempt(self, url, dest_path):
        """
        单次下载尝试（内部方法）
        
        参数:
            url: 下载URL
            dest_path: 目标文件路径
            
        返回:
            bool: 是否成功
            
        抛出:
            Exception: 下载失败
        """
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # 临时文件路径
        temp_path = dest_path + ".tmp"
        
        # 检查是否有未完成的下载（断点续传）
        downloaded = 0
        if os.path.exists(temp_path):
            downloaded = os.path.getsize(temp_path)
        
        # 在尝试续传前，检查当前 URL 是否支持 Range 请求，且文件大小一致
        def _head_check_resume(u, current_downloaded):
            try:
                head = self.session.head(u, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                if head.status_code not in (200, 206):
                    return None
                cl = head.headers.get('Content-Length')
                accept_ranges = head.headers.get('Accept-Ranges', '')
                if cl is not None:
                    try:
                        remote_size = int(cl)
                    except Exception:
                        remote_size = None
                else:
                    remote_size = None

                # 如果 remote_size is set and remote_size < current_downloaded => mismatch
                if remote_size is not None and remote_size < current_downloaded:
                    # 远端比本地短：不一致
                    try:
                        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
                            self.progress_callback.log_message(f"远端文件大小({remote_size})比本地已下载({current_downloaded})小，无法继续续传")
                    except Exception:
                        pass
                    return False

                # if server supports ranges it's more safe to resume
                if 'bytes' in accept_ranges.lower():
                    try:
                        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
                            self.progress_callback.log_message("远端支持 Range，准备开始续传")
                    except Exception:
                        pass
                    return True

                # If content-length exists and remote_size >= current_downloaded but no Accept-Ranges
                if remote_size is not None and remote_size >= current_downloaded:
                    # We can attempt to resume by issuing a ranged GET and seeing if 206 returned
                    try:
                        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
                            self.progress_callback.log_message("远端返回 Content-Length，尝试 Range 请求以校验")
                    except Exception:
                        pass
                    return True

                # Unknown capability
                return None
            except Exception:
                return None

        # 设置断点续传的请求头（如果适合续传）
        headers = {}
        if downloaded > 0:
            resume_ok = _head_check_resume(url, downloaded)
            if resume_ok is True:
                headers['Range'] = f'bytes={downloaded}-'
                print(f"尝试续传: 已有 {downloaded} 字节，准备从 {downloaded} 继续下载")
            elif resume_ok is False:
                # 远端文件变短或不一致，删除临时文件并重新开始
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                downloaded = 0
            else:
                # 未确定是否支持续传，尝试 Range: bytes={downloaded}-，如果服务器返回 206 则继续
                headers['Range'] = f'bytes={downloaded}-'
                print("未确定是否支持断点续传，尝试发送 Range 请求")
        
        # 记录要尝试的 URL（方便调试）
        print(f"开始单次尝试下载 URL: {url} -> {dest_path}")
        response = self.session.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers)
        
        # 416 表示请求的范围无效（文件已完整）
        if response.status_code == 416:
            if os.path.exists(temp_path):
                os.rename(temp_path, dest_path)
            return True
        
        response.raise_for_status()
        
        # 如果我们请求了 `Range` 并得到 200，说明服务器不支持 Range，所以需要重置（删除 tmp 并重新请求完整文件）
        if downloaded > 0 and response.status_code == 200:
            # 服务端没有按 Range 返回 206（不支持或忽略），删除临时文件并重新发起单次请求
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            # 重新发起没有 Range 的请求来下载完整文件
            response.close()
            headers.pop('Range', None)
            response = self.session.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers)

        # 获取文件总大小
        if 'Content-Range' in response.headers:
            # 断点续传：从 Content-Range 中解析总大小
            total = int(response.headers['Content-Range'].split('/')[-1])
        else:
            # 全新下载
            total = int(response.headers.get('content-length', 0))
        
        # 写入模式：追加或新建
        mode = 'ab' if downloaded > 0 else 'wb'
        
        with open(temp_path, mode) as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                # 检查是否被停止
                if self.stopped:
                    raise Exception("下载已停止")
                
                # 检查是否暂停
                while self.paused and not self.stopped:
                    time.sleep(0.1)
                
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 调用进度回调
                    if self.progress_callback and total > 0:
                        percent = (downloaded / total) * 100
                        self.progress_callback(percent, downloaded, total)
        
        # 下载完成，重命名临时文件
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(temp_path, dest_path)
        
        # 验证文件完整性
        if total > 0:
            actual_size = os.path.getsize(dest_path)
            if actual_size != total:
                raise Exception(f"文件大小不匹配: 期望 {total} 字节，实际 {actual_size} 字节")
        
        return True

    def _verify_file_hash(self, path: str, expected_hash: str) -> bool:
        """
        验证指定文件的 SHA256 哈希是否与 expected_hash 匹配
        """
        try:
            import hashlib
            if not expected_hash:
                return True
            expected = expected_hash.strip().lower()
            sha256 = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            got = sha256.hexdigest().lower()
            if got == expected:
                return True
            else:
                print(f"校验失败: {path} SHA256 不匹配 (期望 {expected}, 实际 {got})")
                try:
                    if hasattr(self, 'progress_callback') and getattr(self.progress_callback, 'log_message', None):
                        self.progress_callback.log_message(f"校验失败: {path} 期望 {expected}, 实际 {got}")
                except Exception:
                    pass
                return False
        except Exception as e:
            print(f"验证哈希时发生错误: {e}")
            return False
    
    def download_dlc(self, dlc_key, url, fallback_urls=None, expected_hash: str = None, primary_source_name: str = None):
        """
        下载DLC到缓存
        
        参数:
            dlc_key: DLC键名
            url: 主下载URL
            fallback_urls: 备用URL列表 (List[Tuple[str, str]] - URL和源名称的元组)
            
        返回:
            str: 缓存文件路径
            
        抛出:
            Exception: 下载失败
        """
        # 从URL提取文件名
        filename = url.split('/')[-1]
        if not filename:
            filename = f"{dlc_key}.zip"
        cache_path = os.path.join(PathUtils.get_dlc_cache_dir(), filename)
        
        # 如果缓存已存在，直接返回
        if os.path.exists(cache_path):
            return cache_path
        
        # 下载到缓存
        self.download(url, cache_path, fallback_urls, expected_hash=expected_hash, primary_source_name=primary_source_name)
        return cache_path
    
    def is_cached(self, dlc_key):
        """
        检查DLC是否已缓存
        
        参数:
            dlc_key: DLC键名
            
        返回:
            bool: 是否已缓存
        """
        # 检查是否有任何以dlc_key开头的zip文件
        cache_dir = PathUtils.get_dlc_cache_dir()
        if not os.path.exists(cache_dir):
            return False
        
        for file in os.listdir(cache_dir):
            if file.startswith(f"{dlc_key}.") and file.endswith('.zip'):
                return True
        return False
