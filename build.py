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
import json
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime

# 导入配置系统
sys.path.insert(0, str(Path(__file__).parent / "src"))
from src.config import VERSION, UPDATE_URL_BASE


class Packager:
    """打包器类"""

    def __init__(self, fast_mode=False):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "build_venv"
        self.dist_path = self.project_root / "dist"
        self.final_path = self.project_root / "Stellaris-DLC-Helper"
        self.fast_mode = fast_mode

    def create_venv(self):
        """创建虚拟环境（支持重用）"""
        print("检查虚拟环境...")

        # 检查虚拟环境是否已经存在且有效
        pip_exe = self.venv_path / "Scripts" / "pip.exe"
        python_exe = self.venv_path / "Scripts" / "python.exe"

        if self.venv_path.exists() and pip_exe.exists() and python_exe.exists():
            # 测试虚拟环境是否工作正常
            try:
                result = subprocess.run([str(python_exe), "-c", "import sys; print('OK')"],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and "OK" in result.stdout:
                    print("虚拟环境已存在且有效，跳过创建")
                    return
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass

        # 需要重新创建虚拟环境
        print("创建新的虚拟环境...")
        if self.venv_path.exists():
            shutil.rmtree(self.venv_path)
        venv.create(self.venv_path, with_pip=True)
        print("虚拟环境创建完成")

    def install_minimal_deps(self):
        """安装最小依赖（支持缓存）"""
        print("检查依赖安装...")
        pip_exe = self.venv_path / "Scripts" / "pip.exe"
        python_exe = self.venv_path / "Scripts" / "python.exe"

        # 从requirements-build.txt读取依赖
        requirements_file = self.project_root / "requirements-build.txt"
        deps = []

        if requirements_file.exists():
            with open(requirements_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        deps.append(line)
        else:
            # 后备依赖列表
            print("警告: 未找到requirements-build.txt，使用内置依赖列表")
            deps = [
                "requests>=2.28.0",
                "customtkinter>=5.2.0",
                "Pillow>=9.0.0",  # PIL
            ]

        # 检查依赖是否已安装
        missing_deps = []
        for dep in deps:
            # 提取包名（去掉版本要求）
            package_name = dep.split()[0].split('>=')[0].split('==')[0].split('<')[0].split('>')[0]
            try:
                result = subprocess.run([str(python_exe), "-c", f"import {package_name}; print('OK')"],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    missing_deps.append(dep)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ImportError):
                missing_deps.append(dep)

        if not missing_deps:
            print("所有依赖已安装，跳过安装步骤")
            return

        print(f"安装缺失的依赖 ({len(missing_deps)}个)...")
        for dep in missing_deps:
            print(f"安装 {dep}...")
            subprocess.run([str(pip_exe), "install", dep], check=True)

        print("依赖安装完成")

    def build_exe(self):
        """使用 PyInstaller 构建 exe（支持缓存）"""
        print("检查PyInstaller构建...")

        python_exe = self.venv_path / "Scripts" / "python.exe"

        # 检查PyInstaller是否已安装
        try:
            result = subprocess.run([str(python_exe), "-c", "import PyInstaller; print('OK')"],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise ImportError()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ImportError):
            print("安装 PyInstaller...")
            subprocess.run([str(python_exe), "-m", "pip", "install", "pyinstaller>=5.0.0"], check=True)

        # 检查是否需要重新构建（基于源文件变化）
        exe_path = self.dist_path / "Stellaris-DLC-Helper.exe"
        if exe_path.exists():
            # 获取源文件的最新修改时间
            src_mtime = self._get_src_max_mtime()
            exe_mtime = exe_path.stat().st_mtime

            if exe_mtime > src_mtime:
                print("exe文件已存在且是最新的，跳过构建")
                return

        print("构建 exe 文件...")

        # 使用自定义 spec 文件构建
        spec_file = self.project_root / "Stellaris-DLC-Helper.spec"
        if spec_file.exists():
            pyinstaller_cmd = [
                str(python_exe), "-m", "PyInstaller",
                str(spec_file)
            ]
        else:
            # 如果没有spec文件，使用基本命令
            print("未找到spec文件，使用基本PyInstaller命令...")
            # Windows下使用分号分隔路径
            separator = ";" if os.name == 'nt' else ":"
            pyinstaller_cmd = [
                str(python_exe), "-m", "PyInstaller",
                "--onefile",  # 打包成单个exe文件
                "--windowed",  # 不显示控制台窗口
                "--name", "Stellaris-DLC-Helper",
                "--add-data", f"{self.project_root}/src{separator}src",  # 添加src目录
                "--add-data", f"{self.project_root}/config{separator}config",  # 添加config目录
                "--add-data", f"{self.project_root}/assets{separator}assets",  # 添加assets目录
                "--hidden-import", "customtkinter",
                "--hidden-import", "PIL",
                "--hidden-import", "PIL.Image",
                "--hidden-import", "PIL.ImageTk",
                str(self.project_root / "main.py")  # 主入口文件
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
        readme_content = f"""Stellaris DLC Helper v{VERSION}

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

        # 生成 version.json 文件
        self._generate_version_json()

        print("文件组织完成")

    def _generate_version_json(self):
        """生成版本信息文件"""
        print("生成版本信息文件...")

        try:
            # 获取打包目录大小
            dir_size = self._get_dir_size(self.final_path)

            # 生成版本信息
            version_info = {
                "latest_version": VERSION,
                "force_update": False,
                "update_url": f"{UPDATE_URL_BASE}v{VERSION}/Stellaris-DLC-Helper-v{VERSION}.zip",
                "update_log": f"{UPDATE_URL_BASE}v{VERSION}/update.log",
                "min_version": VERSION,
                "release_date": datetime.now().strftime("%Y-%m-%d"),
                "file_size": f"{dir_size:.1f} MB",
                "checksum": ""  # 可以后续添加MD5校验
            }

            # 保存到打包目录
            version_path = self.final_path / "version.json"
            with open(version_path, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=2, ensure_ascii=False)

            print(f"版本信息文件已生成: {version_path}")

        except Exception as e:
            print(f"生成版本信息文件失败: {e}")

    def _get_dir_size(self, path):
        """获取目录大小（MB）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)

    def create_release_package(self):
        """创建发布压缩包"""
        print("创建发布压缩包...")

        try:
            # 压缩包名称
            zip_name = f"Stellaris-DLC-Helper-v{VERSION}.zip"
            zip_path = self.project_root / zip_name

            # 删除已存在的压缩包
            if zip_path.exists():
                zip_path.unlink()

            # 创建压缩包
            print(f"正在压缩到: {zip_name}")
            compression = zipfile.ZIP_STORED if self.fast_mode else zipfile.ZIP_DEFLATED
            with zipfile.ZipFile(zip_path, 'w', compression) as zipf:
                for root, dirs, files in os.walk(self.final_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.final_path)
                        zipf.write(file_path, arcname)

            # 计算文件大小和哈希
            zip_size = zip_path.stat().st_size / (1024 * 1024)  # MB

            # 计算SHA256哈希
            sha256_hash = self._calculate_file_hash(zip_path, 'sha256')
            md5_hash = self._calculate_file_hash(zip_path, 'md5')

            print(f"压缩包大小: {zip_size:.2f} MB")
            print(f"SHA256: {sha256_hash}")
            print(f"MD5: {md5_hash}")

            # 更新version.json中的checksum
            self._update_version_checksum(sha256_hash)

            # 清理中间文件
            print("清理中间文件...")
            self._cleanup_intermediate_files()

            return zip_path, zip_size, sha256_hash

        except Exception as e:
            print(f"创建压缩包失败: {e}")
            return None, 0, ""

    def _calculate_file_hash(self, file_path, algorithm='sha256'):
        """计算文件哈希值"""
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    def _update_version_checksum(self, sha256_hash):
        """更新version.json中的校验和"""
        try:
            version_path = self.final_path / "version.json"
            if version_path.exists():
                with open(version_path, 'r', encoding='utf-8') as f:
                    version_info = json.load(f)

                version_info["checksum"] = sha256_hash

                with open(version_path, 'w', encoding='utf-8') as f:
                    json.dump(version_info, f, indent=2, ensure_ascii=False)

                print("version.json 中的校验和已更新")
        except Exception as e:
            print(f"更新校验和失败: {e}")

    def _get_src_max_mtime(self):
        """获取源文件目录中的最新修改时间"""
        max_mtime = 0
        src_dirs = ["src", "main.py", "config.json.example"]

        for src_dir in src_dirs:
            src_path = self.project_root / src_dir
            if src_path.exists():
                if src_path.is_file():
                    max_mtime = max(max_mtime, src_path.stat().st_mtime)
                else:
                    for root, dirs, files in os.walk(src_path):
                        for file in files:
                            if file.endswith(('.py', '.json', '.txt', '.md')):
                                file_path = os.path.join(root, file)
                                max_mtime = max(max_mtime, os.path.getmtime(file_path))

        return max_mtime

    def _cleanup_intermediate_files(self):
        """清理打包过程中的中间文件"""
        try:
            # 删除构建目录
            if self.dist_path.exists():
                shutil.rmtree(self.dist_path)
                print("已删除 dist/ 目录")

            # 删除虚拟环境
            if self.venv_path.exists():
                shutil.rmtree(self.venv_path)
                print("已删除 build_venv/ 目录")

            # 删除spec文件
            spec_file = self.project_root / "Stellaris-DLC-Helper.spec"
            if spec_file.exists():
                spec_file.unlink()
                print("已删除 Stellaris-DLC-Helper.spec 文件")

            # 删除解压后的目录
            if self.final_path.exists():
                shutil.rmtree(self.final_path)
                print("已删除 Stellaris-DLC-Helper/ 目录")

        except Exception as e:
            print(f"清理中间文件时出错: {e}")

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
            self.create_release_package()
            # 注意：中间文件已在create_release_package中清理

            print("=" * 50)
            print("完整打包流程完成！")
            print("生成的文件：")
            zip_name = f"Stellaris-DLC-Helper-v{VERSION}.zip"
            print(f"  📦 {zip_name}")
            print("  💡 中间文件已自动清理")

        except Exception as e:
            print(f"打包失败: {e}")
            return False

        return True

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Stellaris DLC Helper 打包工具')
    parser.add_argument('--fast', action='store_true', help='启用快速模式（跳过压缩，构建更快但文件更大）')

    args = parser.parse_args()

    packager = Packager(fast_mode=args.fast)
    success = packager.package()

    if success:
        mode_desc = "快速模式" if args.fast else "标准模式"
        print(f"\n打包成功！（{mode_desc}）发布文件已生成在项目根目录。")
    else:
        print("\n打包失败！请检查错误信息。")
        sys.exit(1)


if __name__ == "__main__":
    main()