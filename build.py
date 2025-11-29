#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stellaris DLC Helper 打包脚本
使用 PyInstaller 打包程序为独立 exe 文件

打包结构：
Stellaris-DLC-Helper/
├── Stellaris-DLC-Helper.exe  # 主程序
├── patches/                  # 补丁文件
│   └── cream_api.ini
├── config/                   # 配置文件
│   └── config.json
├── assets/                   # 资源文件
│   └── images/
│       └── README.md
├── libraries/                # 依赖库（可选）
└── Stellaris_DLC_Cache/      # 缓存目录（运行时创建）
"""

import os
import sys
import subprocess
import shutil
import venv
from pathlib import Path


class Packager:
    """打包器类"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "build_venv"
        self.dist_path = self.project_root / "dist"
        self.final_path = self.project_root / "Stellaris-DLC-Helper"

    def create_venv(self):
        """创建虚拟环境"""
        print("创建虚拟环境...")
        if self.venv_path.exists():
            shutil.rmtree(self.venv_path)
        venv.create(self.venv_path, with_pip=True)
        print("虚拟环境创建完成")

    def install_minimal_deps(self):
        """安装最小依赖"""
        print("安装最小依赖...")
        pip_exe = self.venv_path / "Scripts" / "pip.exe"

        # 安装核心依赖
        deps = [
            "requests>=2.28.0",
            "customtkinter>=5.2.0",
            "Pillow>=9.0.0",  # PIL
        ]

        for dep in deps:
            print(f"安装 {dep}...")
            subprocess.run([str(pip_exe), "install", dep], check=True)

        print("依赖安装完成")

    def build_exe(self):
        """使用 PyInstaller 构建 exe"""
        print("构建 exe 文件...")

        python_exe = self.venv_path / "Scripts" / "python.exe"

        # 首先安装 PyInstaller
        print("安装 PyInstaller...")
        subprocess.run([str(python_exe), "-m", "pip", "install", "pyinstaller>=5.0.0"], check=True)

        # 使用自定义 spec 文件构建
        spec_file = self.project_root / "Stellaris-DLC-Helper.spec"
        if spec_file.exists():
            pyinstaller_cmd = [
                str(python_exe), "-m", "PyInstaller",
                str(spec_file)
            ]
            # 在项目根目录运行 PyInstaller，确保 os.getcwd() 返回正确路径
            subprocess.run(pyinstaller_cmd, check=True, cwd=str(self.project_root))
        print("exe 构建完成")

    def organize_files(self):
        """组织最终文件结构"""
        print("组织文件结构...")

        # 创建最终目录
        if self.final_path.exists():
            shutil.rmtree(self.final_path)
        self.final_path.mkdir()

        # 移动 exe 文件
        exe_source = self.dist_path / "Stellaris-DLC-Helper.exe"
        exe_target = self.final_path / "Stellaris-DLC-Helper.exe"
        shutil.move(str(exe_source), str(exe_target))

        # 复制资源文件夹
        folders_to_copy = ["patches", "config", "assets"]
        for folder in folders_to_copy:
            src = self.project_root / folder
            dst = self.final_path / folder
            if src.exists():
                shutil.copytree(str(src), str(dst))

        # 创建 libraries 文件夹（可选，用于存放额外库）
        libraries_path = self.final_path / "libraries"
        libraries_path.mkdir(exist_ok=True)

        # 创建 README.txt
        readme_content = """Stellaris DLC Helper v1.0.0

使用说明：
1. 运行 Stellaris-DLC-Helper.exe
2. 选择您的 Stellaris 游戏目录
3. 选择要下载的 DLC
4. 点击"一键解锁"开始下载和安装

注意事项：
- 请确保网络连接正常
- 首次运行会自动创建缓存目录
- 如有问题请查看日志文件

技术支持：https://github.com/sign-river/Stellaris-DLC-Helper
"""
        readme_path = self.final_path / "README.txt"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print("文件组织完成")

    def cleanup(self):
        """清理临时文件"""
        print("清理临时文件...")
        if self.venv_path.exists():
            shutil.rmtree(self.venv_path)
        if self.dist_path.exists():
            shutil.rmtree(self.dist_path)
        spec_file = self.project_root / "Stellaris-DLC-Helper.spec"
        if spec_file.exists():
            spec_file.unlink()
        print("清理完成")

    def package(self):
        """执行完整打包流程"""
        try:
            print("开始打包 Stellaris DLC Helper...")
            print("=" * 50)

            self.create_venv()
            self.install_minimal_deps()
            self.build_exe()
            self.organize_files()
            self.cleanup()

            print("=" * 50)
            print("打包完成！")
            print(f"输出目录: {self.final_path}")
            print(f"文件大小: {self._get_dir_size(self.final_path):.2f} MB")

        except Exception as e:
            print(f"打包失败: {e}")
            return False

        return True

    def _get_dir_size(self, path):
        """获取目录大小（MB）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)


def main():
    """主函数"""
    packager = Packager()
    success = packager.package()

    if success:
        print("\n打包成功！您可以在 Stellaris-DLC-Helper 文件夹中找到可执行文件。")
    else:
        print("\n打包失败！请检查错误信息。")
        sys.exit(1)


if __name__ == "__main__":
    main()