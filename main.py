#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stellaris DLC Helper - CustomTkinter 版本
主入口文件

作者: sign-river
许可证: MIT License
项目地址: https://github.com/sign-river/Stellaris-DLC-Helper
"""

import customtkinter as ctk
import logging
from src.utils.logging_setup import configure_basic_logging, get_default_log_file_path
from src.gui.main_window import MainWindowCTk


def main():
    """主函数"""
    # Configure basic logging for console and file (before creating UI)
    configure_basic_logging(log_to_file=True)
    logging.getLogger().info(f"日志文件路径: {get_default_log_file_path()}")

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
