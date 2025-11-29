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
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
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

            # 保存哈希信息到文件
            hash_info = f"""Stellaris DLC Helper v{VERSION} 发布包信息

文件名: {zip_name}
文件大小: {zip_size:.2f} MB
SHA256: {sha256_hash}
MD5: {md5_hash}

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            hash_file = self.project_root / f"Stellaris-DLC-Helper-v{VERSION}-checksums.txt"
            with open(hash_file, 'w', encoding='utf-8') as f:
                f.write(hash_info)

            print(f"校验文件已保存: {hash_file.name}")

            # 更新version.json中的checksum
            self._update_version_checksum(sha256_hash)

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
            self.cleanup()

            print("=" * 50)
            print("完整打包流程完成！")
            print("生成的文件：")
            zip_name = f"Stellaris-DLC-Helper-v{VERSION}.zip"
            checksum_name = f"Stellaris-DLC-Helper-v{VERSION}-checksums.txt"
            print(f"  📦 {zip_name}")
            print(f"  🔐 {checksum_name}")
            print(f"  📁 Stellaris-DLC-Helper/ (解压后的目录)")

        except Exception as e:
            print(f"打包失败: {e}")
            return False

        return True

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