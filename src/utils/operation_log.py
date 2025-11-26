#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作记录管理模块
"""

import os
import json
from datetime import datetime
from .path_utils import PathUtils


class OperationLog:
    """操作记录管理类"""
    
    def __init__(self, game_path):
        """
        初始化操作记录管理器
        
        Args:
            game_path: 游戏路径
        """
        self.game_path = game_path
        self.log_path = PathUtils.get_operation_log_path(game_path)
        
    def load(self):
        """
        加载操作日志
        
        Returns:
            dict: 日志数据
        """
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"operations": [], "game_path": self.game_path}
    
    def save(self, log_data):
        """
        保存操作日志
        
        Args:
            log_data: 日志数据
        """
        log_data["game_path"] = self.game_path
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存日志失败: {str(e)}")
    
    def add_operation(self, op_type, details):
        """
        添加操作记录
        
        Args:
            op_type: 操作类型
            details: 操作详情
        """
        log_data = self.load()
        log_data["operations"].append({
            "type": op_type,
            "details": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save(log_data)
    
    def clear(self):
        """清空操作日志"""
        if os.path.exists(self.log_path):
            try:
                os.remove(self.log_path)
            except Exception:
                pass
    
    def get_operations(self):
        """
        获取所有操作记录
        
        Returns:
            list: 操作列表
        """
        log_data = self.load()
        return log_data.get("operations", [])
