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

# Stellaris AppID
STELLARIS_APP_ID = get_config("stellaris_app_id", default="281990")

# DLC 服务器配置
DLC_SERVER_URL = get_config("server", "url", default="http://47.100.2.190/dlc/")
DLC_INDEX_URL = f"{DLC_SERVER_URL}index.json"

# 网络配置
REQUEST_TIMEOUT = get_config("server", "timeout", default=30)
CHUNK_SIZE = get_config("network", "chunk_size", default=8192)

# 缓存配置
CACHE_DIR_NAME = get_config("cache", "dir_name", default="Stellaris_DLC_Cache")
DLC_CACHE_SUBDIR = get_config("cache", "dlc_subdir", default="dlc")
LOG_CACHE_SUBDIR = get_config("cache", "log_subdir", default="operation_logs")

# 字体配置
FONT1 = tuple(get_config("fonts", "font1", default=["Microsoft YaHei UI", 20, "bold"]))
FONT2 = tuple(get_config("fonts", "font2", default=["Microsoft YaHei UI", 16, "bold"]))
FONT3 = tuple(get_config("fonts", "font3", default=["Microsoft YaHei UI", 12]))
FONT4 = tuple(get_config("fonts", "font4", default=["Microsoft YaHei UI", 10]))
