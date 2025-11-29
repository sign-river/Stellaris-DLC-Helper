#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径工具模块
"""

import os
import sys
import hashlib
from ..config import CACHE_DIR_NAME, DLC_CACHE_SUBDIR, LOG_CACHE_SUBDIR, STELLARIS_APP_ID


class PathUtils:
    """路径工具类"""
    
    @staticmethod
    def get_base_dir():
        """获取程序基础目录"""
        if getattr(sys, 'frozen', False):
            # 打包后的exe
            return os.path.dirname(sys.executable)
        else:
            # 开发环境
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    @staticmethod
    def get_cache_dir():
        """获取缓存根目录"""
        cache_dir = os.path.join(PathUtils.get_base_dir(), CACHE_DIR_NAME)
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    @staticmethod
    def get_dlc_cache_dir():
        """获取DLC缓存目录"""
        dlc_dir = os.path.join(PathUtils.get_cache_dir(), DLC_CACHE_SUBDIR, STELLARIS_APP_ID)
        os.makedirs(dlc_dir, exist_ok=True)
        return dlc_dir
    
    @staticmethod
    def get_dlc_cache_path(dlc_key):
        """
        获取DLC缓存文件路径
        
        参数:
            dlc_key: DLC键名
            
        返回:
            str: 缓存文件完整路径
        """
        return os.path.join(PathUtils.get_dlc_cache_dir(), f"{dlc_key}.zip")
    
    @staticmethod
    def get_log_dir():
        """获取日志目录"""
        log_dir = os.path.join(PathUtils.get_cache_dir(), LOG_CACHE_SUBDIR)
        os.makedirs(log_dir, exist_ok=True)
        return log_dir
    
    @staticmethod
    def get_operation_log_path(game_path):
        """
        获取操作日志文件路径
        
        参数:
            game_path: 游戏路径
            
        返回:
            str: 日志文件路径
        """
        path_hash = hashlib.md5(game_path.encode()).hexdigest()[:12]
        return os.path.join(PathUtils.get_log_dir(), f"operations_{path_hash}.json")
    
    @staticmethod
    def validate_stellaris_path(path):
        """
        验证是否是有效的Stellaris游戏目录
        
        参数:
            path: 游戏路径
            
        返回:
            bool: 是否有效
        """
        if os.path.exists(os.path.join(path, "stellaris.app")):
            return True
        return os.path.exists(os.path.join(path, "stellaris.exe"))
    
    @staticmethod
    def get_dlc_folder(game_path):
        """
        获取游戏DLC文件夹路径
        
        参数:
            game_path: 游戏路径
            
        返回:
            str: DLC文件夹路径
        """
        return os.path.join(game_path, "dlc")

    @staticmethod
    def get_appinfo_dir():
        """
        获取 AppInfo 缓存目录（用于保存 stellaris_appinfo.json 等缓存文件）
        返回: str: 目录路径
        """
        appinfo_dir = os.path.join(PathUtils.get_cache_dir(), 'appinfo')
        os.makedirs(appinfo_dir, exist_ok=True)
        return appinfo_dir

    @staticmethod
    def get_appinfo_path(filename: str = 'stellaris_appinfo.json'):
        """
        获取 AppInfo 缓存文件的完整路径
        参数:
            filename: 应用配置文件名
        返回: str: 文件完整路径
        """
        return os.path.join(PathUtils.get_appinfo_dir(), filename)
