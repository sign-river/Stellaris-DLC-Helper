#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新系统验证脚本
用于验证更新包结构和更新系统配置
"""

import sys
import zipfile
from pathlib import Path


def check_update_package(zip_path: Path):
    """检查更新包结构"""
    print(f"\n检查更新包: {zip_path}")
    print("=" * 60)
    
    if not zip_path.exists():
        print(f"❌ 错误: 更新包不存在: {zip_path}")
        return False
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            all_files = zf.namelist()
            print(f"\n✅ 更新包有效，包含 {len(all_files)} 个文件")
            
            # 检查关键文件
            critical_files = [
                'Stellaris-DLC-Helper.exe',
                'config.json',
                'pairings.json',
            ]
            
            print("\n检查关键文件:")
            for cf in critical_files:
                found = False
                for f in all_files:
                    if f.endswith(cf):
                        print(f"  ✅ {cf}: {f}")
                        found = True
                        break
                if not found:
                    print(f"  ⚠️ {cf}: 未找到")
            
            # 检查 updater_helper.exe
            has_helper = any('updater_helper.exe' in f for f in all_files)
            if has_helper:
                print(f"  ✅ updater_helper.exe: 已包含")
            else:
                print(f"  ⚠️ updater_helper.exe: 未找到（更新可能依赖批处理脚本）")
            
            # 检查目录结构
            print("\n目录结构:")
            top_dirs = set()
            for f in all_files:
                parts = f.split('/')
                if len(parts) > 1:
                    top_dirs.add(parts[0])
            
            if len(top_dirs) == 1:
                top_dir = list(top_dirs)[0]
                print(f"  ✅ 单一顶层目录: {top_dir}")
                print(f"     这是推荐的结构，更新系统会自动识别")
            elif len(top_dirs) == 0:
                print(f"  ℹ️ 平铺结构（文件在根目录）")
            else:
                print(f"  ⚠️ 多个顶层目录: {', '.join(sorted(top_dirs))}")
                print(f"     可能导致更新失败")
            
            # 显示前10个文件
            print("\n更新包内容（前10项）:")
            for f in all_files[:10]:
                print(f"  - {f}")
            if len(all_files) > 10:
                print(f"  ... 还有 {len(all_files) - 10} 个文件")
            
            return True
            
    except Exception as e:
        print(f"❌ 错误: 无法读取更新包: {e}")
        return False


def check_current_installation():
    """检查当前安装"""
    print("\n检查当前安装")
    print("=" * 60)
    
    # 检查是否在 exe 模式
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        app_root = Path(sys.executable).parent
        print(f"✅ 运行模式: 打包exe")
    else:
        app_root = Path(__file__).parent
        print(f"ℹ️ 运行模式: 开发环境")
    
    print(f"程序根目录: {app_root}")
    
    # 检查关键文件
    critical_files = {
        'Stellaris-DLC-Helper.exe': '主程序',
        'updater_helper.exe': '更新助手',
        'config.json': '配置文件',
        'pairings.json': '映射文件',
    }
    
    print("\n关键文件检查:")
    for filename, desc in critical_files.items():
        file_path = app_root / filename
        if file_path.exists():
            size = file_path.stat().st_size / 1024
            print(f"  ✅ {filename} ({desc}): {size:.1f} KB")
        else:
            print(f"  ❌ {filename} ({desc}): 不存在")
    
    # 检查备份目录
    cache_dir = app_root / "Stellaris_DLC_Cache"
    backup_dir = cache_dir / "backup"
    if backup_dir.exists():
        backups = list(backup_dir.glob("backup_*"))
        print(f"\n✅ 备份目录存在: {len(backups)} 个备份")
        for backup in sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            print(f"  - {backup.name}")
    else:
        print(f"\nℹ️ 备份目录不存在（首次运行正常）")
    
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Stellaris DLC Helper - 更新系统验证工具")
    print("=" * 60)
    
    # 检查当前安装
    check_current_installation()
    
    # 如果提供了更新包路径，检查更新包
    if len(sys.argv) > 1:
        zip_path = Path(sys.argv[1])
        check_update_package(zip_path)
    else:
        print("\n" + "=" * 60)
        print("提示: 运行时可以指定更新包路径来检查:")
        print(f"  python {Path(__file__).name} <更新包.zip>")
        print("=" * 60)
    
    print("\n验证完成!")


if __name__ == '__main__':
    main()
