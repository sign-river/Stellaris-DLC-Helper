#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stellaris DLC Helper - CustomTkinter 版本
主入口文件

作者: sign-river
许可证: MIT License
项目地址: https://github.com/sign-river/Stellaris-DLC-Helper
"""

import sys
import platform
import logging

# 尽早初始化日志系统，确保所有错误都能被记录
try:
    from src.utils.logging_setup import configure_basic_logging, get_default_log_file_path
    configure_basic_logging(log_to_file=True)
    logger = logging.getLogger(__name__)
except Exception as e:
    # 如果日志初始化失败，至少配置基础的控制台输出
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning(f"日志系统初始化失败: {e}")

# 检查操作系统
if platform.system() != "Windows":
    error_msg = f"不支持的操作系统: {platform.system()} {platform.release()}"
    logger.error(error_msg)
    logger.error("本工具目前仅实现了 Windows 平台的补丁功能")
    
    print("="*60)
    print("错误: 此程序仅支持 Windows 操作系统")
    print("="*60)
    print(f"检测到当前系统: {platform.system()} {platform.release()}")
    print("\n本工具目前仅实现了 Windows 平台的补丁功能。")
    print("\n如需支持其他系统，请在项目 GitHub 页面提交 Issue 或贡献代码:")
    print("https://github.com/sign-river/Stellaris-DLC-Helper/issues")
    print("="*60)
    
    # 尝试显示图形化错误提示
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "不支持的操作系统",
            f"此程序仅支持 Windows 操作系统\n\n"
            f"检测到当前系统: {platform.system()} {platform.release()}\n\n"
            f"本工具目前仅实现了 Windows 平台的补丁功能。"
        )
        root.destroy()
    except Exception as e:
        logger.warning(f"显示图形界面错误提示失败: {e}")
    
    sys.exit(1)

import customtkinter as ctk
from src.gui.main_window import MainWindowCTk
import os
from src import config as app_config
from src import config_loader


def main():
    """主函数"""
    # 日志系统已在模块顶部初始化
    try:
        logger.info(f"日志文件路径: {get_default_log_file_path()}")
    except:
        pass
    
    # 立即清理残留的 .new 文件（优先级最高，在任何其他操作之前）
    try:
        from pathlib import Path
        if getattr(sys, 'frozen', False):
            app_root = Path(sys.executable).parent
            new_files = list(app_root.glob('*.new'))
            
            if new_files:
                logger.info(f"发现 {len(new_files)} 个残留的 .new 文件")
                for new_file in new_files:
                    try:
                        target_name = new_file.name[:-4]  # 移除 .new
                        target_file = app_root / target_name
                        
                        # 不替换正在运行的主程序
                        if target_file.resolve() == Path(sys.executable).resolve():
                            logger.warning(f"跳过主程序: {target_file.name}")
                            continue
                        
                        # 执行替换
                        if target_file.exists():
                            backup = target_file.with_suffix(target_file.suffix + '.old')
                            target_file.rename(backup)
                            new_file.rename(target_file)
                            try:
                                backup.unlink()
                            except Exception:
                                pass
                            logger.info(f"✅ 已完成替换: {target_file.name}")
                        else:
                            new_file.rename(target_file)
                            logger.info(f"✅ 已恢复文件: {target_file.name}")
                            
                    except Exception as e:
                        logger.warning(f"处理 {new_file.name} 失败: {e}")
    except Exception as e:
        logger.warning(f"清理残留文件失败: {e}")

    # 记录运行时环境信息，帮助诊断打包后用户运行旧配置的问题
    try:
        logger.info(f"sys.executable: {sys.executable}")
        logger.info(f"当前工作目录: {os.getcwd()}")
        # config_loader 内部维护了用于加载的路径信息，尝试读取并记录
        try:
            cfg_path = getattr(config_loader, '_loader').config_path
            logger.info(f"使用的 config.json 路径: {cfg_path}")
            # 尝试记录关键配置字段以判断来源
            try:
                from src.config import DLC_SERVER_URL, DLC_INDEX_URL, VERSION
                logger.info(f"应用版本 (config.VERSION): {VERSION}")
                logger.info(f"DLC_SERVER_URL: {DLC_SERVER_URL}")
                logger.info(f"DLC_INDEX_URL: {DLC_INDEX_URL}")
            except Exception as e:
                logger.warning(f"读取配置关键字段失败: {e}")
        except Exception as e:
            logger.warning(f"无法获取 config loader 路径信息: {e}")
    except Exception as e:
        logger.warning(f"记录运行时环境信息失败: {e}")

    # 将运行时诊断信息写入 runtime_info.txt，分别写到 exe 目录和当前工作目录，便于用户上报
    try:
        from pathlib import Path
        import time
        exe_dir = Path(sys.executable).parent
        cwd = Path.cwd()
        # 缓存目录，优先写入到 Stellaris_DLC_Cache（或 config 指定的缓存名）
        try:
            cache_dir_name = getattr(app_config, 'CACHE_DIR_NAME', 'Stellaris_DLC_Cache')
        except Exception:
            cache_dir_name = 'Stellaris_DLC_Cache'
        cache_dir = cwd / cache_dir_name
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            cfg_path = getattr(config_loader, '_loader').config_path
        except Exception:
            cfg_path = "(unknown)"

        try:
            from src.config import DLC_SERVER_URL, DLC_INDEX_URL, VERSION
        except Exception:
            DLC_SERVER_URL = "(unknown)"
            DLC_INDEX_URL = "(unknown)"
            VERSION = "(unknown)"

        content_lines = [
            f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"sys.executable: {sys.executable}",
            f"exe_dir: {exe_dir}",
            f"cwd: {cwd}",
            f"config_path: {cfg_path}",
            f"VERSION: {VERSION}",
            f"DLC_SERVER_URL: {DLC_SERVER_URL}",
            f"DLC_INDEX_URL: {DLC_INDEX_URL}",
        ]
        # 写入到缓存目录的 runtime_info.txt
        try:
            out_path = cache_dir / "runtime_info.txt"
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_lines))
            logger.info(f"已写入运行时诊断文件: {out_path}")
        except Exception as e:
            logger.warning(f"写 runtime_info 到 {cache_dir} 失败: {e}")
    except Exception as e:
        logger.warning(f"生成 runtime_info.txt 失败: {e}")

    root = ctk.CTk()
    app = MainWindowCTk(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except ModuleNotFoundError as e:
        import tkinter as tk
        from tkinter import messagebox
        import sys
        logging.exception(f"程序启动失败: {e}")

        # 在遇到缺少模块时，提示用户尝试回滚更新（如果存在备份）
        try:
            from src.core.updater import AutoUpdater
            au = AutoUpdater()
            root = tk.Tk()
            root.withdraw()
            resp = messagebox.askyesno("启动失败", f"检测到缺失模块: {e}.\n是否尝试回滚到上一版本？")
            if resp:
                ok = au.rollback()
                if ok:
                    messagebox.showinfo("回滚成功", "已回滚到上一版本，请重新运行程序。")
                else:
                    messagebox.showerror("回滚失败", "回滚失败，请手动恢复或重新安装程序。")
            else:
                messagebox.showinfo("提示", "请手动恢复或重新安装程序。")
        except Exception as ex:
            logging.exception(f"自动回滚失败: {ex}")
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", f"程序无法自动恢复: {ex}")
        finally:
            try:
                sys.exit(1)
            except SystemExit:
                pass
