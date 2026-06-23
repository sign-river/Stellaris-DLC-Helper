#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新残留文件清理：.new 替换、.old 备份、过期批处理配置
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def apply_pending_new_files(app_root: Path, log: Optional[logging.Logger] = None) -> int:
    """将程序目录中的 *.new 文件替换为目标文件。返回成功数量。"""
    log = log or logger
    if not getattr(sys, 'frozen', False):
        return 0

    success = 0
    for new_file in sorted(app_root.glob('*.new')):
        try:
            target_name = new_file.name[:-4]
            target_file = app_root / target_name

            if target_file.resolve() == Path(sys.executable).resolve():
                log.warning(f"跳过正在运行的主程序: {target_file.name}")
                continue

            if target_file.exists():
                backup = target_file.with_suffix(target_file.suffix + '.old')
                try:
                    if backup.exists():
                        backup.unlink()
                except OSError:
                    pass
                target_file.rename(backup)
                new_file.rename(target_file)
                _try_remove(backup, log)
            else:
                new_file.rename(target_file)

            log.info(f"已完成替换: {target_file.name}")
            success += 1
        except Exception as e:
            log.warning(f"处理 {new_file.name} 失败: {e}")
    return success


def cleanup_old_backups(app_root: Path, log: Optional[logging.Logger] = None) -> int:
    """删除程序目录中已成功替换后遗留的 *.old 备份。返回删除数量。"""
    log = log or logger
    removed = 0
    for old_file in app_root.glob('*.old'):
        if _try_remove(old_file, log):
            log.info(f"已清理备份: {old_file.name}")
            removed += 1
    return removed


def cleanup_stale_batch_configs(app_root: Path, log: Optional[logging.Logger] = None) -> int:
    """删除过期的 update_batch_*.json 配置。返回删除数量。"""
    log = log or logger
    removed = 0
    for batch_file in app_root.glob('update_batch_*.json'):
        if _try_remove(batch_file, log):
            log.debug(f"已清理批处理配置: {batch_file.name}")
            removed += 1
    return removed


def run_startup_update_cleanup(app_root: Path, log: Optional[logging.Logger] = None) -> dict:
    """启动时执行完整的更新残留清理。"""
    log = log or logger
    applied = apply_pending_new_files(app_root, log)
    removed_old = cleanup_old_backups(app_root, log)
    removed_batch = cleanup_stale_batch_configs(app_root, log)
    if applied or removed_old or removed_batch:
        log.info(
            f"启动清理完成: 替换 {applied} 个 .new, "
            f"删除 {removed_old} 个 .old, {removed_batch} 个批处理配置"
        )
    return {
        'applied_new': applied,
        'removed_old': removed_old,
        'removed_batch': removed_batch,
    }


def _try_remove(path: Path, log: logging.Logger) -> bool:
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        log.debug(f"暂无法删除 {path.name}: {e}")
        return False
