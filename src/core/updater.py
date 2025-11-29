#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新模块
负责检查、下载和应用程序更新
"""

import os
import json
import requests
import zipfile
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Any
import logging
from ..config import REQUEST_TIMEOUT, VERSION
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
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

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

    UPDATE_CHECK_URL = "https://dlc.dlchelper.top/update/version.json"
    UPDATE_CHECK_TIMEOUT = 15  # 更新检查超时时间（秒）

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_version = VERSION
        self.temp_dir = Path(tempfile.gettempdir()) / "StellarisUpdate"
        self.backup_dir = Path(PathUtils.get_cache_dir()) / "backup"

    def check_for_updates(self, callback: Callable[[Optional[UpdateInfo]], None]) -> None:
        """
        检查更新（异步）

        参数:
            callback: 回调函数，参数为 UpdateInfo 或 None（检查失败）
        """
        def _check():
            try:
                self.logger.info("开始检查更新...")
                response = requests.get(self.UPDATE_CHECK_URL, timeout=self.UPDATE_CHECK_TIMEOUT)
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

            # 下载文件
            response = requests.get(update_info.update_url, stream=True, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress_callback(downloaded_size, total_size)

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

            # 获取程序根目录
            app_root = Path(__file__).parent.parent.parent

            # 解压更新包到临时目录
            extract_dir = self.temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 找到解压后的程序目录（应该只有一个文件夹）
            extracted_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                self.logger.error("更新包中没有找到程序目录")
                return False

            new_app_dir = extracted_dirs[0]

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
            backup_dirs = sorted(self.backup_dir.glob("backup_*"), reverse=True)
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
            backup_name = f"backup_{self.current_version}_{PathUtils.get_timestamp()}"
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

            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.logger.info("临时文件清理完成")
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {e}")