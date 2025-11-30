#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新模块
负责检查、下载和应用程序更新
"""

import requests
import zipfile
import shutil
import tempfile
import threading
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional
import logging
import hashlib
import os
import re
from ..config import REQUEST_TIMEOUT, VERSION, UPDATE_CHECK_URL, CHUNK_SIZE
from ..utils import PathUtils


class UpdateInfo:
    """更新信息类"""

    def __init__(self, data: dict):
        self.latest_version = data.get("latest_version", "")
        self.force_update = data.get("force_update", False)
        self.update_url = data.get("update_url", "")
        self.update_log_url = data.get("update_log", "")
        self.min_version = data.get("min_version", "")
        self.release_date = data.get("release_date", "")
        self.file_size = data.get("file_size", "")
        self.checksum = data.get("checksum", "")

    def has_update(self, current_version: str) -> bool:
        """检查是否有更新"""
        return self._compare_versions(current_version, self.latest_version) < 0

    def is_force_update(self, current_version: str) -> bool:
        """检查是否强制更新"""
        return self.force_update or self._compare_versions(current_version, self.min_version) < 0

    @staticmethod
    def _compare_versions(version1: str, version2: str) -> int:
        """比较版本号，返回 -1, 0, 1"""
        # Normalize: strip leading 'v' and parse numeric prefix of each segment
        def _parse(v: str):
            if not v:
                return []
            v = str(v).lower().lstrip('v')
            parts = []
            for seg in v.split('.'):
                m = re.match(r"(\d+)", seg)
                parts.append(int(m.group(1)) if m else 0)
            return parts

        v1_parts = _parse(version1)
        v2_parts = _parse(version2)

        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        return 0


class AutoUpdater:
    """自动更新器类"""

    UPDATE_CHECK_TIMEOUT = 15  # 更新检查超时时间（秒）

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_version = VERSION
        self.temp_dir = Path(tempfile.gettempdir()) / "StellarisUpdate"
        self.backup_dir = Path(PathUtils.get_cache_dir()) / "backup"
        self.exe_replacement_pending = False

    def check_for_updates(self, callback: Callable[[Optional[UpdateInfo]], None]) -> None:
        """
        检查更新（异步）

        参数:
            callback: 回调函数，参数为 UpdateInfo 或 None（检查失败）
        """
        def _check():
            try:
                self.logger.info("开始检查更新...")
                response = requests.get(UPDATE_CHECK_URL, timeout=self.UPDATE_CHECK_TIMEOUT)
                response.raise_for_status()

                data = response.json()
                update_info = UpdateInfo(data)

                if update_info.has_update(self.current_version):
                    self.logger.info(f"发现新版本: {update_info.latest_version}")
                    callback(update_info)
                else:
                    self.logger.info("当前已是最新版本")
                    callback(None)

            except Exception as e:
                self.logger.error(f"检查更新失败: {e}")
                callback(None)

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    def download_update(self, update_info: UpdateInfo,
                       progress_callback: Callable[[int, int], None]) -> Optional[Path]:
        """
        下载更新包

        参数:
            update_info: 更新信息
            progress_callback: 进度回调函数 (current, total)

        返回:
            下载文件的路径，失败返回 None
        """
        try:
            self.logger.info(f"开始下载更新包: {update_info.update_url}")

            # 确保临时目录存在
            self.temp_dir.mkdir(parents=True, exist_ok=True)

            # 下载文件名
            filename = f"Stellaris-DLC-Helper-v{update_info.latest_version}.zip"
            download_path = self.temp_dir / filename

            # 验证 update_url 格式与安全性
            if update_info.update_url:
                if not update_info.update_url.lower().startswith(("https://", "http://")):
                    self.logger.warning(f"更新 URL 格式异常: {update_info.update_url}")

            # 支持续传：如果已存在部分下载文件，尝试使用 Range 请求继续
            headers = {}
            existing_size = 0
            if download_path.exists():
                existing_size = download_path.stat().st_size
                # 如果已下载的文件与清单中 checksum 匹配，直接返回（不重复下载）
                if update_info.checksum:
                    try:
                        sha256_hash = hashlib.sha256()
                        with open(download_path, 'rb') as fh:
                            for block in iter(lambda: fh.read(4096), b""):
                                sha256_hash.update(block)
                        got_hash = sha256_hash.hexdigest()
                        expected = update_info.checksum.strip().lower()
                        if got_hash == expected:
                            self.logger.info(f"发现已完整下载的更新包: {download_path}")
                            return download_path
                    except Exception:
                        # 如果计算失败，继续下载/续传
                        existing_size = download_path.stat().st_size

            # 如果服务器支持 Range 或者已有部分文件，则设置 Range header
            if existing_size > 0:
                headers['Range'] = f'bytes={existing_size}-'
                mode = 'ab'
                downloaded_size = existing_size
                # 更新界面进度为已下载
                try:
                    progress_callback(downloaded_size, total_size)
                except Exception:
                    pass
            else:
                mode = 'wb'
                downloaded_size = 0

            # 发起请求（支持续传）
            response = requests.get(update_info.update_url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers)
            response.raise_for_status()

            # 根据响应判断 total size（如果是 206，则 Content-Range 可用）
            total_size = 0
            if 'content-range' in response.headers:
                # Content-Range: bytes 1234-5678/8901
                try:
                    content_range = response.headers.get('content-range')
                    total_size = int(content_range.split('/')[-1])
                except Exception:
                    total_size = int(response.headers.get('content-length', 0)) + existing_size
            else:
                total_size = int(response.headers.get('content-length', 0))

            # 如果已有文件已经满足 total_size，则直接返回（无需下载）
            try:
                if existing_size > 0 and total_size > 0 and existing_size >= total_size:
                    self.logger.info("发现已完整下载的更新包（通过大小判断）: {download_path}")
                    return download_path
            except Exception:
                pass

            # 如果服务器没有返回 206，并且有已存在文件，则重新下载完整文件（覆盖）
            if existing_size > 0 and response.status_code == 200:
                self.logger.info("服务器不支持续传，重新从头下载")
                mode = 'wb'
                downloaded_size = 0
            # 开始写入文件
            with open(download_path, mode) as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        try:
                            progress_callback(downloaded_size, total_size)
                        except Exception:
                            pass

            # 校验checksum（如果存在），优先使用sha256
            if update_info.checksum:
                sha256_hash = hashlib.sha256()
                with open(download_path, 'rb') as fh:
                    for block in iter(lambda: fh.read(4096), b""):
                        sha256_hash.update(block)
                got_hash = sha256_hash.hexdigest()
                expected = update_info.checksum.strip().lower()
                if got_hash != expected:
                    self.logger.error(f"更新包校验失败: 期望 {expected}，实际 {got_hash}")
                    try:
                        download_path.unlink()
                    except Exception:
                        pass
                    return None
            self.logger.info(f"更新包下载完成: {download_path}")
            return download_path

        except Exception as e:
            self.logger.error(f"下载更新包失败: {e}")
            return None

    def apply_update(self, zip_path: Path) -> bool:
        """
        应用更新

        参数:
            zip_path: 更新包路径

        返回:
            是否成功
        """
        try:
            self.logger.info("开始应用更新...")

            # 创建备份
            if not self._create_backup():
                return False

            def fetch_update_log(self, update_info: UpdateInfo, timeout: int = 10) -> Optional[str]:
                """获取更新日志内容（文本）"""
                if not update_info or not update_info.update_log_url:
                    return None
                try:
                    self.logger.info(f"获取更新日志: {update_info.update_log_url}")
                    r = requests.get(update_info.update_log_url, timeout=timeout)
                    r.raise_for_status()
                    return r.text
                except Exception as e:
                    self.logger.warning(f"获取更新日志失败: {e}")
                    return None

            # 获取程序根目录
            app_root = Path(__file__).parent.parent.parent

            # 解压更新包到临时目录
            extract_dir = self.temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            # 安全解压: 防止zip-slip（路径穿越）
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    # Skip directory entries
                    if member.endswith('/'):
                        continue
                    # Create full path and ensure it's within extract_dir
                    dest_path = extract_dir / member
                    dest_path_parent = dest_path.parent
                    if not str(dest_path.resolve()).startswith(str(extract_dir.resolve()) + os.sep):
                        self.logger.error(f"更新包包含非法路径: {member}")
                        return False
                zip_ref.extractall(extract_dir)

            # 找到解压后的程序目录：若ZIP中只包含单个顶层文件夹，使用它；否则使用整个 extract_dir
            extracted_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if len(extracted_dirs) == 1:
                new_app_dir = extracted_dirs[0]
            else:
                # ZIP 可能将文件平铺在根目录
                new_app_dir = extract_dir

            # 替换文件
            self._replace_files(app_root, new_app_dir)

            self.logger.info("更新应用成功")
            return True

        except Exception as e:
            self.logger.error(f"应用更新失败: {e}")
            # 尝试回滚
            self.rollback()
            return False

    def rollback(self) -> bool:
        """
        回滚到上一版本

        返回:
            是否成功
        """
        try:
            self.logger.info("开始回滚...")

            app_root = Path(__file__).parent.parent.parent

            # 查找最新的备份
            # 按修改时间排序，选择最新的备份
            backup_dirs = sorted(self.backup_dir.glob("backup_*"), key=lambda x: x.stat().st_mtime, reverse=True)
            if not backup_dirs:
                self.logger.error("没有找到备份文件")
                return False

            latest_backup = backup_dirs[0]

            # 恢复文件
            self._replace_files(app_root, latest_backup)

            self.logger.info("回滚成功")
            return True

        except Exception as e:
            self.logger.error(f"回滚失败: {e}")
            return False

    def _create_backup(self) -> bool:
        """创建当前版本的备份"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 清理旧备份，只保留最近3个
            self._cleanup_old_backups()

            app_root = Path(__file__).parent.parent.parent
            # 兼容性：如果 PathUtils 没有 get_timestamp 方法，则使用 datetime 生成安全时间戳
            try:
                timestamp = PathUtils.get_timestamp()
            except Exception:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_name = f"backup_{self.current_version}_{timestamp}"
            backup_path = self.backup_dir / backup_name

            # 复制需要备份的文件
            files_to_backup = [
                "Stellaris-DLC-Helper.exe",
                "src",
                "patches",
                "assets",
                "config",
                "libraries"
            ]

            for item in files_to_backup:
                src = app_root / item
                dst = backup_path / item
                if src.exists():
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)

            self.logger.info(f"备份创建成功: {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"创建备份失败: {e}")
            return False

    def _cleanup_old_backups(self) -> None:
        """清理旧备份，只保留最近3个"""
        try:
            backup_dirs = sorted(
                self.backup_dir.glob("backup_*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # 保留最近3个备份
            max_backups = 3
            if len(backup_dirs) > max_backups:
                for old_backup in backup_dirs[max_backups:]:
                    try:
                        shutil.rmtree(old_backup)
                        self.logger.debug(f"删除旧备份: {old_backup}")
                    except Exception as e:
                        self.logger.warning(f"删除旧备份失败 {old_backup}: {e}")
                        
        except Exception as e:
            self.logger.warning(f"清理旧备份时出错: {e}")

    def _replace_files(self, target_dir: Path, source_dir: Path) -> None:
        """替换文件"""
        for item in source_dir.iterdir():
            src = source_dir / item.name
            dst = target_dir / item.name

            # 防止路径穿越：确保目标路径位于 target_dir 下
            if not str(dst.resolve()).startswith(str(target_dir.resolve()) + os.sep):
                self.logger.warning(f"尝试写入目标目录以外的路径，跳过: {dst}")
                continue

            try:
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    # 若要替换的是 exe 文件，Windows 下可能无法直接覆盖正在运行的文件
                    if dst.suffix.lower() == '.exe':
                        try:
                            shutil.copy2(src, dst)
                        except (PermissionError, OSError):
                            # 写入临时 new 文件，并创建替换脚本在程序退出后完成替换
                            tmp_new = target_dir / (dst.name + '.new')
                            shutil.copy2(src, tmp_new)
                            self.logger.info(f"程序正在运行，已将新 exe 写为临时文件: {tmp_new}")
                            try:
                                self._create_replace_script(tmp_new, dst, owner_pid=os.getpid())
                            except Exception as e:
                                self.logger.warning(f"创建替换脚本失败: {e}")
                    else:
                        shutil.copy2(src, dst)
            except Exception as e:
                self.logger.warning(f"替换文件失败 {src} -> {dst}: {e}")

    def _create_replace_script(self, new_exe: Path, dst_exe: Path, owner_pid: int = None) -> None:
        """创建 Windows 批处理脚本用于等待主程序退出再替换 exe 并重启（或使用 helper exe）。"""
        try:
            # 使用随机或时间戳生成脚本名
            script_path = dst_exe.parent / f"apply_update_{int(time.time())}.bat"
        except Exception:
            script_path = dst_exe.parent / f"apply_update.bat"

        new_exe_abs = str(new_exe.resolve())
        dst_exe_abs = str(dst_exe.resolve())
        app_root = dst_exe.parent

        # 优先尝试使用 updater_helper.exe（更可靠），否则降级为批处理脚本
        helper_path = app_root / 'updater_helper.exe'
        if helper_path.exists():
            args = [str(helper_path), '--new', new_exe_abs, '--dst', dst_exe_abs]
            if owner_pid:
                args += ['--pid', str(owner_pid)]
            subprocess.Popen(args, cwd=str(app_root))
            try:
                self.exe_replacement_pending = True
            except Exception:
                pass
            return

        bat_content = (
            '@echo off\r\n'
            ':wait_loop\r\n'
            f'tasklist /FI "PID eq {owner_pid}" 2>NUL | find "{owner_pid}" >NUL\r\n' if owner_pid else f'tasklist /FI "IMAGENAME eq {dst_exe.name}" 2>NUL | find /I "{dst_exe.name}" >NUL\r\n'
            'IF %ERRORLEVEL%==0 (\r\n'
            '    timeout /T 1 /NOBREAK >nul\r\n'
            '    goto :wait_loop\r\n'
            ')\r\n'
            f'move /Y "{new_exe_abs}" "{dst_exe_abs}"\r\n'
            f'start "" "{dst_exe_abs}"\r\n'
            'del "%~f0"\r\n'
        )

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)

        # 标记 exe 替换已经计划
        try:
            self.exe_replacement_pending = True
        except Exception:
            pass

        # 启动脚本（新窗口）
        subprocess.Popen(['cmd', '/c', 'start', '""', str(script_path)], cwd=str(dst_exe.parent))

    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.logger.info("临时文件清理完成")
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {e}")