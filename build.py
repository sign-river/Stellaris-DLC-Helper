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
├── config.json               # 配置文件
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
        self.cache_root = self.project_root / "Stellaris_DLC_Cache"
        self.venv_path = self.cache_root / "venv" / "build_venv"
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

        # 检查是否需要重新构建（基于源文件变化和构建配置）
        if not self._should_rebuild_exe():
            print("exe文件已存在且是最新的，跳过构建")
            # 如果 updater_helper 脚本存在但 helper exe 不存在，则尝试仅构建 helper
            helper_script = self.project_root / 'tools' / 'updater_helper.py'
            helper_exe = self.dist_path / 'updater_helper.exe'
            if helper_script.exists() and not helper_exe.exists():
                print('补充构建 updater_helper.exe...')
                helper_cmd = [
                    str(python_exe), '-m', 'PyInstaller',
                    '--onefile', '--name', 'updater_helper',
                    str(helper_script)
                ]
                subprocess.run(helper_cmd, check=True, cwd=str(self.project_root))
            return

        print("构建 exe 文件...")

        # 保存构建配置哈希
        config_hash_dir = self.cache_root / "config"
        config_hash_dir.mkdir(parents=True, exist_ok=True)
        config_hash_file = config_hash_dir / ".build_config_hash"
        current_hash = self._get_build_config_hash()
        with open(config_hash_file, 'w', encoding='utf-8') as f:
            f.write(current_hash)

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
            # 获取 tcl/tk 数据目录（修复 tkinter 打包问题）
            import tkinter
            import sys
            tcl_dir = None
            tk_dir = None
            try:
                # 尝试获取 tcl/tk 目录
                tkinter_path = Path(tkinter.__file__).parent
                tcl_candidates = [
                    tkinter_path / "tcl",
                    tkinter_path.parent / "tcl",
                    Path(sys.base_prefix) / "tcl"
                ]
                for candidate in tcl_candidates:
                    if candidate.exists():
                        # 查找 tcl8.x 和 tk8.x 目录
                        tcl_versions = list(candidate.glob("tcl8*"))
                        tk_versions = list(candidate.glob("tk8*"))
                        if tcl_versions:
                            tcl_dir = tcl_versions[0]
                        if tk_versions:
                            tk_dir = tk_versions[0]
                        if tcl_dir and tk_dir:
                            break
            except Exception as e:
                print(f"警告：无法自动检测 tcl/tk 目录: {e}")
            
            pyinstaller_cmd = [
                str(python_exe), "-m", "PyInstaller",
                "--onefile",  # 打包成单个exe文件
                "--windowed",  # 不显示控制台窗口
                "--name", "Stellaris-DLC-Helper",
                "--add-data", f"{self.project_root}/src{separator}src",  # 添加src目录
                "--add-data", f"{self.project_root}/config.json{separator}config.json",  # 添加config.json文件
                "--add-data", f"{self.project_root}/pairings.json{separator}pairings.json",  # 添加pairings.json文件
                "--add-data", f"{self.project_root}/assets{separator}assets",  # 添加assets目录
                # Pillow 的 C 扩展和插件在部分环境下不会被自动收集，显式收集以避免 _imaging 缺失
                "--collect-all", "PIL",
                # 收集 customtkinter 的主题与资源（blue.json 等）
                "--collect-all", "customtkinter",
                # 网络请求栈在一文件模式下常见缺失：明确收集 idna/charset_normalizer 子模块
                "--collect-submodules", "idna",
                "--collect-submodules", "charset_normalizer",
                "--hidden-import", "customtkinter",
                "--hidden-import", "PIL",
                "--hidden-import", "PIL.Image",
                "--hidden-import", "PIL._imaging",
                "--hidden-import", "PIL.ImageTk",
                "--hidden-import", "unicodedata",
                "--hidden-import", "idna",
                "--hidden-import", "charset_normalizer",
                str(self.project_root / "main.py")  # 主入口文件
            ]
            
            # 添加 tcl/tk 数据目录（修复 tkinter 打包问题）
            if tcl_dir and tcl_dir.exists():
                pyinstaller_cmd.extend(["--add-data", f"{tcl_dir}{separator}tcl"])
                print(f"添加 Tcl 数据目录: {tcl_dir}")
            if tk_dir and tk_dir.exists():
                pyinstaller_cmd.extend(["--add-data", f"{tk_dir}{separator}tk"])
                print(f"添加 Tk 数据目录: {tk_dir}")

        # 在项目根目录运行 PyInstaller，确保 os.getcwd() 返回正确路径
        subprocess.run(pyinstaller_cmd, check=True, cwd=str(self.project_root))
        # 额外构建：updater_helper 可执行程序（更稳定的替换器）
        helper_script = self.project_root / 'tools' / 'updater_helper.py'
        if helper_script.exists():
            print('正在构建 updater_helper.exe...')
            helper_cmd = [
                str(python_exe), '-m', 'PyInstaller',
                '--onefile', '--name', 'updater_helper',
                str(helper_script)
            ]
            subprocess.run(helper_cmd, check=True, cwd=str(self.project_root))
            # 多路径匹配：PyInstaller 可能生成 dist/updater_helper.exe 或 dist/updater_helper/updater_helper.exe
            # 通过 glob 搜索任何下层目录以找到最可能的 exe
            import glob
            helper_candidates = list(self.dist_path.glob('**/updater_helper.exe'))
            if not helper_candidates:
                # 没找到 helper 在 dist 中，尝试当前目录下的 dist/updater_helper.exe (fallback)
                fallback = self.dist_path / 'updater_helper.exe'
                if fallback.exists():
                    helper_candidates = [fallback]
            if helper_candidates:
                # 保留第一个匹配路径
                helper_exe_path = helper_candidates[0]
                print(f"找到并构建 helper: {helper_exe_path}")
            else:
                print('未在 dist 中找到 updater_helper.exe，构建可能失败')
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

        # 复制资源文件夹和文件
        folders_to_copy = ["patches", "assets"]
        for folder in folders_to_copy:
            src = self.project_root / folder
            dst = self.final_path / folder
            if src.exists():
                shutil.copytree(str(src), str(dst))
        
        # 复制配置文件与映射文件
        config_src = self.project_root / "config.json"
        config_dst = self.final_path / "config.json"
        if config_src.exists():
            shutil.copy2(str(config_src), str(config_dst))

        # 将 pairings.json 也复制到发布包中，方便外部修改/更新映射文件而无需重新打包
        pairings_src = self.project_root / "pairings.json"
        pairings_dst = self.final_path / "pairings.json"
        if pairings_src.exists():
            shutil.copy2(str(pairings_src), str(pairings_dst))

        # 创建 libraries 文件夹（可选，用于存放额外库）
        libraries_path = self.final_path / "libraries"
        libraries_path.mkdir(exist_ok=True)

        # 如果存在 helper exe，则复制到 release 根目录
        # 复制 helper_exe：支持 dist 下不同的生成路径
        from glob import glob
        helper_candidates = list(self.dist_path.glob('**/updater_helper.exe'))
        if helper_candidates:
            helper_exe = helper_candidates[0]
            shutil.copy2(str(helper_exe), str(self.final_path / "updater_helper.exe"))
        else:
            # 检查 fallback
            fallback = self.dist_path / 'updater_helper.exe'
            if fallback.exists():
                shutil.copy2(str(fallback), str(self.final_path / "updater_helper.exe"))

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

            # 创建压缩包（将文件放到 Stellaris-DLC-Helper 顶层文件夹中）
            print(f"正在压缩到: {zip_name}")
            compression = zipfile.ZIP_STORED if self.fast_mode else zipfile.ZIP_DEFLATED
            top_folder = "Stellaris-DLC-Helper"
            with zipfile.ZipFile(zip_path, 'w', compression) as zipf:
                for root, dirs, files in os.walk(self.final_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 在 ZIP 中添加顶层文件夹
                        rel_path = os.path.relpath(file_path, self.final_path)
                        arcname = os.path.join(top_folder, rel_path)
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

            # 跳过清理中间文件，保留 dist/ 与发布目录用于本地验证
            print("跳过清理中间文件，保留 dist/ 与发布目录用于验证")

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

    def _get_build_config_hash(self):
        """获取构建配置的哈希值"""
        config_parts = []

        # 添加版本号
        config_parts.append(f"version:{VERSION}")

        # 添加依赖列表
        requirements_file = self.project_root / "requirements-build.txt"
        if requirements_file.exists():
            with open(requirements_file, 'r', encoding='utf-8') as f:
                deps_content = f.read().strip()
                config_parts.append(f"deps:{deps_content}")

        # 添加构建脚本的哈希（前1000个字符）
        build_script = self.project_root / "build.py"
        if build_script.exists():
            with open(build_script, 'r', encoding='utf-8') as f:
                script_content = f.read()[:1000]  # 只取前1000字符
                config_parts.append(f"script:{hash(script_content)}")

        # 合并所有配置并计算哈希
        config_str = "|".join(config_parts)
        return hashlib.md5(config_str.encode()).hexdigest()

    def _should_rebuild_exe(self):
        """判断是否需要重新构建exe"""
        exe_path = self.dist_path / "Stellaris-DLC-Helper.exe"
        if not exe_path.exists():
            return True

        # 检查源文件修改时间
        src_mtime = self._get_src_max_mtime()
        exe_mtime = exe_path.stat().st_mtime

        if exe_mtime < src_mtime:
            return True

        # 检查构建配置哈希
        config_hash_file = self.cache_root / "config" / ".build_config_hash"
        current_hash = self._get_build_config_hash()

        if config_hash_file.exists():
            try:
                with open(config_hash_file, 'r', encoding='utf-8') as f:
                    saved_hash = f.read().strip()
                if saved_hash != current_hash:
                    return True
            except:
                return True
        else:
            return True

        return False

    def _cleanup_intermediate_files(self):
        """清理打包过程中的中间文件"""
        try:
            # 删除构建目录
            if self.dist_path.exists():
                shutil.rmtree(self.dist_path)
                print("已删除 dist/ 目录")

            # 注意：保留虚拟环境以实现缓存效果
            # 如需清理虚拟环境，请手动删除 Stellaris_DLC_Cache/venv/build_venv/ 目录

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
            print("  💡 中间文件已清理（保留虚拟环境以加速下次打包）")

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