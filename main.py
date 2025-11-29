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
    main()
