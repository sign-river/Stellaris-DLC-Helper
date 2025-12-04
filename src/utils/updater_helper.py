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
import logging

# 设置日志 - 写入操作日志目录
try:
    # 尝试写入 Stellaris_DLC_Cache/operation_logs 目录
    if getattr(sys, 'frozen', False):
        # 打包后的exe模式
        app_dir = os.path.dirname(sys.executable)
    else:
        # 开发模式
        app_dir = os.getcwd()
    
    log_dir = os.path.join(app_dir, 'Stellaris_DLC_Cache', 'operation_logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'updater_helper.log')
except Exception:
    # 如果失败，写入程序目录
    log_file = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd(), 'updater_helper.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 启动时记录日志位置
logging.info(f"日志文件位置: {log_file}")

# Windows 专属模块，仅在 Windows 系统导入
if platform.system() == "Windows":
    import ctypes
else:
    ctypes = None


def wait_for_pid(pid: int):
    """Wait for process with PID to exit using Windows API"""
    start_time = time.time()
    logging.info(f"[步骤1/4] 等待主程序退出 (PID={pid})...")
    
    if platform.system() != "Windows" or ctypes is None:
        # 非 Windows 系统的简单等待（实际上此工具不应在非 Windows 系统运行）
        logging.warning("非 Windows 系统，使用简单等待")
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
        elapsed = time.time() - start_time
        logging.info(f"进程 PID={pid} 未找到或已退出 (耗时 {elapsed:.2f}秒)")
        return
    
    # WAIT_INFINITE = 0xFFFFFFFF
    WAIT_INFINITE = 0xFFFFFFFF
    kernel32.WaitForSingleObject(handle, WAIT_INFINITE)
    kernel32.CloseHandle(handle)
    
    elapsed = time.time() - start_time
    logging.info(f"主程序已退出 (等待时间: {elapsed:.2f}秒)")


def wait_for_file_unlock(path: str):
    """Wait until the file can be replaced (no longer opened by another process)."""
    logging.info(f"等待文件解锁: {path}")
    # Try to open in exclusive mode by renaming to a temp name
    for i in range(60):  # wait up to 60s
        try:
            # Try to rename the file to itself (no-op) as a quick lock check
            if os.path.exists(path):
                tmp = path + '.locktest'
                os.replace(path, tmp)
                os.replace(tmp, path)
            logging.info(f"文件已解锁: {path}")
            return
        except Exception as e:
            if i % 10 == 0:  # 每10秒记录一次
                logging.debug(f"等待文件解锁... 尝试 {i+1}/60: {e}")
            time.sleep(1)
    logging.warning(f"等待文件解锁超时: {path}")
    # Give up


def main():
    logging.info("=" * 60)
    logging.info("Updater Helper 启动")
    logging.info("=" * 60)
    
    # 创建互斥锁，防止多个实例同时运行
    lock_file = None
    try:
        import tempfile
        lock_file = os.path.join(tempfile.gettempdir(), 'stellaris_updater_helper.lock')
        
        # 尝试创建锁文件
        if os.path.exists(lock_file):
            # 检查锁文件是否过期（超过5分钟）
            try:
                if time.time() - os.path.getmtime(lock_file) > 300:
                    logging.warning("发现过期的锁文件，删除并继续")
                    os.remove(lock_file)
                else:
                    logging.error("另一个 updater_helper 实例正在运行，退出")
                    sys.exit(1)
            except Exception:
                pass
        
        # 创建锁文件
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        logging.info(f"已创建互斥锁: {lock_file}")
    except Exception as e:
        logging.warning(f"创建互斥锁失败: {e}")
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, default=None, help='PID to wait for')
    parser.add_argument('--new', required=False, help='New file path (单文件替换)')
    parser.add_argument('--dst', required=False, help='Destination path (单文件替换)')
    parser.add_argument('--batch', required=False, help='批量替换文件的 JSON 列表路径')
    args = parser.parse_args()

    new = os.path.abspath(args.new) if args.new else None
    dst = os.path.abspath(args.dst) if args.dst else None
    batch = os.path.abspath(args.batch) if args.batch else None
    
    logging.info(f"参数: PID={args.pid}, New={new}, Dst={dst}, Batch={batch}")

    try:
        # 等待主程序退出
        if args.pid:
            wait_for_pid(args.pid)
        elif dst:
            # fallback: wait for file unlock
            wait_for_file_unlock(dst)
        else:
            # 如果没有指定 PID 或 dst，等待5秒
            logging.info("没有指定 PID 或目标文件，等待 5 秒...")
            time.sleep(5)

        # 如果传入了批处理文件，则按序替换
        if batch and os.path.exists(batch):
            logging.info(f"[步骤2/4] 读取批处理配置: {batch}")
            import json
            with open(batch, 'r', encoding='utf-8') as fh:
                pairs = json.load(fh)
            
            logging.info(f"[步骤3/4] 开始替换 {len(pairs)} 个文件...")
            success_count = 0
            total_start_time = time.time()
            
            for idx, p in enumerate(pairs):
                newp = os.path.abspath(p.get('new'))
                dstp = os.path.abspath(p.get('dst'))
                file_start_time = time.time()
                
                logging.info(f"  [{idx+1}/{len(pairs)}] 处理: {os.path.basename(newp)} -> {os.path.basename(dstp)}")
                
                # 跳过 updater_helper.exe 自身（无法替换正在运行的程序）
                if os.path.basename(dstp).lower() == 'updater_helper.exe':
                    logging.info(f"    ⊙ 跳过 updater_helper.exe（正在运行，保留 .new 文件供主程序启动时替换）")
                    # 保留 .new 文件，不删除，让主程序启动后替换
                    success_count += 1  # 计为成功
                    continue
                
                if not os.path.exists(newp):
                    logging.error(f"    ✖ 源文件不存在: {newp}")
                    continue
                
                replaced = False
                for attempt in range(10):  # 减少到10次重试，每次1秒，最多10秒
                    try:
                        if os.path.exists(dstp):
                            os.remove(dstp)
                        shutil.move(newp, dstp)
                        file_elapsed = time.time() - file_start_time
                        logging.info(f"    ✔ 替换成功 (尝试 {attempt+1} 次, 耗时 {file_elapsed:.2f}秒)")
                        replaced = True
                        success_count += 1
                        break
                    except Exception as e:
                        if attempt == 0:  # 第一次失败立即记录
                            logging.warning(f"    ⚠ 替换失败 (尝试 {attempt+1}/10): {e}")
                        elif attempt % 3 == 0:  # 之后每3次记录一次
                            logging.warning(f"    ⚠ 替换失败 (尝试 {attempt+1}/10): {e}")
                        time.sleep(1)
                
                if not replaced:
                    file_elapsed = time.time() - file_start_time
                    logging.error(f"    ✖ 替换失败，已重试10次 (耗时 {file_elapsed:.2f}秒): {newp} -> {dstp}")
            
            total_elapsed = time.time() - total_start_time
            logging.info(f"[步骤3/4] 批量替换完成: {success_count}/{len(pairs)} 成功 (总耗时 {total_elapsed:.2f}秒)")
            
            # 清理批处理配置文件
            try:
                os.remove(batch)
                logging.info(f"已清理批处理配置文件: {batch}")
            except Exception as e:
                logging.warning(f"清理批处理配置文件失败: {e}")
                
        elif new and dst:
            # 单文件替换
            logging.info(f"单文件替换: {new} -> {dst}")
            
            if not os.path.exists(new):
                logging.error(f"源文件不存在: {new}")
                sys.exit(1)
            
            replaced = False
            for attempt in range(10):  # 减少到10次重试
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                        logging.debug(f"已删除旧文件: {dst}")
                    shutil.move(new, dst)
                    logging.info(f"替换成功 (尝试 {attempt+1} 次)")
                    replaced = True
                    break
                except Exception as e:
                    if attempt == 0:
                        logging.warning(f"替换失败 (尝试 {attempt+1}/10): {e}")
                    elif attempt % 3 == 0:
                        logging.warning(f"替换失败 (尝试 {attempt+1}/10): {e}")
                    time.sleep(1)
            
            if not replaced:
                logging.error(f"替换失败，已重试10次")
                sys.exit(1)
        
        # 启动第一个被替换的目标（如果是 exe）以恢复运行
        try:
            logging.info("[步骤4/4] 准备启动新版本程序...")
            # 确定要启动的程序
            first_dest = None
            
            # 从已完成的替换中找到主程序
            if batch:
                # 批处理模式：已经在上面处理过了，batch文件已被清理
                # 需要找到主程序exe
                app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                main_exe = os.path.join(app_dir, 'Stellaris-DLC-Helper.exe')
                if os.path.exists(main_exe):
                    first_dest = main_exe
                    logging.info(f"  找到主程序: {main_exe}")
            elif dst and dst.endswith('.exe'):
                first_dest = dst
                logging.info(f"  找到目标程序: {dst}")
            
            if first_dest and os.path.exists(first_dest):
                logging.info(f"  启动程序: {first_dest}")
                # Windows: 隐藏窗口
                creationflags = 0
                if platform.system() == 'win32':
                    creationflags = 0x08000000  # CREATE_NO_WINDOW
                subprocess.Popen([first_dest], creationflags=creationflags)
                time.sleep(0.5)  # 等待程序启动
                logging.info("  ✔ 程序已启动")
            else:
                logging.warning(f"  ⚠ 未找到要启动的程序: {first_dest}")
        except Exception as e:
            logging.error(f"  ✖ 启动程序失败: {e}")
        
        logging.info("Updater Helper 完成")
        logging.info("=" * 60)
        
        # 清理互斥锁
        try:
            if lock_file and os.path.exists(lock_file):
                os.remove(lock_file)
                logging.info("已删除互斥锁")
        except Exception as e:
            logging.warning(f"删除互斥锁失败: {e}")
        
        # 完成任务后立即退出，避免挂在后台
        sys.exit(0)

    except Exception as e:
        # Last resort: if we couldn't complete, print error and exit
        logging.error(f"Updater helper 错误: {e}", exc_info=True)
        print(f"Updater helper error: {e}")
        
        # 清理互斥锁
        try:
            if lock_file and os.path.exists(lock_file):
                os.remove(lock_file)
        except Exception:
            pass
        
        sys.exit(1)


if __name__ == '__main__':
    main()
