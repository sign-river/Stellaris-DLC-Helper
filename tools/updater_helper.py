#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Updater helper script
Used by application to reliably replace a running exe with a new file and restart it.
This script waits for the specified pid to exit (if provided), then moves the new file to the destination, starts it and exits.
If no pid is provided, falls back to waiting for the old file to be unlocked (poll-and-move).

Note: This script is designed for Windows systems only.
"""

import argparse
import os
import sys
import time
import shutil
import subprocess
import platform

# Windows 专属模块，仅在 Windows 系统导入
if platform.system() == "Windows":
    import ctypes
else:
    ctypes = None


def wait_for_pid(pid: int):
    """Wait for process with PID to exit using Windows API"""
    if platform.system() != "Windows" or ctypes is None:
        # 非 Windows 系统的简单等待（实际上此工具不应在非 Windows 系统运行）
        time.sleep(5)
        return
    
    # SYNCHRONIZE access right is 0x00100000
    SYNCHRONIZE = 0x00100000
    PROCESS_QUERY_INFORMATION = 0x0400
    # OpenProcess for the PID
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_INFORMATION, False, int(pid))
    if not handle:
        # maybe process not found
        return
    # WAIT_INFINITE = 0xFFFFFFFF
    WAIT_INFINITE = 0xFFFFFFFF
    kernel32.WaitForSingleObject(handle, WAIT_INFINITE)
    kernel32.CloseHandle(handle)


def wait_for_file_unlock(path: str):
    """Wait until the file can be replaced (no longer opened by another process)."""
    # Try to open in exclusive mode by renaming to a temp name
    for i in range(60):  # wait up to 60s
        try:
            # Try to rename the file to itself (no-op) as a quick lock check
            if os.path.exists(path):
                tmp = path + '.locktest'
                os.replace(path, tmp)
                os.replace(tmp, path)
            return
        except Exception:
            time.sleep(1)
    # Give up


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, default=None, help='PID to wait for')
    parser.add_argument('--new', required=False, help='New file path (单文件替换)')
    parser.add_argument('--dst', required=False, help='Destination path (单文件替换)')
    parser.add_argument('--batch', required=False, help='批量替换文件的 JSON 列表路径')
    args = parser.parse_args()

    new = os.path.abspath(args.new) if args.new else None
    dst = os.path.abspath(args.dst) if args.dst else None
    batch = os.path.abspath(args.batch) if args.batch else None

    try:
        if args.pid:
            wait_for_pid(args.pid)
        else:
            # fallback: wait for file unlock
            wait_for_file_unlock(dst)

        # 如果传入了批处理文件，则按序替换
        if batch and os.path.exists(batch):
            import json
            with open(batch, 'r', encoding='utf-8') as fh:
                pairs = json.load(fh)
            for p in pairs:
                newp = os.path.abspath(p.get('new'))
                dstp = os.path.abspath(p.get('dst'))
                for attempt in range(10):
                    try:
                        if os.path.exists(dstp):
                            os.remove(dstp)
                        shutil.move(newp, dstp)
                        break
                    except Exception:
                        time.sleep(1)
        elif new and dst:
            # 单文件替换
            for attempt in range(10):
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(new, dst)
                    break
                except Exception:
                    time.sleep(1)
        # 启动第一个被替换的目标（如果是 exe）以恢复运行
        try:
            # 如果批处理存在，尝试启动第一个目标
            first_dest = None
            if batch and os.path.exists(batch):
                import json
                with open(batch, 'r', encoding='utf-8') as fh:
                    pairs = json.load(fh)
                if pairs:
                    first_dest = os.path.abspath(pairs[0].get('dst'))
            elif dst:
                first_dest = dst
            if first_dest and os.path.exists(first_dest):
                subprocess.Popen([first_dest])
        except Exception:
            pass
        
        # 完成任务后立即退出，避免挂在后台
        sys.exit(0)

    except Exception as e:
        # Last resort: if we couldn't complete, print error and exit
        print(f"Updater helper error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
