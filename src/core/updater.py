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
from ..config import REQUEST_TIMEOUT, VERSION, UPDATE_CHECK_URL, ANNOUNCEMENT_URL, CHUNK_SIZE
from ..utils import PathUtils


class UpdateInfo:
    """更新信息类"""

    def __init__(self, data: dict, announcement: str = ""):
        self.latest_version = data.get("latest_version", "")
        self.force_update = data.get("force_update", False)
        self.update_url = data.get("update_url", "")
        self.min_version = data.get("min_version", "")
        self.release_date = data.get("release_date", "")
        self.file_size = data.get("file_size", "")
        self.checksum = data.get("checksum", "")
        self.announcement = announcement  # 公告内容

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

    def fetch_announcement(self, timeout: int = 10) -> str:
        """获取公告内容"""
        try:
            self.logger.info(f"获取公告: {ANNOUNCEMENT_URL}")
            response = requests.get(ANNOUNCEMENT_URL, timeout=timeout)
            response.raise_for_status()
            announcement = response.text.strip()
            self.logger.debug(f"公告内容长度: {len(announcement)}")
            return announcement
        except Exception as e:
            self.logger.warning(f"获取公告失败: {e}")
            return ""

    def check_for_updates(self, callback: Callable[[Optional[UpdateInfo], str], None]) -> None:
        """
        检查更新（异步），同时获取公告

        参数:
            callback: 回调函数，参数为 (UpdateInfo 或 None, 公告内容)
        """
        def _check():
            try:
                self.logger.info("开始检查更新...")
                
                # 并行获取更新信息和公告
                update_info = None
                announcement = ""
                
                # 获取更新信息
                try:
                    response = requests.get(UPDATE_CHECK_URL, timeout=self.UPDATE_CHECK_TIMEOUT)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    self.logger.warning(f"获取更新信息失败: {e}")
                    data = {}
                
                # 获取公告
                announcement = self.fetch_announcement()
                
                # 创建 UpdateInfo（即使没有更新也创建，用于传递公告）
                update_info = UpdateInfo(data, announcement)

                if update_info.has_update(self.current_version):
                    self.logger.info(f"发现新版本: {update_info.latest_version}")
                    callback(update_info, announcement)
                else:
                    self.logger.info("当前已是最新版本")
                    # 即使没有更新，如果有公告也要传递
                    callback(None, announcement)

            except Exception as e:
                self.logger.error(f"检查更新失败: {e}")
                # 失败时也尝试获取公告
                announcement = self.fetch_announcement()
                callback(None, announcement)

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
            # 如果服务器支持 Range 或者已有部分文件，则设置 Range header
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
            # 如果已有部分文件，试图判断服务器是否支持 Range，并校验远程文件大小
            mode = 'wb'
            downloaded_size = 0
            if existing_size > 0:
                # 尝试使用 HEAD 获取远程文件信息，以确认是否支持续传
                try:
                    head = requests.head(update_info.update_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                    head.raise_for_status()
                    accept_ranges = head.headers.get('accept-ranges', '').lower()
                    remote_size = None
                    if head.headers.get('content-length'):
                        try:
                            remote_size = int(head.headers.get('content-length'))
                        except Exception:
                            remote_size = None
                    # 记录服务器返回信息
                    self.logger.debug(f"远程文件接受续传: {accept_ranges}, 大小: {remote_size}")
                    # 如果远程文件大小已知并且本地已下载大小 >= 远端大小，尝试通过 checksum 判断是否完整
                    if remote_size is not None and existing_size >= remote_size:
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
                                pass
                        # 如果文件大小超过或等于远端但校验不通过，删除本地文件并从头开始
                        try:
                            download_path.unlink()
                            existing_size = 0
                        except Exception:
                            pass
                    # 若远端支持字节范围，则准备续传
                    if accept_ranges == 'bytes' and remote_size is not None and existing_size > 0:
                        headers['Range'] = f'bytes={existing_size}-'
                        mode = 'ab'
                        downloaded_size = existing_size
                    else:
                        # 未知是否支持续传，仍尝试以 head 检测到的不支持续传为准，从头下载
                        mode = 'wb'
                        downloaded_size = 0
                except Exception:
                    # 如果 HEAD 请求失败或解析出错，就以 GET 的方式尝试续传（原有逻辑），设置 Range 并处理可能的 416
                    headers['Range'] = f'bytes={existing_size}-'
                    mode = 'ab'
                    downloaded_size = existing_size
            # 发起请求（支持续传）。若 server 返回 416（Range Not Satisfiable），尝试删除本地续传文件并重试完整下载
            # 尝试请求与写入，遇到 416 时自动重试一次（删除本地部分文件后从头开始）
            attempts = 0
            max_attempts = 2
            response = None
            last_exception = None
            while attempts < max_attempts:
                try:
                    response = requests.get(update_info.update_url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers)
                    response.raise_for_status()
                    break
                except requests.exceptions.HTTPError as he:
                    last_exception = he
                    status_code = None
                    try:
                        status_code = he.response.status_code
                    except Exception:
                        status_code = None
                    if status_code == 416 and existing_size > 0:
                        self.logger.warning("服务器返回 416，续传不可用或本地文件与远端不一致，删除本地部分文件并重试")
                        try:
                            download_path.unlink()
                        except Exception:
                            pass
                        headers.pop('Range', None)
                        mode = 'wb'
                        downloaded_size = 0
                        existing_size = 0
                        # 改变条件，继续下一次重试
                        attempts += 1
                        continue
                    else:
                        raise
                except Exception as e:
                    last_exception = e
                    raise
            if response is None:
                # 如果超过重试但仍然没有 response，则抛出最后的异常
                if last_exception:
                    raise last_exception
                else:
                    raise RuntimeError("无法获取更新包，未知错误")
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

            # 在知道 total_size 后，若已有已下载的部分，更新进度回调显示当前进度
            try:
                if existing_size > 0:
                    progress_callback(existing_size, total_size)
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
        """替换文件
        替换策略：
        - 将解压目录中的文件复制到目标目录
        - 如果复制失败（例如文件被占用），则将新文件复制为 {filename}.new 并将其排入替换队列
        - 在循环结束后，如果替换队列不为空，则调用替换脚本/Helper 执行顺序替换
        """
        scheduled_replacements = []
        for item in source_dir.iterdir():
            src = source_dir / item.name
            dst = target_dir / item.name
            # 防止路径穿越：确保目标路径位于 target_dir 下
            if not str(dst.resolve()).startswith(str(target_dir.resolve()) + os.sep):
                self.logger.warning(f"尝试写入目标目录以外的路径，跳过: {dst}")
                continue

            try:
                if src.is_dir():
                    # 若存在同名目录，直接替换
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(src, dst)
                    except (PermissionError, OSError) as e:
                        # 无法覆盖时，写入 .new 并排程替换
                        try:
                            tmp_new = target_dir / (dst.name + '.new')
                            shutil.copy2(src, tmp_new)
                            scheduled_replacements.append((tmp_new, dst))
                            self.logger.info(f"文件被占用，已写入临时 new 并计划替换: {tmp_new} -> {dst}")
                        except Exception as ex:
                            self.logger.warning(f"写入临时 new 失败 {src} -> {tmp_new}: {ex}")
            except Exception as e:
                # 如果整个复制出错（例如权限、IO 等问题），尝试写入 .new 作为回退
                self.logger.debug(f"复制文件时异常，尝试写入 .new 作为回退: {src} -> {dst}: {e}")
                try:
                    tmp_new = target_dir / (dst.name + '.new')
                    shutil.copy2(src, tmp_new)
                    scheduled_replacements.append((tmp_new, dst))
                    self.logger.info(f"已将新文件写为临时 new 并计划替换: {tmp_new} -> {dst}")
                except Exception as ex:
                    self.logger.warning(f"回退：写入临时 new 失败 {src} -> {tmp_new}: {ex}")

        # 如果有待替换的文件，生成替换脚本/调用 helper 统一处理
        if scheduled_replacements:
            try:
                import sys
                # 仅在 exe 模式下才使用替换脚本
                is_frozen = getattr(sys, 'frozen', False)
                if is_frozen:
                    self._create_replace_script(scheduled_replacements, owner_pid=os.getpid())
                else:
                    # 开发环境下直接尝试覆盖（可能需要手动重启）
                    self.logger.warning("开发环境检测到待替换文件，请手动重启程序")
                    for new_file, dst_file in scheduled_replacements:
                        self.logger.info(f"待替换: {new_file} -> {dst_file}")
            except Exception as e:
                self.logger.warning(f"创建统一替换脚本失败: {e}")

    def _create_replace_script(self, new_dst_pairs, owner_pid: int = None) -> None:
        """创建 Windows 批处理脚本用于等待主程序退出再替换 exe 并重启（或使用 helper exe）。"""
        import sys
        # 仅在 exe 模式下使用此方法
        if not getattr(sys, 'frozen', False):
            self.logger.warning("_create_replace_script 仅在 exe 模式下使用")
            return
        
        # 使用第一个替换目标的 parent 作为默认目录
        first_dst = new_dst_pairs[0][1]
        try:
            # 使用随机或时间戳生成脚本名
            script_path = first_dst.parent / f"apply_update_{int(time.time())}.bat"
        except Exception:
            script_path = first_dst.parent / f"apply_update.bat"

        app_root = first_dst.parent

        # 优先尝试使用 updater_helper.exe（更可靠），否则降级为批处理脚本
        helper_path = app_root / 'updater_helper.exe'
        # 如果 helper 存在，优先使用 helper 处理所有替换，写入 batch.json 并一次性调用 helper
        if helper_path.exists():
            try:
                batch_path = app_root / f'apply_update_batch_{int(time.time())}.json'
                batch_list = []
                for new_exe, dst_exe in new_dst_pairs:
                    batch_list.append({
                        'new': str(new_exe.resolve()),
                        'dst': str(dst_exe.resolve())
                    })
                import json
                with open(batch_path, 'w', encoding='utf-8') as bf:
                    json.dump(batch_list, bf, ensure_ascii=False, indent=2)
                args = [str(helper_path), '--batch', str(batch_path)]
                if owner_pid:
                    args += ['--pid', str(owner_pid)]
                subprocess.Popen(args, cwd=str(app_root))
            except Exception as e:
                self.logger.warning(f"启动 updater_helper (batch) 失败: {e}")
            try:
                self.exe_replacement_pending = True
            except Exception:
                pass
            return

        bat_content = '@echo off\r\n'
        bat_content += ':wait_loop\r\n'
        if owner_pid:
            bat_content += f'tasklist /FI "PID eq {owner_pid}" 2>NUL | find "{owner_pid}" >NUL\r\n'
        else:
            # 如果没有 pid，则等待旧 exe 不再出现在进程列表（基于镜像名称）
            bat_content += f'tasklist /FI "IMAGENAME eq {first_dst.name}" 2>NUL | find /I "{first_dst.name}" >NUL\r\n'
        bat_content += 'IF %ERRORLEVEL%==0 (\r\n'
        bat_content += '    timeout /T 1 /NOBREAK >nul\r\n'
        bat_content += '    goto :wait_loop\r\n'
        bat_content += ')\r\n'
        # 在等待主程序退出后，按序将所有 new 文件替换到目标位置并尝试启动主 exe
        for new_exe, dst_exe in new_dst_pairs:
            new_exe_abs = str(Path(new_exe).resolve())
            dst_exe_abs = str(Path(dst_exe).resolve())
            bat_content += f'move /Y "{new_exe_abs}" "{dst_exe_abs}"\r\n'
        # 启动目标 exe（第一个替换目标若为 exe）
        first_dst_abs = str(first_dst.resolve())
        bat_content += f'start "" "{first_dst_abs}"\r\n'
        bat_content += 'del "%~f0"\r\n'

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)

        # 标记 exe 替换已经计划
        try:
            self.exe_replacement_pending = True
        except Exception:
            pass

        # 启动脚本（新窗口）
        subprocess.Popen(['cmd', '/c', 'start', '""', str(script_path)], cwd=str(first_dst.parent))

    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.logger.info("临时文件清理完成")
        except Exception as e:
            # 临时目录可能还在被占用（如 PyInstaller 的 _MEI 目录），静默忽略
            self.logger.debug(f"清理临时文件失败（可忽略）: {e}")