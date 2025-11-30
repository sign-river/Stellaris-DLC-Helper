#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
负责从 config.json 加载配置并提供访问接口
"""

import json
import shutil
from pathlib import Path
import logging
import sys


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self):
        """初始化配置加载器"""
        # 以多个候选路径查找 config.json，兼容开发模式、打包后的 EXE、以及从当前工作目录启动的情况
        self.config_path = self._find_config_path()
        self.example_path = Path(__file__).parent.parent / "config.json.example"
        self._config = self._load_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "version": "1.0.0",
            "stellaris_app_id": "281990",
            "server": {
                "url": "https://dlc.dlchelper.top/dlc/",
                "timeout": 30,
                "update_url_base": "https://dlc.dlchelper.top/update/",
                "appinfo_url": "https://dlc.dlchelper.top/appinfo/stellaris_appinfo.json"
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

        优先级：当前工作目录、可执行文件目录、模块文件目录、PyInstaller 的 _MEIPASS。
        """
        candidates = []
        # 1. 当前工作目录
        candidates.append(Path.cwd() / "config.json")

        # 2. 可执行文件所在目录（对于打包 exe 很重要）
        try:
            exe_dir = Path(sys.executable).parent
            candidates.append(exe_dir / "config.json")
        except Exception:
            pass

        # 3. 当前模块的上级目录（原来的实现）
        try:
            module_dir = Path(__file__).parent.parent
            candidates.append(module_dir / "config.json")
        except Exception:
            pass

        # 4. PyInstaller 临时目录（如果存在）
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "config.json")

        # 记录候选路径并返回第一个存在的，如果都不存在则返回第一个候选（cwd）作为默认写入位置
        for p in candidates:
            logging.debug(f"候选配置路径: {p} (exists={p.exists()})")
            if p.exists():
                logging.info(f"使用配置文件: {p}")
                return p

        # 如果都不存在，返回第一个候选（cwd）用于创建
        default = candidates[0] if candidates else Path(__file__).parent.parent / "config.json"
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
            # 如果不存在，从 config.json.example 复制（先尝试在 self.config_path 的目录内）
            possible_example = self.example_path
            if not possible_example.exists():
                # 尝试在 _MEIPASS 中查找示例文件
                meipass = getattr(sys, "_MEIPASS", None)
                if meipass:
                    possible_example = Path(meipass) / "config.json.example"
            if possible_example.exists():
                try:
                    shutil.copy(possible_example, self.config_path)
                    logging.info(f"✓ 已从示例配置创建 config.json")
                    logging.info(f"  请根据需要修改: {self.config_path}")
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logging.warning(f"⚠ 警告: 无法创建配置文件: {e}")
            
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
