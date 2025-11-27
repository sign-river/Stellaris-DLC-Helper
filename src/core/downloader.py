#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载模块
负责下载DLC文件，支持断点续传
"""

import os
import requests
from ..config import REQUEST_TIMEOUT, CHUNK_SIZE
from ..utils import PathUtils


class DLCDownloader:
    """DLC下载器类"""
    
    def __init__(self, progress_callback=None):
        """
        初始化下载器
        
        Args:
            progress_callback: 进度回调函数 callback(percent, downloaded, total)
        """
        self.progress_callback = progress_callback
        self.paused = False  # 暂停标志
        self.stopped = False  # 停止标志
        
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
    
    def download(self, url, dest_path):
        """
        下载文件（支持断点续传）
        
        Args:
            url: 下载URL
            dest_path: 目标文件路径
            
        Returns:
            bool: 是否成功
            
        Raises:
            Exception: 下载失败
        """
        try:
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
            
            response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers)
            
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
                        import time
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
            
            return True
        except Exception as e:
            raise Exception(f"下载失败: {str(e)}")
    
    def download_dlc(self, dlc_key, url):
        """
        下载DLC到缓存
        
        Args:
            dlc_key: DLC键名
            url: 下载URL
            
        Returns:
            str: 缓存文件路径
            
        Raises:
            Exception: 下载失败
        """
        cache_path = PathUtils.get_dlc_cache_path(dlc_key)
        
        # 如果缓存已存在，直接返回
        if os.path.exists(cache_path):
            return cache_path
        
        # 下载到缓存
        self.download(url, cache_path)
        return cache_path
    
    def is_cached(self, dlc_key):
        """
        检查DLC是否已缓存
        
        Args:
            dlc_key: DLC键名
            
        Returns:
            bool: 是否已缓存
        """
        cache_path = PathUtils.get_dlc_cache_path(dlc_key)
        return os.path.exists(cache_path)
