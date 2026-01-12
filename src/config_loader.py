#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
负责从 config.json 加载配置并提供访问接口
"""

import json
from pathlib import Path
import logging
import sys


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self):
        """初始化配置加载器"""
        # 以多个候选路径查找 config.json，兼容开发模式、打包后的 EXE、以及从当前工作目录启动的情况
        self.config_path = self._find_config_path()
        self._config = self._load_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "version": "1.0.0",
            "stellaris_app_id": "281990",
            "server": {
                "url": "http://47.100.2.190/dlc/",
                "timeout": 30,
                "update_url_base": "http://47.100.2.190/update/",
                "appinfo_url": "http://47.100.2.190/appinfo/stellaris_appinfo.json"
            },
            "network": {
                "chunk_size": 8192,
                "retry_times": 3
            },
            "cache": {
                "dir_name": "Stellaris_DLC_Cache",
                "dlc_subdir": "dlc",
                "log_subdir": "operation_logs"
            },
            "fonts": {
                "font1": ["Microsoft YaHei UI", 20, "bold"],
                "font2": ["Microsoft YaHei UI", 16, "bold"],
                "font3": ["Microsoft YaHei UI", 12],
                "font4": ["Microsoft YaHei UI", 10]
            }
        }

    def _find_config_path(self):
        """按优先级查找配置文件的路径，返回 Path（可能不存在）。

        优先级：
        - 开发模式：模块目录 > 当前工作目录 > 可执行文件目录
        - 打包模式：可执行文件目录 > PyInstaller _MEIPASS
        """
        candidates = []
        exe_dir = None
        try:
            exe_dir = Path(sys.executable).parent
        except Exception:
            exe_dir = None

        meipass = getattr(sys, "_MEIPASS", None)
        
        # 判断是否为打包模式
        is_frozen = getattr(sys, 'frozen', False) or meipass is not None

        if is_frozen:
            # 打包模式：优先使用可执行文件所在目录
            # 1. 可执行文件所在目录
            if exe_dir:
                candidates.append(exe_dir / "config.json")
            
            # 2. PyInstaller 临时目录（如果存在）
            if meipass:
                candidates.append(Path(meipass) / "config.json")
        else:
            # 开发模式：优先使用模块目录和当前工作目录，避免使用 Python 解释器所在目录
            # 1. 当前模块的上级目录（源码目录）
            try:
                from .utils.path_utils import PathUtils
                module_dir = Path(PathUtils.get_base_dir())
                candidates.append(module_dir / "config.json")
            except Exception:
                pass
            
            # 2. 当前工作目录
            candidates.append(Path.cwd() / "config.json")

        # 记录候选路径并返回第一个存在的
        for p in candidates:
            try:
                logging.debug(f"候选配置路径: {p} (exists={p.exists()})")
            except Exception:
                logging.debug(f"候选配置路径: {p}")
            if p.exists():
                logging.info(f"使用配置文件: {p}")
                return p

        # 如果都不存在，默认使用第一个候选（优先为 exe_dir），否则回退到模块目录
        from .utils.path_utils import PathUtils
        default = candidates[0] if candidates else Path(PathUtils.get_base_dir()) / "config.json"
        logging.info(f"未找到配置文件，默认使用路径: {default}")
        return default
    
    def _load_config(self):
        """加载配置文件"""
        # 尝试加载 config.json，self.config_path 由 _find_config_path() 选出
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logging.info(f"✓ 已加载配置文件: {self.config_path}")
                    return config
            except Exception as e:
                logging.warning(f"⚠ 警告: 加载配置文件失败，使用默认配置: {e}")
                return self._get_default_config()
        else:
            # 配置文件不存在，使用默认配置
            logging.warning(f"⚠ 配置文件不存在: {self.config_path}")
            logging.info("使用默认配置运行，建议从 GitHub 仓库下载 config.json")
            return self._get_default_config()
    
    def get(self, *keys, default=None):
        """
        获取配置项
        
        参数:
            *keys: 配置键路径，例如 get("server", "url")
            default: 默认值
            
        返回:
            配置值，如果不存在则返回默认值
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def reload(self):
        """重新加载配置文件"""
        self._config = self._load_config()


# 全局配置加载器实例
_loader = ConfigLoader()


def get_config(*keys, default=None):
    """
    获取配置项的便捷函数
    
    参数:
        *keys: 配置键路径
        default: 默认值
        
    返回:
        配置值
    """
    return _loader.get(*keys, default=default)


def reload_config():
    """重新加载配置"""
    _loader.reload()
