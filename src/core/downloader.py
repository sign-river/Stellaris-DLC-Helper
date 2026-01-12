#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载模块
负责下载DLC文件，支持断点续传
"""

import os
import time
import hashlib
import requests
from ..config import REQUEST_TIMEOUT, CHUNK_SIZE
from ..utils import PathUtils


class DLCDownloader:
    """DLC下载器类（简化版 - 仅支持单源GitLink）"""
    
    def __init__(self, progress_callback=None):
        """
        初始化下载器
        
        参数:
            progress_callback: 进度回调函数 callback(downloaded, total, percent)
        """
        self.progress_callback = progress_callback
        self.paused = False
        self.stopped = False
        self.user_agent = 'Stellaris-DLC-Helper/2.0'
        
        # 创建会话以复用连接
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
    def pause(self):
        """暂停下载"""
        self.paused = True
        
    def resume(self):
        """恢复下载"""
        self.paused = False
        
    def stop(self):
        """停止下载"""
        self.stopped = True
        self.paused = False
        
    def close(self):
        """关闭下载器并释放会话"""
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except Exception:
                pass
    
    def download(self, url, dest_path, expected_hash: str = None, expected_size: int = None):
        """
        下载文件（支持断点续传）
        
        参数:
            url: 下载URL
            dest_path: 目标文件路径
            expected_hash: 预期的文件SHA256哈希（可选）
            expected_size: 预期的文件大小（字节，可选）
            
        返回:
            bool: 是否成功
            
        抛出:
            Exception: 下载失败
        """
        try:
            print(f"开始下载: {url}")
            result = self._download_single_attempt(url, dest_path, expected_size)
            
            # 验证哈希（如果提供）
            if result and expected_hash:
                ok = self._verify_file_hash(dest_path, expected_hash)
                if not ok:
                    raise Exception("校验失败: 文件哈希与期望值不匹配")
                print(f"✅ 文件校验通过: {dest_path}")
            
            return result
        except Exception as e:
            # 删除错误文件
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
            except Exception:
                pass
            raise Exception(f"下载失败: {str(e)}")
    
    def _download_single_attempt(self, url, dest_path, expected_size=None):
        """
        单次下载尝试（内部方法）
        
        参数:
            url: 下载URL
            dest_path: 目标文件路径
            expected_size: 预期的文件大小（字节，可选）
            
        返回:
            bool: 是否成功
            
        抛出:
            Exception: 下载失败
        """
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # 检查已下载的文件
        if os.path.exists(dest_path):
            existing_size = os.path.getsize(dest_path)
            if existing_size > 0:
                # 验证ZIP文件完整性
                try:
                    import zipfile
                    with zipfile.ZipFile(dest_path, 'r') as zip_ref:
                        # testzip()返回第一个损坏文件的名称，如果都正常则返回None
                        bad_file = zip_ref.testzip()
                        if bad_file is None:
                            print(f"✓ 文件已存在且完整 ({existing_size / 1024 / 1024:.2f} MB)，使用缓存")
                            return True
                        else:
                            print(f"⚠ ZIP文件损坏 (文件 {bad_file} 校验失败)，重新下载")
                except (zipfile.BadZipFile, Exception) as e:
                    print(f"⚠ ZIP文件无效或损坏 ({e})，重新下载")
                
                # 文件损坏，删除重新下载
                try:
                    os.remove(dest_path)
                except Exception as e:
                    print(f"⚠ 删除损坏文件失败: {e}")
            else:
                # 文件为空，删除重新下载
                print(f"⚠ 检测到空文件，将重新下载")
                try:
                    os.remove(dest_path)
                except Exception as e:
                    print(f"⚠ 删除空文件失败: {e}")
        
        # 配置请求头
        headers = {
            'User-Agent': self.user_agent,
        }
        
        # 发送请求（不使用Range）
        response = self.session.get(url, headers=headers, stream=True, timeout=30)
        
        # 处理响应状态
        if response.status_code != 200:
            raise Exception(f"HTTP错误: {response.status_code}")
        
        # 获取文件总大小（GitLink不返回Content-Length，使用expected_size）
        if 'Content-Length' in response.headers:
            total_size = int(response.headers['Content-Length'])
            print(f"✓ 从服务器获取文件大小: {total_size} bytes ({total_size/1024/1024:.1f} MB)")
        elif expected_size:
            total_size = expected_size
            print(f"✓ 使用预期文件大小: {total_size} bytes ({total_size/1024/1024:.1f} MB)")
        else:
            total_size = 0
            print(f"⚠ 警告: 无法获取文件大小，进度条将不可用")
        
        # 下载文件（始终从头开始）
        downloaded = 0
        start_time = time.time()
        last_update_time = start_time
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                # 检查停止标志
                if self.stopped:
                    raise Exception("下载已停止")
                
                # 检查暂停标志
                while self.paused and not self.stopped:
                    time.sleep(0.1)
                
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 更新进度（节流：每0.1秒更新一次）
                    current_time = time.time()
                    if current_time - last_update_time >= 0.1:
                        if self.progress_callback:
                            try:
                                percent = int(downloaded / total_size * 100) if total_size > 0 else 0
                                # 每5秒输出一次进度信息
                                if not hasattr(self, '_last_log_time'):
                                    self._last_log_time = 0
                                if current_time - self._last_log_time >= 5:
                                    print(f"进度: {percent}% ({downloaded}/{total_size})")
                                    self._last_log_time = current_time
                                # 注意：progress_callback的参数顺序是(percent, downloaded, total)
                                self.progress_callback(percent, downloaded, total_size)
                            except Exception:
                                pass
                        last_update_time = current_time
        
        # 最终进度更新
        if self.progress_callback:
            try:
                # 注意：progress_callback的参数顺序是(percent, downloaded, total)
                self.progress_callback(100, downloaded, total_size)
            except Exception:
                pass
        
        elapsed_time = time.time() - start_time
        speed_mb = downloaded / 1024 / 1024 / max(elapsed_time, 0.001)
        print(f"✅ 下载完成: {dest_path} (平均速度: {speed_mb:.2f} MB/s)")
        return True
    
    def _verify_file_hash(self, file_path, expected_hash):
        """
        验证文件哈希
        
        参数:
            file_path: 文件路径
            expected_hash: 期望的SHA256哈希值
            
        返回:
            bool: 是否匹配
        """
        if not expected_hash:
            return True
        
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            actual_hash = sha256.hexdigest()
            return actual_hash.lower() == expected_hash.lower()
        except Exception as e:
            print(f"哈希校验失败: {str(e)}")
            return False
    
    def download_dlc(self, dlc_name, url, dest_folder, expected_hash=None, expected_size=None):
        """
        下载单个DLC
        
        参数:
            dlc_name: DLC名称
            url: 下载URL
            dest_folder: 目标文件夹
            expected_hash: 预期的文件哈希（可选）
            expected_size: 预期的文件大小（字节，可选）
            
        返回:
            str: 下载文件的路径
        """
        # 确定目标文件名
        filename = url.split('/')[-1] if '/' in url else f"{dlc_name}.zip"
        dest_path = os.path.join(dest_folder, filename)
        
        try:
            self.download(url, dest_path, expected_hash, expected_size)
            return dest_path  # 返回文件路径而不是布尔值
        except Exception as e:
            raise Exception(f"下载DLC {dlc_name} 失败: {str(e)}")
