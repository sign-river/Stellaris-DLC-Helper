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
        # 关闭会话
        if hasattr(self, 'session'):
            self.session.close()
    
    def download(self, url, dest_path, fallback_urls=None):
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
        
        # 如果没有启用的备用URL，使用主URL
        if not urls_to_try:
            urls_to_try = [(url, "domestic_cloud")]  # 默认使用国内云
        
        last_exception = None
        
        # 尝试每个URL
        for current_url, source_name in urls_to_try:
            try:
                print(f"尝试从 {source_name} 下载...")
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
                return self._download_single_attempt(current_url, dest_path)
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
        
        # 检查是否有未完成的下载
        downloaded = 0
        if os.path.exists(temp_path):
            downloaded = os.path.getsize(temp_path)
        
        # 设置断点续传的请求头
        headers = {}
        if downloaded > 0:
            headers['Range'] = f'bytes={downloaded}-'
        
        response = self.session.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers)
        
        # 416 表示请求的范围无效（文件已完整）
        if response.status_code == 416:
            if os.path.exists(temp_path):
                os.rename(temp_path, dest_path)
            return True
        
        response.raise_for_status()
        
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
    
    def download_dlc(self, dlc_key, url, fallback_urls=None):
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
        self.download(url, cache_path, fallback_urls)
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
