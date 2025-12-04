#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载模块
负责下载DLC文件，支持断点续传和智能速度监控
"""

import os
import time
import requests
from ..config import REQUEST_TIMEOUT, CHUNK_SIZE, RETRY_TIMES
from ..utils import PathUtils


class SpeedTooSlowException(Exception):
    """速度过慢异常，用于触发智能切源"""
    def __init__(self, message, new_url, new_source):
        super().__init__(message)
        self.new_url = new_url
        self.new_source = new_source


class DLCDownloader:
    """DLC下载器类"""
    
    def __init__(self, progress_callback=None):
        """
        初始化下载器
        
        参数:
            progress_callback: 进度回调函数 callback(percent, downloaded, total)
        """
        from ..config import SPEED_MONITOR_ENABLED
        
        self.progress_callback = progress_callback
        self.paused = False  # 暂停标志
        self.stopped = False  # 停止标志
        
        # 创建SourceManager实例用于检查启用的源
        from .source_manager import SourceManager
        self.source_manager = SourceManager()
        
        # 全局配置
        self._speed_monitor_enabled = SPEED_MONITOR_ENABLED  # 从配置读取
        self._speed_check_interval = 3.0  # 速度检查间隔（3秒）
        
        # DLC级别的状态（每次下载时重置）
        self._current_dlc_state = None  # 当前DLC的下载状态
        
        # 创建会话以复用连接
        self.session = requests.Session()
        # 设置合理的超时和重试
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0,  # 我们自己处理重试
            pool_block=False
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
        # 注意：不在 stop 中关闭 session，这样可在切换后进行重试
        # 如果需要彻底释放资源，请调用 close()

    def close(self):
        """彻底关闭下载器并释放会话"""
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except Exception:
                pass
    
    def _init_dlc_download_state(self):
        """初始化单个DLC的下载状态（每次下载DLC前调用）"""
        self._current_dlc_state = {
            'speed_samples': [],  # 速度采样 [(timestamp, bytes_downloaded), ...]
            'last_speed_check_time': 0,  # 上次速度检查时间
            'slow_speed_duration': 0,  # 慢速持续时间
            'download_start_time': time.time(),  # DLC下载开始时间
            'last_data_time': time.time(),  # 最后一次收到数据的时间
            'total_downloaded': 0,  # 当前DLC已下载的总字节数
        }
    
    def _reset_dlc_download_state(self):
        """重置DLC下载状态（切换源时调用）"""
        if self._current_dlc_state:
            self._current_dlc_state['speed_samples'] = []
            self._current_dlc_state['last_speed_check_time'] = time.time()
            self._current_dlc_state['slow_speed_duration'] = 0
            self._current_dlc_state['last_data_time'] = time.time()
    
    def _check_speed_and_switch(self, current_downloaded, current_time, fallback_urls, current_source_name):
        """
        检查下载速度，如果过慢则返回建议切换的源（基于当前DLC的状态）
        
        参数:
            current_downloaded: 当前DLC已下载字节数（仅本次尝试）
            current_time: 当前时间戳
            fallback_urls: 备用URL列表
            current_source_name: 当前源名称
            
        返回:
            tuple: (should_switch, new_url, new_source_name) 或 (False, None, None)
        """
        if not self._speed_monitor_enabled or not fallback_urls or not self._current_dlc_state:
            return False, None, None
        
        state = self._current_dlc_state
        
        # 添加速度采样点（使用DLC级别的总下载量）
        state['speed_samples'].append((current_time, state['total_downloaded']))
        
        # 只保留最近60秒的采样
        cutoff_time = current_time - 60
        state['speed_samples'] = [(t, b) for t, b in state['speed_samples'] if t >= cutoff_time]
        
        # 需要至少10秒的数据才能判断
        if len(state['speed_samples']) < 2:
            return False, None, None
        
        time_span = current_time - state['speed_samples'][0][0]
        if time_span < 10:
            return False, None, None
        
        # 计算平均速度（MB/s）
        bytes_delta = state['total_downloaded'] - state['speed_samples'][0][1]
        avg_speed_mb = (bytes_delta / 1024 / 1024) / time_span
        
        # 检查速度阈值（考虑Gitee稳定2-3 MB/s）
        # 如果速度持续低于1.0 MB/s（低于Gitee下限），持续20秒以上
        SLOW_THRESHOLD = 1.0  # MB/s
        SLOW_DURATION_THRESHOLD = 20  # 秒
        
        if avg_speed_mb < SLOW_THRESHOLD:
            state['slow_speed_duration'] += (current_time - state['last_speed_check_time'])
            
            if state['slow_speed_duration'] >= SLOW_DURATION_THRESHOLD:
                # 速度过慢，需要切源
                # 检查是否在缓存有效期内（5分钟）
                current_timestamp = time.time()
                cache_valid = False
                
                if hasattr(self.source_manager, '_last_best_timestamp'):
                    cache_age = current_timestamp - self.source_manager._last_best_timestamp
                    if cache_age < self.source_manager._cache_validity:
                        cache_valid = True
                
                if cache_valid:
                    # 使用缓存的速度信息选择次优源
                    speed_cache = getattr(self.source_manager, '_speed_cache', {})
                    available_sources = []
                    
                    for url, source_name in fallback_urls:
                        if source_name != current_source_name and source_name in speed_cache:
                            speed, _ = speed_cache[source_name]
                            available_sources.append((speed, url, source_name))
                    
                    if available_sources:
                        # 选择缓存中速度最快的源
                        available_sources.sort(key=lambda x: x[0], reverse=True)
                        best_speed, best_url, best_source = available_sources[0]
                        
                        # 只有当备选源速度明显更快时才切换（至少快50%）
                        if best_speed > avg_speed_mb * 1.5:
                            self._log_message(f"⚠️ 检测到速度过慢 ({avg_speed_mb:.2f} MB/s)，切换到更快的源: {best_source} (缓存速度: {best_speed:.2f} MB/s)")
                            self._reset_dlc_download_state()  # 重置DLC级别状态
                            return True, best_url, best_source
                else:
                    # 缓存过期，重新测速选择最佳源
                    self._log_message(f"⚠️ 检测到速度过慢 ({avg_speed_mb:.2f} MB/s)，重新测速选择最佳源...")
                    
                    try:
                        # 使用缓存机制避免频繁测速
                        best_source, test_url = self.source_manager.get_best_download_source(
                            silent=False,
                            log_callback=self._get_log_callback(),
                            force_retest=False  # 使用缓存
                        )
                        
                        # 从fallback_urls中找到对应的URL
                        for url, source_name in fallback_urls:
                            if source_name == best_source:
                                self._log_message(f"✅ 切换到测速最优源: {best_source}")
                                self._reset_dlc_download_state()  # 重置DLC级别状态
                                return True, url, best_source
                    except Exception as e:
                        self._log_message(f"❌ 重新测速失败: {e}")
        else:
            # 速度正常，重置慢速计时器
            state['slow_speed_duration'] = 0
            state['slow_speed_duration'] = 0
        
        state['last_speed_check_time'] = current_time
        return False, None, None
    
    def _log_message(self, message):
        """输出日志消息"""
        print(message)
        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
            try:
                self.progress_callback.log_message(message)
            except Exception:
                pass
    
    def _get_log_callback(self):
        """获取日志回调函数"""
        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
            return self.progress_callback.log_message
        return None
    
    def download(self, url, dest_path, fallback_urls=None, expected_hash: str = None, primary_source_name: str = None):
        """
        下载文件（支持断点续传、重试、多源fallback和智能速度监控切源）
        
        参数:
            url: 主下载URL
            dest_path: 目标文件路径
            fallback_urls: 备用URL列表（可选）
            
        返回:
            bool: 是否成功
            
        抽出:
            Exception: 下载失败
        """
        # 初始化当前DLC的下载状态
        self._init_dlc_download_state()
        
        # 使用所有URL，但只尝试启用的源
        urls_to_try = []
        # 添加主 URL（如果指定 primary_source_name，则附带源名称）
        if primary_source_name:
            urls_to_try.append((url, primary_source_name))
        else:
            urls_to_try.append((url, None))

        if fallback_urls:
            # 检查哪些源是启用的
            enabled_source_names = set()
            if hasattr(self, 'source_manager') and self.source_manager:
                enabled_sources = self.source_manager.get_enabled_sources()
                enabled_source_names = {s.get("name") for s in enabled_sources}
            
            # 只添加启用的源
            for url, source_name in fallback_urls:
                if source_name in enabled_source_names:
                    urls_to_try.append((url, source_name))
        
        # 如果没有启用的源可用（按 enable 检查），确保有 perferred main url尝试
        if not urls_to_try:
            urls_to_try = [(url, primary_source_name or "domestic_cloud")]  # 默认使用国内云
        
        last_exception = None
        
        # 尝试每个URL
        for current_url, source_name in urls_to_try:
            try:
                print(f"尝试从 {source_name} 下载...")
                # 记录完整 URL 到日志（有助于调试 URL 映射是否正确）
                print(f"尝试 URL: {current_url}")
                # 如果有UI回调，更新当前下载源显示
                if hasattr(self, 'progress_callback') and self.progress_callback:
                    # 确保progress_callback已初始化
                    if not hasattr(self.progress_callback, 'update_source'):
                        # 调用一次progress_callback来初始化它
                        try:
                            self.progress_callback(0, 0, 100)
                        except:
                            pass  # 忽略初始化错误
                    
                    # 现在调用update_source
                    if hasattr(self.progress_callback, 'update_source'):
                        # 源名称映射为用户友好的显示名称
                        display_name = {
                            "r2": "R2云存储",
                            "domestic_cloud": "国内云服务器", 
                            "gitee": "Gitee",
                            "github": "GitHub"
                        }.get(source_name, source_name)
                        self.progress_callback.update_source(display_name)
                
                # 尝试下载（可能抛出SpeedTooSlowException）
                result = self._download_single_attempt(current_url, dest_path, fallback_urls, source_name)
                
                # 验证哈希（如果提供）
                if result and expected_hash:
                    try:
                        ok = self._verify_file_hash(dest_path, expected_hash)
                        if not ok:
                            # 校验失败，记录并抛出错误以便 trigger fallback
                            raise Exception("校验失败: 文件哈希与期望值不匹配")
                        # 校验通过日志
                        try:
                            if hasattr(self, 'progress_callback') and getattr(self.progress_callback, 'log_message', None):
                                self.progress_callback.log_message(f"文件校验通过: {dest_path}")
                        except Exception:
                            pass
                    except Exception as e:
                        # 删除错误文件并尝试下一源
                        try:
                            if os.path.exists(dest_path):
                                os.remove(dest_path)
                        except Exception:
                            pass
                        raise
                return result
            except SpeedTooSlowException as e:
                # 速度过慢，智能切换到建议的源
                self._log_message(f"💨 {str(e)}")
                # 将建议的源插入到尝试列表的最前面（下次循环时使用）
                suggested_url = e.new_url
                suggested_source = e.new_source
                
                # 从urls_to_try中移除已尝试的当前源
                remaining_urls = [(u, s) for u, s in urls_to_try if s != source_name]
                
                # 将建议源插入到最前面
                urls_to_try = [(suggested_url, suggested_source)] + remaining_urls
                
                # 继续下一轮尝试
                last_exception = e
                continue
            except Exception as e:
                last_exception = e
                print(f"从 {source_name} 下载失败: {str(e)}")
                if (current_url, source_name) != urls_to_try[-1]:  # 不是最后一个URL
                    print("尝试下一个源...")
                    continue
        
        # 所有URL都失败了
        raise Exception(f"所有下载源都失败，最后一次错误: {str(last_exception)}")
    
    def _download_single_attempt(self, url, dest_path, fallback_urls=None, current_source_name=None):
        """
        单次下载尝试（内部方法）
        
        参数:
            url: 下载URL
            dest_path: 目标文件路径
            fallback_urls: 备用URL列表（用于速度监控切源）
            current_source_name: 当前源名称
            
        返回:
            bool: 是否成功
            
        抛出:
            Exception: 下载失败
            SpeedTooSlowException: 速度过慢需要切源
        """
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # 临时文件路径
        temp_path = dest_path + ".tmp"
        
        # 检查是否有未完成的下载（断点续传）
        downloaded = 0
        if os.path.exists(temp_path):
            downloaded = os.path.getsize(temp_path)
        
        # 在尝试续传前，检查当前 URL 是否支持 Range 请求，且文件大小一致
        def _head_check_resume(u, current_downloaded):
            try:
                head = self.session.head(u, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                if head.status_code not in (200, 206):
                    return None
                cl = head.headers.get('Content-Length')
                accept_ranges = head.headers.get('Accept-Ranges', '')
                if cl is not None:
                    try:
                        remote_size = int(cl)
                    except Exception:
                        remote_size = None
                else:
                    remote_size = None

                # 如果 remote_size is set and remote_size < current_downloaded => mismatch
                if remote_size is not None and remote_size < current_downloaded:
                    # 远端比本地短：不一致
                    try:
                        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
                            self.progress_callback.log_message(f"远端文件大小({remote_size})比本地已下载({current_downloaded})小，无法继续续传")
                    except Exception:
                        pass
                    return False

                # if server supports ranges it's more safe to resume
                if 'bytes' in accept_ranges.lower():
                    try:
                        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
                            self.progress_callback.log_message("远端支持 Range，准备开始续传")
                    except Exception:
                        pass
                    return True

                # If content-length exists and remote_size >= current_downloaded but no Accept-Ranges
                if remote_size is not None and remote_size >= current_downloaded:
                    # We can attempt to resume by issuing a ranged GET and seeing if 206 returned
                    try:
                        if self.progress_callback and hasattr(self.progress_callback, 'log_message'):
                            self.progress_callback.log_message("远端返回 Content-Length，尝试 Range 请求以校验")
                    except Exception:
                        pass
                    return True

                # Unknown capability
                return None
            except Exception:
                return None

        # 设置断点续传的请求头（如果适合续传）
        headers = {}
        if downloaded > 0:
            resume_ok = _head_check_resume(url, downloaded)
            if resume_ok is True:
                headers['Range'] = f'bytes={downloaded}-'
                print(f"尝试续传: 已有 {downloaded} 字节，准备从 {downloaded} 继续下载")
            elif resume_ok is False:
                # 远端文件变短或不一致，删除临时文件并重新开始
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                downloaded = 0
            else:
                # 未确定是否支持续传，尝试 Range: bytes={downloaded}-，如果服务器返回 206 则继续
                headers['Range'] = f'bytes={downloaded}-'
                print("未确定是否支持断点续传，尝试发送 Range 请求")
        
        # 记录要尝试的 URL（方便调试）
        print(f"开始单次尝试下载 URL: {url} -> {dest_path}")
        # 使用分离的超时：(连接超时, 读取超时)
        # 连接超时短（快速失败），读取超时长（给速度监控时间）
        response = self.session.get(url, stream=True, timeout=(10, 60), headers=headers)
        
        # 416 表示请求的范围无效（文件已完整）
        if response.status_code == 416:
            if os.path.exists(temp_path):
                os.rename(temp_path, dest_path)
            return True
        
        response.raise_for_status()
        
        # 如果我们请求了 `Range` 并得到 200，说明服务器不支持 Range，所以需要重置（删除 tmp 并重新请求完整文件）
        if downloaded > 0 and response.status_code == 200:
            # 服务端没有按 Range 返回 206（不支持或忽略），删除临时文件并重新发起单次请求
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            # 重新发起没有 Range 的请求来下载完整文件
            response.close()
            headers.pop('Range', None)
            response = self.session.get(url, stream=True, timeout=(10, 60), headers=headers)

        # 获取文件总大小
        if 'Content-Range' in response.headers:
            # 断点续传：从 Content-Range 中解析总大小
            total = int(response.headers['Content-Range'].split('/')[-1])
        else:
            # 全新下载
            total = int(response.headers.get('content-length', 0))
        
        # 写入模式：追加或新建
        mode = 'ab' if downloaded > 0 else 'wb'
        
        # 重置当前尝试的速度监控状态
        if self._current_dlc_state:
            self._current_dlc_state['last_speed_check_time'] = time.time()
            self._current_dlc_state['last_data_time'] = time.time()
        
        stall_threshold = 15  # 卡死阈值：15秒无数据传输
        
        with open(temp_path, mode) as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                # 检查是否被停止
                if self.stopped:
                    raise Exception("下载已停止")
                
                # 检查是否暂停
                while self.paused and not self.stopped:
                    time.sleep(0.1)
                
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    # 更新DLC级别的状态
                    if self._current_dlc_state:
                        self._current_dlc_state['total_downloaded'] += len(chunk)
                        self._current_dlc_state['last_data_time'] = time.time()
                    
                    # 调用进度回调（每次收到数据时更新）
                    if self.progress_callback:
                        try:
                            if total and total > 0:
                                percent = (downloaded / total) * 100
                            else:
                                percent = None
                            # 传递 total（可能为0/None）以便回调做对应处理
                            self.progress_callback(percent, downloaded, total)
                        except Exception:
                            # 记录回调内异常但不要中断下载
                            pass
                    
                    # 速度监控和智能切源（基于当前DLC的状态）
                    current_time = time.time()
                    if self._current_dlc_state and current_time - self._current_dlc_state['last_speed_check_time'] >= self._speed_check_interval:
                        should_switch, new_url, new_source = self._check_speed_and_switch(
                            downloaded, current_time, fallback_urls, current_source_name
                        )
                        
                        if should_switch and new_url:
                            # 关闭当前响应
                            response.close()
                            # 抛出特殊异常，触发切源
                            raise SpeedTooSlowException(f"速度过慢，切换到源: {new_source}", new_url, new_source)
                else:
                    # 没有收到数据，检查是否卡死
                    if self._current_dlc_state:
                        current_time = time.time()
                        if current_time - self._current_dlc_state['last_data_time'] > stall_threshold:
                            raise Exception(f"下载卡死：{stall_threshold}秒无数据传输")
        
        # 下载完成，重命名临时文件
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(temp_path, dest_path)
        
        # 验证文件完整性
        if total > 0:
            actual_size = os.path.getsize(dest_path)
            if actual_size != total:
                raise Exception(f"文件大小不匹配: 期望 {total} 字节，实际 {actual_size} 字节")
        
        return True

    def _verify_file_hash(self, path: str, expected_hash: str) -> bool:
        """
        验证指定文件的 SHA256 哈希是否与 expected_hash 匹配
        """
        try:
            import hashlib
            if not expected_hash:
                return True
            expected = expected_hash.strip().lower()
            sha256 = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            got = sha256.hexdigest().lower()
            if got == expected:
                return True
            else:
                print(f"校验失败: {path} SHA256 不匹配 (期望 {expected}, 实际 {got})")
                try:
                    if hasattr(self, 'progress_callback') and getattr(self.progress_callback, 'log_message', None):
                        self.progress_callback.log_message(f"校验失败: {path} 期望 {expected}, 实际 {got}")
                except Exception:
                    pass
                return False
        except Exception as e:
            print(f"验证哈希时发生错误: {e}")
            return False
    
    def download_dlc(self, dlc_key, url, fallback_urls=None, expected_hash: str = None, primary_source_name: str = None):
        """
        下载DLC到缓存
        
        参数:
            dlc_key: DLC键名
            url: 主下载URL
            fallback_urls: 备用URL列表 (List[Tuple[str, str]] - URL和源名称的元组)
            expected_hash: 期望的SHA256哈希值（可选）
            primary_source_name: 主下载源名称
            
        返回:
            str: 缓存文件路径
            
        抛出:
            Exception: 下载失败
        """
        # 从URL提取文件名
        filename = url.split('/')[-1]
        if not filename:
            filename = f"{dlc_key}.zip"
        cache_path = os.path.join(PathUtils.get_dlc_cache_dir(), filename)
        
        # 如果缓存已存在，验证其完整性
        if os.path.exists(cache_path):
            is_valid = self._verify_cached_file(cache_path, expected_hash)
            if is_valid:
                return cache_path
            else:
                # 缓存文件损坏，删除并重新下载
                self._log_message(f"⚠ 检测到缓存文件损坏，将重新下载: {filename}")
                try:
                    os.remove(cache_path)
                except Exception as e:
                    self._log_message(f"⚠ 删除损坏缓存文件失败: {e}")
        
        # 下载到缓存
        self.download(url, cache_path, fallback_urls, expected_hash=expected_hash, primary_source_name=primary_source_name)
        return cache_path
    
    def _verify_cached_file(self, file_path, expected_hash=None):
        """
        验证缓存文件的完整性
        
        参数:
            file_path: 文件路径
            expected_hash: 期望的SHA256哈希值（可选）
            
        返回:
            bool: 文件是否有效
        """
        try:
            # 1. 检查文件大小（至少要大于100字节 - 一个空ZIP最小约22字节）
            file_size = os.path.getsize(file_path)
            if file_size < 100:
                self._log_message(f"⚠ 缓存文件过小 ({file_size} 字节)，可能已损坏")
                return False
            
            # 2. 验证ZIP文件格式
            try:
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    # 测试ZIP文件完整性
                    bad_file = zip_ref.testzip()
                    if bad_file:
                        self._log_message(f"⚠ ZIP文件损坏，损坏的文件: {bad_file}")
                        return False
            except zipfile.BadZipFile:
                self._log_message("⚠ 缓存文件不是有效的ZIP格式")
                return False
            except Exception as e:
                self._log_message(f"⚠ ZIP验证失败: {e}")
                return False
            
            # 3. 如果提供了哈希值，进行SHA256校验
            if expected_hash:
                import hashlib
                sha256 = hashlib.sha256()
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        sha256.update(chunk)
                actual_hash = sha256.hexdigest()
                
                if actual_hash.lower() != expected_hash.lower():
                    self._log_message(f"⚠ SHA256校验失败")
                    self._log_message(f"   期望: {expected_hash}")
                    self._log_message(f"   实际: {actual_hash}")
                    return False
            
            return True
        except Exception as e:
            self._log_message(f"⚠ 验证缓存文件时出错: {e}")
            return False
    
    def is_cached(self, dlc_key):
        """
        检查DLC是否已缓存
        
        参数:
            dlc_key: DLC键名
            
        返回:
            bool: 是否已缓存
        """
        # 检查是否有任何以dlc_key开头的zip文件
        cache_dir = PathUtils.get_dlc_cache_dir()
        if not os.path.exists(cache_dir):
            return False
        
        for file in os.listdir(cache_dir):
            if file.startswith(f"{dlc_key}.") and file.endswith('.zip'):
                return True
        return False
