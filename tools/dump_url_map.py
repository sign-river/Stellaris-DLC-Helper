#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印并保存生成的 DLC URL 映射表
"""
import json
import os
from pathlib import Path
from src.core.dlc_manager import DLCManager
from src.utils import PathUtils


def main():
    game_dir = None
    # 尝试使用自动检测
    try:
        from src.utils.steam_utils import SteamUtils
        game_dir = SteamUtils.auto_detect_stellaris()
    except Exception:
        pass

    if not game_dir:
        # 使用默认路径或从环境变量
        game_dir = input('请输入 Stellaris 游戏根目录路径 (或按 Enter 跳过): ')
        if not game_dir:
            print('未指定路径，使用当前目录运行')
            game_dir = os.getcwd()

    manager = DLCManager(game_dir)
    dlc_list = manager.fetch_dlc_list()
    # SourceManager.build_dlc_url_map 已经将映射写入缓存目录，直接读取
    cache_dir = PathUtils.get_cache_dir()
    url_map_path = os.path.join(cache_dir, 'dlc_urls.json')
    if os.path.exists(url_map_path):
        with open(url_map_path, 'r', encoding='utf-8') as f:
            url_map = json.load(f)
        print(json.dumps(url_map, indent=2, ensure_ascii=False))
    else:
        print('未找到 dlc_urls.json，请确保已加载 DLC 列表')


if __name__ == '__main__':
    main()
