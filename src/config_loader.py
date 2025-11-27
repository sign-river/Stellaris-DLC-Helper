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


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self):
        """初始化配置加载器"""
        self.config_path = Path(__file__).parent.parent / "config.json"
        self.example_path = Path(__file__).parent.parent / "config.json.example"
        self._config = self._load_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "version": "1.0.0",
            "stellaris_app_id": "281990",
            "server": {
                "url": "http://47.100.2.190/dlc/",
                "timeout": 30
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
    
    def _load_config(self):
        """加载配置文件"""
        # 尝试加载 config.json
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
            # 如果不存在，从 config.json.example 复制
            if self.example_path.exists():
                try:
                    shutil.copy(self.example_path, self.config_path)
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
        
        Args:
            *keys: 配置键路径，例如 get("server", "url")
            default: 默认值
            
        Returns:
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
    
    Args:
        *keys: 配置键路径
        default: 默认值
        
    Returns:
        配置值
    """
    return _loader.get(*keys, default=default)


def reload_config():
    """重新加载配置"""
    _loader.reload()
