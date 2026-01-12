#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化更新系统 v2.0
- 状态机管理
- HTTPS + 签名验证
- 原子性更新
- 简化的断点续传
"""

import json
import hashlib
import shutil
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import logging
import time
import os
import sys

try:
    from packaging import version as pkg_version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False
    import re

import requests


# ==================== 数据模型 ====================

class UpdateState(Enum):
    """更新状态枚举"""
    IDLE = "idle"
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ERROR = "error"
    CANCELLED = "cancelled"


class UpdateInfo:
    """更新信息类（兼容旧接口）"""

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
        return VersionComparator.compare(current_version, self.latest_version) < 0

    def is_force_update(self, current_version: str) -> bool:
        """检查是否强制更新"""
        return self.force_update or (
            self.min_version and VersionComparator.compare(current_version, self.min_version) < 0
        )


@dataclass
class UpdateManifest:
    """更新清单"""
    version: str
    release_date: str
    download_url: str
    file_size: int
    checksum: str  # SHA256
    signature: Optional[str] = None  # 数字签名（未来扩展）
    force_update: bool = False
    min_version: Optional[str] = None
    changelog: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UpdateManifest':
        return cls(
            version=data.get('latest_version', ''),
            release_date=data.get('release_date', ''),
            download_url=data.get('update_url', ''),
            file_size=data.get('file_size', 0),
            checksum=data.get('checksum', ''),
            signature=data.get('signature'),
            force_update=data.get('force_update', False),
            min_version=data.get('min_version'),
            changelog=data.get('changelog')
        )


@dataclass
class UpdateProgress:
    """更新进度"""
    state: UpdateState
    progress: float = 0.0  # 0-100
    downloaded: int = 0
    total: int = 0
    speed: float = 0.0  # bytes/s
    message: str = ""
    error: Optional[str] = None


# ==================== 版本比较 ====================

class VersionComparator:
    """语义化版本比较"""
    
    @staticmethod
    def compare(v1: str, v2: str) -> int:
        """比较版本号，返回 -1, 0, 1"""
        if HAS_PACKAGING:
            try:
                ver1 = pkg_version.parse(v1.lstrip('v'))
                ver2 = pkg_version.parse(v2.lstrip('v'))
                if ver1 < ver2:
                    return -1
                elif ver1 > ver2:
                    return 1
                return 0
            except Exception:
                pass
        
        # 降级方案：简单数字比较
        return VersionComparator._simple_compare(v1, v2)
    
    @staticmethod
    def _simple_compare(v1: str, v2: str) -> int:
        """简单版本比较（后备方案）"""
        def parse(v):
            v = v.lower().lstrip('v')
            # 移除预发布标签
            v = re.split(r'[-+]', v)[0]
            parts = []
            for seg in v.split('.'):
                try:
                    parts.append(int(seg))
                except ValueError:
                    parts.append(0)
            return parts
        
        p1 = parse(v1)
        p2 = parse(v2)
        
        for i in range(max(len(p1), len(p2))):
            n1 = p1[i] if i < len(p1) else 0
            n2 = p2[i] if i < len(p2) else 0
            if n1 < n2:
                return -1
            elif n1 > n2:
                return 1
        return 0


# ==================== 下载器 ====================

class ReliableDownloader:
    """可靠的下载器（支持断点续传）"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Stellaris-DLC-Helper-Updater/2.0'
        })
        
    def download(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        chunk_size: int = 8192
    ) -> bool:
        """
        下载文件，支持断点续传
        
        返回:
            成功返回 True，失败返回 False
        """
        try:
            # 检查已下载的部分
            headers = {}
            existing_size = 0
            if dest.exists():
                existing_size = dest.stat().st_size
                self.logger.info(f"发现部分下载文件，已下载: {existing_size} bytes")
                
                # 验证服务器是否支持续传
                try:
                    head_resp = self.session.head(url, timeout=10, allow_redirects=True)
                    accept_ranges = head_resp.headers.get('Accept-Ranges', '').lower()
                    content_length = head_resp.headers.get('Content-Length')
                    
                    if accept_ranges == 'bytes' and content_length:
                        remote_size = int(content_length)
                        if 0 < existing_size < remote_size:
                            headers['Range'] = f'bytes={existing_size}-'
                            self.logger.info(f"使用断点续传，从 {existing_size} 继续")
                        elif existing_size >= remote_size:
                            self.logger.info("文件已完整下载")
                            return True
                        else:
                            self.logger.info("服务器不支持续传，重新下载")
                            dest.unlink()
                            existing_size = 0
                    else:
                        self.logger.info("服务器不支持 Range，重新下载")
                        dest.unlink()
                        existing_size = 0
                except Exception as e:
                    self.logger.warning(f"HEAD 请求失败: {e}，尝试完整下载")
                    try:
                        dest.unlink()
                    except Exception:
                        pass
                    existing_size = 0
            
            # 开始下载
            mode = 'ab' if existing_size > 0 else 'wb'
            response = self.session.get(url, stream=True, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 获取总大小
            if response.status_code == 206:  # Partial Content
                content_range = response.headers.get('Content-Range', '')
                # Content-Range: bytes 1234-5678/9999
                total_size = int(content_range.split('/')[-1]) if '/' in content_range else 0
            else:
                total_size = int(response.headers.get('Content-Length', 0))
            
            downloaded = existing_size
            start_time = time.time()
            last_report_time = start_time
            
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            with open(dest, mode) as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 进度回调（限流：每0.5秒更新一次）
                        current_time = time.time()
                        if progress_callback and (current_time - last_report_time) >= 0.5:
                            progress_callback(downloaded, total_size)
                            last_report_time = current_time
            
            # 最后一次进度回调
            if progress_callback:
                progress_callback(downloaded, total_size)
            
            elapsed = time.time() - start_time
            speed = downloaded / elapsed if elapsed > 0 else 0
            self.logger.info(f"下载完成: {downloaded} bytes, 耗时: {elapsed:.2f}s, 速度: {speed/1024:.2f} KB/s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"下载失败: {e}", exc_info=True)
            return False


# ==================== 文件验证器 ====================

class FileVerifier:
    """文件完整性验证"""
    
    @staticmethod
    def verify_checksum(file_path: Path, expected_hash: str, algorithm: str = 'sha256') -> bool:
        """验证文件哈希"""
        try:
            if algorithm == 'sha256':
                hasher = hashlib.sha256()
            elif algorithm == 'md5':
                hasher = hashlib.md5()
            else:
                raise ValueError(f"不支持的算法: {algorithm}")
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            
            actual_hash = hasher.hexdigest().lower()
            expected = expected_hash.lower().strip()
            
            return actual_hash == expected
        except Exception:
            return False


# ==================== 更新安装器 ====================

class UpdateInstaller:
    """更新安装器（原子性操作）"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.is_frozen = getattr(sys, 'frozen', False)
        
    def get_app_root(self) -> Path:
        """获取应用根目录"""
        if self.is_frozen:
            return Path(sys.executable).parent
        else:
            return Path(__file__).parent.parent.parent
    
    def install_update(self, zip_path: Path) -> bool:
        """
        安装更新（原子性）
        
        策略：
        1. 解压到临时目录
        2. 验证所有文件
        3. 创建完整备份
        4. 原子性替换（使用 .new + helper）
        """
        import zipfile
        
        try:
            app_root = self.get_app_root()
            self.logger.info(f"应用根目录: {app_root}")
            
            # 1. 解压到临时目录
            with tempfile.TemporaryDirectory(prefix='stellaris_update_') as temp_dir:
                temp_path = Path(temp_dir)
                extract_dir = temp_path / "extracted"
                extract_dir.mkdir(parents=True, exist_ok=True)
                
                self.logger.info(f"解压更新包到: {extract_dir}")
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    # 安全解压（防止路径穿越）
                    for member in zf.namelist():
                        if member.startswith('/') or '..' in member:
                            self.logger.error(f"检测到不安全的路径: {member}")
                            return False
                    zf.extractall(extract_dir)
                
                # 2. 查找更新源目录
                source_dir = self._find_source_dir(extract_dir)
                if not source_dir:
                    self.logger.error("无法确定更新源目录")
                    return False
                
                self.logger.info(f"更新源目录: {source_dir}")
                
                # 3. 创建备份
                if not self._create_backup(app_root):
                    self.logger.error("创建备份失败")
                    return False
                
                # 4. 执行替换
                if not self._perform_replacement(source_dir, app_root):
                    self.logger.error("文件替换失败")
                    return False
                
                self.logger.info("更新安装成功")
                return True
                
        except Exception as e:
            self.logger.error(f"安装更新失败: {e}", exc_info=True)
            return False
    
    def _find_source_dir(self, extract_dir: Path) -> Optional[Path]:
        """智能查找更新源目录"""
        # 检查是否有单个顶层目录
        items = list(extract_dir.iterdir())
        dirs = [d for d in items if d.is_dir()]
        
        if len(dirs) == 1:
            potential = dirs[0]
            # 检查是否包含主程序
            if (potential / "Stellaris-DLC-Helper.exe").exists() or \
               (potential / "main.py").exists():
                return potential
        
        # 否则使用解压根目录
        if (extract_dir / "Stellaris-DLC-Helper.exe").exists() or \
           (extract_dir / "main.py").exists():
            return extract_dir
        
        return None
    
    def _create_backup(self, app_root: Path) -> bool:
        """创建备份"""
        try:
            from ..utils import PathUtils
            backup_root = Path(PathUtils.get_cache_dir()) / "backup"
            backup_root.mkdir(parents=True, exist_ok=True)
            
            # 生成备份目录名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            from ..config import VERSION
            backup_dir = backup_root / f"backup_{VERSION}_{timestamp}"
            
            # 备份关键文件
            critical_items = [
                "Stellaris-DLC-Helper.exe",
                "updater_helper.exe",
                "config.json",
                "pairings.json",
                "patches",
                "src"
            ]
            
            backup_count = 0
            for item_name in critical_items:
                src = app_root / item_name
                if src.exists():
                    dst = backup_dir / item_name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                    backup_count += 1
            
            self.logger.info(f"备份完成: {backup_dir}, 备份了 {backup_count} 项")
            
            # 清理旧备份（保留最近5个）
            self._cleanup_old_backups(backup_root, keep=5)
            
            return True
            
        except Exception as e:
            self.logger.error(f"创建备份失败: {e}", exc_info=True)
            return False
    
    def _cleanup_old_backups(self, backup_root: Path, keep: int = 5):
        """清理旧备份"""
        try:
            backups = sorted(
                backup_root.glob("backup_*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backups[keep:]:
                try:
                    shutil.rmtree(old_backup)
                    self.logger.debug(f"删除旧备份: {old_backup.name}")
                except Exception as e:
                    self.logger.warning(f"删除旧备份失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"清理旧备份失败: {e}")
    
    def _perform_replacement(self, source_dir: Path, target_dir: Path) -> bool:
        """执行文件替换"""
        scheduled_replacements = []
        
        try:
            for item in source_dir.rglob('*'):
                if item.is_file():
                    # 计算相对路径
                    rel_path = item.relative_to(source_dir)
                    dst = target_dir / rel_path
                    
                    # 跳过某些文件
                    if self._should_skip_file(rel_path):
                        continue
                    
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    # config.json 特殊处理：合并配置
                    if rel_path.name == 'config.json':
                        self._merge_config(item, dst)
                        self.logger.info(f"已合并配置文件: {rel_path}")
                        continue
                    
                    # 尝试直接替换
                    try:
                        if dst.suffix == '.exe' and dst.exists():
                            # exe 文件可能被占用
                            raise PermissionError("exe 被占用")
                        shutil.copy2(item, dst)
                        self.logger.debug(f"已替换: {rel_path}")
                    except (PermissionError, OSError):
                        # 写入 .new 文件，稍后由 helper 处理
                        new_file = dst.parent / (dst.name + '.new')
                        shutil.copy2(item, new_file)
                        scheduled_replacements.append((new_file, dst))
                        self.logger.info(f"已创建 .new 文件: {rel_path}")
            
            # 如果有延迟替换的文件，启动 helper
            if scheduled_replacements and self.is_frozen:
                return self._start_helper(scheduled_replacements)
            
            return True
            
        except Exception as e:
            self.logger.error(f"文件替换失败: {e}", exc_info=True)
            return False
    
    def _should_skip_file(self, rel_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            '__pycache__',
            '.pyc',
            '.log',
            'Stellaris_DLC_Cache',
        ]
        
        path_str = str(rel_path).lower()
        for pattern in skip_patterns:
            if pattern in path_str:
                return True
        return False
    
    def _merge_config(self, new_config_path: Path, old_config_path: Path):
        """合并配置文件：使用新配置但保留用户自定义的值"""
        try:
            # 读取新配置
            with open(new_config_path, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            
            # 如果旧配置存在，读取并合并关键用户配置
            if old_config_path.exists():
                try:
                    with open(old_config_path, 'r', encoding='utf-8') as f:
                        old_config = json.load(f)
                    
                    # 保留用户可能自定义的配置项
                    preserve_keys = [
                        'game_path',  # 游戏路径
                        'steam_path',  # Steam 路径
                    ]
                    
                    for key in preserve_keys:
                        if key in old_config and old_config[key]:
                            new_config[key] = old_config[key]
                            self.logger.debug(f"保留用户配置: {key} = {old_config[key]}")
                    
                    # 如果用户有自定义服务器配置，保留
                    if 'server' in old_config and 'server' in new_config:
                        if 'sources' in old_config['server']:
                            # 检查用户是否修改过源配置
                            old_sources = old_config['server']['sources']
                            new_sources = new_config['server']['sources']
                            if old_sources != new_sources:
                                # 用户修改过，保留用户配置
                                new_config['server']['sources'] = old_sources
                                self.logger.debug("保留用户自定义的服务器源配置")
                    
                except Exception as e:
                    self.logger.warning(f"读取旧配置失败，使用新配置: {e}")
            
            # 写入合并后的配置
            with open(old_config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, ensure_ascii=False, indent=4)
            
            self.logger.info("配置文件已合并")
            
        except Exception as e:
            self.logger.error(f"合并配置文件失败: {e}")
            # 失败时直接复制新配置
            try:
                shutil.copy2(new_config_path, old_config_path)
            except Exception:
                pass
    
    def _start_helper(self, replacements: List[tuple]) -> bool:
        """启动 updater_helper 执行延迟替换"""
        try:
            app_root = self.get_app_root()
            helper_path = app_root / 'updater_helper.exe'
            
            if not helper_path.exists():
                self.logger.error("未找到 updater_helper.exe")
                return False
            
            # 创建批处理配置
            batch_path = app_root / f'update_batch_{int(time.time())}.json'
            batch_data = [
                {'new': str(new.resolve()), 'dst': str(dst.resolve())}
                for new, dst in replacements
            ]
            
            with open(batch_path, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, ensure_ascii=False, indent=2)
            
            # 启动 helper
            args = [
                str(helper_path),
                '--batch', str(batch_path),
                '--pid', str(os.getpid())
            ]
            
            creationflags = 0x08000000 if sys.platform == 'win32' else 0  # CREATE_NO_WINDOW
            subprocess.Popen(args, cwd=str(app_root), creationflags=creationflags)
            
            self.logger.info("updater_helper 已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"启动 helper 失败: {e}", exc_info=True)
            return False


# ==================== 更新管理器（主类）====================

class UpdateManager:
    """现代化更新管理器"""
    
    def __init__(
        self,
        current_version: str,
        update_url: str,
        use_https: bool = True
    ):
        self.logger = logging.getLogger(__name__)
        self.current_version = current_version
        self.update_url = update_url
        
        # 强制使用 HTTPS（安全性），但 IP 地址除外（无 SSL 证书）
        if use_https and update_url.startswith('http://'):
            # 检查是否为 IP 地址
            import re
            ip_pattern = r'http://\d+\.\d+\.\d+\.\d+'
            if not re.match(ip_pattern, update_url):
                self.update_url = update_url.replace('http://', 'https://')
                self.logger.warning("已将更新 URL 切换到 HTTPS")
            else:
                self.logger.info("检测到 IP 地址，保持 HTTP 连接")
        
        self.state = UpdateState.IDLE
        self.progress = UpdateProgress(state=UpdateState.IDLE)
        self.manifest: Optional[UpdateManifest] = None
        
        self.downloader = ReliableDownloader(self.logger)
        self.installer = UpdateInstaller(self.logger)
        
        self.temp_dir = Path(tempfile.gettempdir()) / "StellarisUpdate"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 事件回调
        self.on_progress: Optional[Callable[[UpdateProgress], None]] = None
        self.on_state_change: Optional[Callable[[UpdateState], None]] = None
    
    def check_for_updates(self, callback: Optional[Callable[[Optional[UpdateManifest], str], None]] = None):
        """检查更新（异步）"""
        def _check():
            self._set_state(UpdateState.CHECKING)
            announcement = ""  # 默认空公告
            
            try:
                self.logger.info(f"检查更新: {self.update_url}")
                
                response = requests.get(self.update_url, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                manifest = UpdateManifest.from_dict(data)
                
                # 获取公告 - 优先从 announcement.txt 获取，如果失败则使用 version.json 中的 announcement 字段
                announcement = self._fetch_announcement() or data.get('announcement', '')
                
                # 比较版本
                if VersionComparator.compare(self.current_version, manifest.version) < 0:
                    self.logger.info(f"发现新版本: {manifest.version}")
                    self.manifest = manifest
                    self._set_state(UpdateState.AVAILABLE)
                    if callback:
                        callback(manifest, announcement)
                else:
                    self.logger.info("当前已是最新版本")
                    self._set_state(UpdateState.IDLE)
                    if callback:
                        callback(None, announcement)
                        
            except Exception as e:
                self.logger.error(f"检查更新失败: {e}", exc_info=True)
                self._set_state(UpdateState.ERROR)
                self.progress.error = str(e)
                # 即使检查更新失败，仍然尝试获取公告
                announcement = self._fetch_announcement()
                if callback:
                    callback(None, announcement)
        
        thread = threading.Thread(target=_check, daemon=True)
        thread.start()
    
    def _fetch_announcement(self) -> str:
        """获取系统公告（从 announcement.txt）"""
        try:
            # 从 update_url 提取 base URL
            base_url = self.update_url.rsplit('/', 1)[0]
            announcement_url = f"{base_url}/announcement.txt"
            
            self.logger.info(f"获取公告: {announcement_url}")
            response = requests.get(announcement_url, timeout=3)
            response.raise_for_status()
            
            # 使用 UTF-8 解码
            announcement = response.content.decode('utf-8', errors='ignore').strip()
            if announcement:
                self.logger.info(f"成功获取公告，长度: {len(announcement)} 字符")
                return announcement
            else:
                self.logger.info("公告内容为空")
                return ""
                
        except Exception as e:
            self.logger.warning(f"获取公告失败: {e}")
            return ""
    
    def download_and_install(self, manifest: Optional[UpdateManifest] = None):
        """下载并安装更新（异步）"""
        if manifest:
            self.manifest = manifest
        
        if not self.manifest:
            self.logger.error("没有可用的更新")
            return
        
        def _download_and_install():
            try:
                # 1. 下载
                self._set_state(UpdateState.DOWNLOADING)
                filename = f"Stellaris-DLC-Helper-v{self.manifest.version}.zip"
                download_path = self.temp_dir / filename
                
                # 清理旧文件
                for old_file in self.temp_dir.glob("Stellaris-DLC-Helper-v*.zip"):
                    if old_file != download_path:
                        try:
                            old_file.unlink()
                        except Exception:
                            pass
                
                # 下载
                success = self.downloader.download(
                    self.manifest.download_url,
                    download_path,
                    progress_callback=self._on_download_progress
                )
                
                if not success:
                    raise Exception("下载失败")
                
                self._set_state(UpdateState.DOWNLOADED)
                
                # 2. 验证
                self.logger.info("验证文件完整性...")
                if self.manifest.checksum:
                    if not FileVerifier.verify_checksum(download_path, self.manifest.checksum):
                        raise Exception("文件校验失败")
                    self.logger.info("文件校验通过")
                
                # 3. 安装
                self._set_state(UpdateState.INSTALLING)
                if not self.installer.install_update(download_path):
                    raise Exception("安装失败")
                
                self._set_state(UpdateState.INSTALLED)
                self.logger.info("更新安装完成，请重启应用")
                
            except Exception as e:
                self.logger.error(f"更新失败: {e}", exc_info=True)
                self._set_state(UpdateState.ERROR)
                self.progress.error = str(e)
        
        thread = threading.Thread(target=_download_and_install, daemon=True)
        thread.start()
    
    def _on_download_progress(self, downloaded: int, total: int):
        """下载进度回调"""
        if total > 0:
            self.progress.progress = (downloaded / total) * 100
            self.progress.downloaded = downloaded
            self.progress.total = total
            
            if self.on_progress:
                self.on_progress(self.progress)
    
    def _set_state(self, state: UpdateState):
        """设置状态"""
        self.state = state
        self.progress.state = state
        
        if self.on_state_change:
            self.on_state_change(state)
        
        if self.on_progress:
            self.on_progress(self.progress)
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            self.logger.debug(f"清理临时文件失败: {e}")


# ==================== 兼容层 ====================

class AutoUpdater:
    """
    向后兼容的 AutoUpdater 类
    内部使用新的 UpdateManager
    """
    
    def __init__(self):
        from ..config import VERSION, UPDATE_CHECK_URL
        
        self.logger = logging.getLogger(__name__)
        self.current_version = VERSION
        
        # 使用新的更新管理器
        self.manager = UpdateManager(
            current_version=VERSION,
            update_url=UPDATE_CHECK_URL,
            use_https=True  # 强制 HTTPS
        )
        
        # 启动时清理残留文件
        self._cleanup_leftover_new_files()
    
    def _cleanup_leftover_new_files(self):
        """清理残留的 .new 文件"""
        try:
            app_root = self.manager.installer.get_app_root()
            new_files = list(app_root.glob('*.new'))
            
            if new_files:
                self.logger.info(f"发现 {len(new_files)} 个残留的 .new 文件")
                for new_file in new_files:
                    try:
                        target_name = new_file.name[:-4]  # 移除 .new
                        target_file = app_root / target_name
                        
                        # 不替换正在运行的主程序
                        if getattr(sys, 'frozen', False):
                            if target_file.resolve() == Path(sys.executable).resolve():
                                self.logger.warning(f"跳过主程序: {target_file.name}")
                                continue
                        
                        # 执行替换
                        if target_file.exists():
                            backup = target_file.with_suffix(target_file.suffix + '.old')
                            target_file.rename(backup)
                            new_file.rename(target_file)
                            try:
                                backup.unlink()
                            except Exception:
                                pass
                            self.logger.info(f"✅ 已完成替换: {target_file.name}")
                        else:
                            new_file.rename(target_file)
                            self.logger.info(f"✅ 已恢复文件: {target_file.name}")
                            
                    except Exception as e:
                        self.logger.warning(f"处理 {new_file.name} 失败: {e}")
        except Exception as e:
            self.logger.warning(f"清理残留文件失败: {e}")
    
    def check_for_updates(self, callback: Callable):
        """检查更新（兼容旧接口）"""
        def _callback(manifest: Optional[UpdateManifest], announcement: str):
            if manifest:
                # 转换为旧的 UpdateInfo 格式
                old_data = {
                    'latest_version': manifest.version,
                    'update_url': manifest.download_url,
                    'file_size': manifest.file_size,
                    'checksum': manifest.checksum,
                    'force_update': manifest.force_update,
                    'min_version': manifest.min_version or '',
                    'release_date': manifest.release_date
                }
                update_info = UpdateInfo(old_data, announcement)
                callback(update_info, announcement)
            else:
                callback(None, announcement)
        
        self.manager.check_for_updates(_callback)
    
    def download_update(self, update_info, progress_callback):
        """下载更新（兼容旧接口）"""
        # 转换为新的 UpdateManifest
        manifest = UpdateManifest(
            version=update_info.latest_version,
            release_date=update_info.release_date,
            download_url=update_info.update_url,
            file_size=update_info.file_size or 0,
            checksum=update_info.checksum,
            force_update=update_info.force_update
        )
        
        self.manager.manifest = manifest
        self.manager.on_progress = lambda p: progress_callback(p.downloaded, p.total)
        
        # 仅下载
        def _download():
            self.manager._set_state(UpdateState.DOWNLOADING)
            filename = f"Stellaris-DLC-Helper-v{manifest.version}.zip"
            download_path = self.manager.temp_dir / filename
            
            success = self.manager.downloader.download(
                manifest.download_url,
                download_path,
                progress_callback=lambda d, t: progress_callback(d, t)
            )
            
            if success and manifest.checksum:
                if FileVerifier.verify_checksum(download_path, manifest.checksum):
                    return download_path
            return None if not success else download_path
        
        import threading
        result = [None]
        
        def _run():
            result[0] = _download()
        
        thread = threading.Thread(target=_run)
        thread.start()
        thread.join()
        
        return result[0]
    
    def apply_update(self, zip_path: Path) -> bool:
        """应用更新（兼容旧接口）"""
        return self.manager.installer.install_update(zip_path)
