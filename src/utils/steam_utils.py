#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 工具模块
用于自动检测 Steam 游戏路径
"""

import os
import re
import winreg
from pathlib import Path
from typing import Optional, List


class SteamUtils:
    """Steam 工具类"""
    
    STELLARIS_APPID = "281990"
    
    @staticmethod
    def get_steam_path() -> Optional[str]:
        """
        从注册表获取 Steam 安装路径
        
        返回:
            Steam 安装路径，如果未找到返回 None
        """
        try:
            # 尝试 64 位注册表
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Valve\Steam",
                0,
                winreg.KEY_READ
            )
            steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
            winreg.CloseKey(key)
            return steam_path
        except:
            pass
        
        try:
            # 尝试 32 位注册表
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Valve\Steam",
                0,
                winreg.KEY_READ
            )
            steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
            winreg.CloseKey(key)
            return steam_path
        except:
            pass
        
        return None
    
    @staticmethod
    def parse_vdf(content: str) -> dict:
        """
        简单解析 VDF 文件（Valve Data Format）
        
        参数:
            content: VDF 文件内容
            
        返回:
            解析后的字典
        """
        result = {}
        current_key = None
        
        # 匹配键值对: "key" "value"
        pattern = r'"([^"]+)"\s+"([^"]+)"'
        
        for match in re.finditer(pattern, content):
            key, value = match.groups()
            if key == "path":
                current_key = len(result)
                result[current_key] = {"path": value}
            elif current_key is not None and key == "apps":
                # 跳过 apps 块
                continue
        
        return result
    
    @staticmethod
    def get_library_folders(steam_path: str) -> List[str]:
        """
        获取所有 Steam 游戏库文件夹
        
        参数:
            steam_path: Steam 安装路径
            
        返回:
            游戏库路径列表
        """
        libraries = [steam_path]  # 默认库就是 Steam 安装目录
        
        vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        
        if not os.path.exists(vdf_path):
            return libraries
        
        try:
            with open(vdf_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单解析 VDF，查找所有 "path" 键
            pattern = r'"path"\s+"([^"]+)"'
            for match in re.finditer(pattern, content):
                lib_path = match.group(1)
                # 处理转义的反斜杠
                lib_path = lib_path.replace('\\\\', '\\')
                if os.path.exists(lib_path) and lib_path not in libraries:
                    libraries.append(lib_path)
        
        except Exception as e:
            import logging
            logging.warning(f"解析 libraryfolders.vdf 失败: {e}")
        
        return libraries
    
    @staticmethod
    def find_game_in_library(library_path: str, appid: str) -> Optional[str]:
        """
        在指定游戏库中查找游戏
        
        参数:
            library_path: 游戏库路径
            appid: 游戏 AppID
            
        返回:
            游戏安装路径，如果未找到返回 None
        """
        steamapps_path = os.path.join(library_path, "steamapps")
        
        if not os.path.exists(steamapps_path):
            return None
        
        # 查找 appmanifest 文件
        manifest_file = os.path.join(steamapps_path, f"appmanifest_{appid}.acf")
        
        if not os.path.exists(manifest_file):
            return None
        
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找 installdir
            match = re.search(r'"installdir"\s+"([^"]+)"', content)
            if match:
                install_dir = match.group(1)
                game_path = os.path.join(steamapps_path, "common", install_dir)
                
                if os.path.exists(game_path):
                    return game_path
        
        except Exception as e:
            import logging
            logging.warning(f"读取 manifest 文件失败: {e}")
        
        return None
    
    @classmethod
    def auto_detect_stellaris(cls) -> Optional[str]:
        """
        自动检测 Stellaris 游戏路径
        
        返回:
            Stellaris 游戏路径，如果未找到返回 None
        """
        # 1. 获取 Steam 路径
        steam_path = cls.get_steam_path()
        if not steam_path:
            return None
        
        # 2. 获取所有游戏库
        libraries = cls.get_library_folders(steam_path)
        
        # 3. 在每个库中查找 Stellaris
        for library in libraries:
            game_path = cls.find_game_in_library(library, cls.STELLARIS_APPID)
            if game_path:
                return game_path
        
        return None


def test():
    """测试函数"""
    import logging
    logging.info("测试 Steam 路径检测...")
    
    steam_path = SteamUtils.get_steam_path()
    logging.info(f"Steam 安装路径: {steam_path}")
    
    if steam_path:
        libraries = SteamUtils.get_library_folders(steam_path)
        logging.info(f"\n找到 {len(libraries)} 个游戏库:")
        for lib in libraries:
            logging.info(f"  - {lib}")
    
    stellaris_path = SteamUtils.auto_detect_stellaris()
    if stellaris_path:
        logging.info(f"\n✓ 找到 Stellaris: {stellaris_path}")
    else:
        logging.warning("\n✗ 未找到 Stellaris")


if __name__ == "__main__":
    test()
