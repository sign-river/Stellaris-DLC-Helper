#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终验证测试
"""

import sys
from pathlib import Path

# 将 repo 根目录加入 sys.path 以便通过 src 包引用内部模块
here = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(here))

from src.core.source_manager import SourceManager
from src.core.dlc_manager import DLCManager

def final_test():
    print('=== 最终验证 ===')

    manager = SourceManager()
    dlc_manager = DLCManager('dummy_path')

    print(f'启用的源: {len(manager.get_enabled_sources())}')
    for source in manager.get_enabled_sources():
        print(f'  - {source["name"]}: {source["url"]}')

    # 测试DLC列表获取
    try:
        dlc_list = dlc_manager.fetch_dlc_list()
        print(f'✓ 获取到 {len(dlc_list)} 个DLC')

        # 测试URL生成
        if dlc_list:
            test_dlc = dlc_list[0]
            urls = test_dlc.get('urls', [])
            print(f'测试DLC "{test_dlc["name"]}" 有 {len(urls)} 个下载URL:')
            for i, url in enumerate(urls, 1):
                print(f'  {i}. {url}')

    except Exception as e:
        print(f'✗ 错误: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    final_test()