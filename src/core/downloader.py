#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载模块
负责下载DLC文件
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
        
    def download(self, url, dest_path):
        """
        下载文件
        
        Args:
            url: 下载URL
            dest_path: 目标文件路径
            
        Returns:
            bool: 是否成功
            
        Raises:
            Exception: 下载失败
        """
        try:
            response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            total = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 调用进度回调
                        if self.progress_callback and total > 0:
                            percent = (downloaded / total) * 100
                            self.progress_callback(percent, downloaded, total)
            
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
