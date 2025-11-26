#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
包含全局常量和配置项
"""

# 版本号
VERSION = "1.0.0"

# Stellaris AppID (固定)
STELLARIS_APP_ID = "281990"

# DLC 服务器配置
DLC_SERVER_URL = "http://47.100.2.190/dlc/"
DLC_INDEX_URL = f"{DLC_SERVER_URL}index.json"

# 字体配置
FONT1 = ("Microsoft YaHei UI", 20, "bold")
FONT2 = ("Microsoft YaHei UI", 16, "bold")
FONT3 = ("Microsoft YaHei UI", 12)
FONT4 = ("Microsoft YaHei UI", 10)

# 网络配置
REQUEST_TIMEOUT = 30
CHUNK_SIZE = 8192

# 缓存配置
CACHE_DIR_NAME = "Stellaris_DLC_Cache"
DLC_CACHE_SUBDIR = "dlc"
LOG_CACHE_SUBDIR = "operation_logs"
