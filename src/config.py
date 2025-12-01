#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
提供全局配置常量的访问接口
所有配置值从 config.json 加载
"""

from .config_loader import get_config

# 版本号
VERSION = get_config("version", default="1.0.0")

# Stellaris 游戏 AppID
STELLARIS_APP_ID = get_config("stellaris_app_id", default="281990")

# DLC 服务器配置 - 多源支持
DLC_SOURCES = get_config("server", "sources", default=[
    {
        "name": "r2",
        "url": "https://dlc.dlchelper.top/dlc/",
        "priority": 1,
        "enabled": True,
        "format": "standard"
    }
])

# 兼容性：保留原有配置作为默认源
DLC_SERVER_URL = DLC_SOURCES[0]["url"] if DLC_SOURCES else "https://dlc.dlchelper.top/dlc/"
DLC_INDEX_URL = f"{DLC_SERVER_URL}index.json"

def _get_best_source_url():
    """获取最佳的源URL（优先选择国内云服务器）"""
    # 优先选择国内云服务器
    for source in DLC_SOURCES:
        if source.get("name") == "domestic_cloud" and source.get("enabled", False):
            return source["url"].rstrip("/")
    # 如果没有找到，选第一个启用的源
    for source in DLC_SOURCES:
        if source.get("enabled", False):
            return source["url"].rstrip("/")
    # 默认值
    return "https://dlc.dlchelper.top"

# 更新服务器配置 - 使用专用配置
UPDATE_URL_BASE = get_config("server", "update_url_base", default="https://dlc.dlchelper.top/update/")
UPDATE_CHECK_URL = f"{UPDATE_URL_BASE}version.json"
ANNOUNCEMENT_URL = f"{UPDATE_URL_BASE}announcement.txt"
APPINFO_URL = get_config("server", "appinfo_url", default="https://dlc.dlchelper.top/appinfo/stellaris_appinfo.json")

# 网络配置
REQUEST_TIMEOUT = get_config("server", "timeout", default=30)
CHUNK_SIZE = get_config("network", "chunk_size", default=8192)
RETRY_TIMES = get_config("network", "retry_times", default=3)

# 缓存配置
CACHE_DIR_NAME = get_config("cache", "dir_name", default="Stellaris_DLC_Cache")
DLC_CACHE_SUBDIR = get_config("cache", "dlc_subdir", default="dlc")
LOG_CACHE_SUBDIR = get_config("cache", "log_subdir", default="operation_logs")

# 字体配置
FONT1 = tuple(get_config("fonts", "font1", default=["Microsoft YaHei UI", 20, "bold"]))
FONT2 = tuple(get_config("fonts", "font2", default=["Microsoft YaHei UI", 16, "bold"]))
FONT3 = tuple(get_config("fonts", "font3", default=["Microsoft YaHei UI", 12]))
FONT4 = tuple(get_config("fonts", "font4", default=["Microsoft YaHei UI", 10]))
