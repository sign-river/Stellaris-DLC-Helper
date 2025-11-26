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
from src.gui.main_window import MainWindowCTk


def main():
    """主函数"""
    root = ctk.CTk()
    app = MainWindowCTk(root)
    root.mainloop()


if __name__ == "__main__":
    main()
