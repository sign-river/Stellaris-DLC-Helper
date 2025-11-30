#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载源连通性测试
测试所有下载源的网络连通性
"""

import sys
import requests
from pathlib import Path

# 将 repo 根目录加入 sys.path 以便通过 src 包引用内部模块
here = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(here))

from src.core.source_manager import SourceManager
from src.core.dlc_manager import DLCManager
from src.config import REQUEST_TIMEOUT

def test_source_connectivity():
    """测试所有下载源的连通性"""
    print('=== 下载源连通性测试 ===\n')

    manager = SourceManager()
    dlc_manager = DLCManager('dummy_path')

    enabled_sources = manager.get_enabled_sources()
    print(f'发现 {len(enabled_sources)} 个启用的下载源\n')

    results = {}

    for source in enabled_sources:
        source_name = source['name']
        format_type = source.get('format', 'standard')
        base_url = source.get('url', '').rstrip('/')

        print(f'🔍 测试源: {source_name} ({format_type})')
        print(f'   基础URL: {base_url}')

        # 测试结果
        connectivity_ok = False
        test_url = None
        error_msg = None

        try:
            if format_type in ['standard', 'domestic_cloud']:
                # 测试index.json
                test_url = f"{base_url}/index.json"
                print(f'   测试URL: {test_url}')

                response = requests.head(test_url, timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    connectivity_ok = True
                    print(f'   ✅ 连通正常 (HTTP {response.status_code})')
                else:
                    error_msg = f'HTTP {response.status_code}'
                    print(f'   ❌ 响应异常 (HTTP {response.status_code})')

            elif format_type in ['github_release', 'gitee_release']:
                # 测试具体的DLC文件URL
                # 先获取DLC列表，然后测试第一个DLC的URL
                try:
                    dlc_list = dlc_manager.fetch_dlc_list()
                    if dlc_list:
                        test_dlc = dlc_list[0]
                        urls = manager.get_download_urls_for_dlc(
                            list(test_dlc.keys())[0] if isinstance(test_dlc, dict) and 'urls' not in test_dlc else 'test_key',
                            test_dlc
                        )

                        # 找到当前源的URL
                        source_url = None
                        for url in urls:
                            if source_name in url:
                                source_url = url
                                break

                        if source_url:
                            test_url = source_url
                            print(f'   测试URL: {test_url}')

                            response = requests.head(test_url, timeout=REQUEST_TIMEOUT)
                            if response.status_code == 200:
                                connectivity_ok = True
                                print(f'   ✅ 连通正常 (HTTP {response.status_code})')
                            else:
                                error_msg = f'HTTP {response.status_code}'
                                print(f'   ❌ 响应异常 (HTTP {response.status_code})')
                        else:
                            error_msg = '未找到测试URL'
                            print(f'   ⚠️  未找到该源的测试URL')
                    else:
                        error_msg = '无法获取DLC列表'
                        print(f'   ⚠️  无法获取DLC列表进行测试')
                except Exception as e:
                    error_msg = str(e)
                    print(f'   ❌ 测试失败: {e}')

        except requests.exceptions.Timeout:
            error_msg = '连接超时'
            print(f'   ❌ 连接超时 ({REQUEST_TIMEOUT}s)')
        except requests.exceptions.ConnectionError:
            error_msg = '连接失败'
            print(f'   ❌ 连接失败')
        except Exception as e:
            error_msg = str(e)
            print(f'   ❌ 测试异常: {e}')

        results[source_name] = {
            'connectivity_ok': connectivity_ok,
            'test_url': test_url,
            'error_msg': error_msg,
            'format_type': format_type
        }

        print()  # 空行分隔

    # 汇总结果
    print('=== 测试结果汇总 ===')
    all_ok = True

    for source_name, result in results.items():
        status = '✅' if result['connectivity_ok'] else '❌'
        print(f'{status} {source_name}: {"连通正常" if result["connectivity_ok"] else f"连接失败 ({result.get("error_msg", "未知错误")})"}')
        if not result['connectivity_ok']:
            all_ok = False

    print()
    if all_ok:
        print('🎉 所有下载源连通性测试通过！')
    else:
        print('⚠️  部分下载源存在连通性问题，请检查网络或配置。')
        print('\n📋 部署状态说明:')
        print('• R2源: ✅ 已部署并可访问')
        print('• 国内云服务器: ❌ 需要上传 index.json 和 DLC 文件')
        print('• GitHub: ❌ 需要创建 ste4.2 release 并上传 DLC 文件')
        print('• Gitee: ❌ 需要创建 ste1-26 和 ste27-39 releases 并上传 DLC 文件')

    return results

if __name__ == '__main__':
    test_source_connectivity()