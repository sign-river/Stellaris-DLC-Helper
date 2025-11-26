#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stellaris DLC Helper - 群星DLC一键解锁工具
主入口文件

作者: sign-river
许可证: MIT License
项目地址: https://github.com/sign-river/Stellaris-DLC-Helper
"""

import tkinter as tk
from src.gui import MainWindow


def main():
    """主函数"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
