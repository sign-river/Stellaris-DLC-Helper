#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
提供全局配置常量的访问接口
所有配置值从 config.json 加载
"""

from .config_loader import get_config

# 版本号（从 config.json 读取）
VERSION = get_config("version", default="1.0.2")

# Stellaris 游戏 AppID
STELLARIS_APP_ID = get_config("stellaris_app_id", default="281990")

# GitLink DLC API URL（仅支持GitLink单一源）
DLC_API_URL = "https://gitlink.org.cn/api/signriver/file-warehouse/releases.json"

# 更新服务器配置 - GitLink
UPDATE_URL_BASE = get_config("server", "update_url_base", default="https://gitlink.org.cn/signriver/file-warehouse/releases/download/v/")
UPDATE_CHECK_URL = f"{UPDATE_URL_BASE}version.json"
ANNOUNCEMENT_URL = f"{UPDATE_URL_BASE}announcement.txt"

# AppInfo 配置 - GitLink (和 DLC 文件放在一起)
APPINFO_URL = get_config("server", "appinfo_url", default="https://gitlink.org.cn/signriver/file-warehouse/releases/download/ste/stellaris_appinfo.json")

# 网络配置
REQUEST_TIMEOUT = get_config("server", "timeout", default=10)  # 减少超时时间，避免启动卡顿
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
