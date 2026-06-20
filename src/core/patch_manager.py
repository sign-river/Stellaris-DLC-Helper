#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补丁管理模块
负责应用和还原 CreamAPI 补丁
"""

import os
import shutil
from ..utils import PathUtils, Logger

# 常量定义（仅 64 位）
STEAM_API64_DLL = 'steam_api64.dll'
STEAM_API64_O_DLL = 'steam_api64_o.dll'

# 补丁校验阈值
PATCHED_DLL_MIN_SIZE = 1024 * 1024       # 补丁 DLL 应 > 1MB
BACKUP_DLL_MAX_SIZE = 400 * 1024         # 原版备份应 < 400KB
PATCH_SOURCE_MIN_SIZE = 1024 * 1024      # patches/ 下补丁源文件应 > 1MB
MAX_PATCH_ATTEMPTS = 3                   # 打补丁最大重试次数

# Stellaris 游戏内的大型资源目录，不可能包含 steam_api64.dll
_SKIP_SCAN_DIRS = frozenset({
    'dlc', 'mod', 'mods', 'sound', 'music', 'gfx', 'interface', 'map',
    'common', 'events', 'localisation', 'localization', 'graphics',
    'fonts', 'flags', 'portraits', 'thumbnail', 'pdx_browser', 'tools',
    'tutorial', 'prescripted_countries', 'setup', 'journals', 'specimens',
})


class PatchManager:
    """补丁管理器类"""
    
    def __init__(self, game_path, logger=None):
        """
        初始化补丁管理器
        
        参数:
            game_path: 游戏路径
            logger: 日志记录器
        """
        self.game_path = game_path
        self.logger = logger or Logger()
        self.patch_dir = self._get_patch_dir()
        
    @staticmethod
    def _get_patch_dir():
        """获取补丁文件目录"""
        base_dir = PathUtils.get_base_dir()
        return os.path.join(base_dir, "patches")

    @staticmethod
    def _backup_path(dll_path):
        """获取与 steam_api64.dll 对应的备份路径"""
        dir_name = os.path.dirname(dll_path)
        file_name = os.path.basename(dll_path)
        backup_name = file_name.replace('.dll', '_o.dll')
        return os.path.join(dir_name, backup_name)

    @staticmethod
    def _safe_file_size(path):
        """安全获取文件大小，不存在时返回 0"""
        try:
            return os.path.getsize(path) if os.path.exists(path) else 0
        except OSError:
            return 0

    def _format_size(self, size_bytes):
        """格式化文件大小用于日志"""
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        return f"{size_bytes / 1024:.1f} KB"

    def _is_valid_patched_dll(self, dll_path):
        """补丁 DLL 是否有效（已替换为 CreamAPI 版本）"""
        return self._safe_file_size(dll_path) > PATCHED_DLL_MIN_SIZE

    def _is_valid_backup(self, backup_path):
        """原版备份是否有效"""
        size = self._safe_file_size(backup_path)
        return size > 0 and size < BACKUP_DLL_MAX_SIZE

    def _verify_patch_source(self):
        """校验 patches/ 目录下的补丁源文件"""
        source_path = os.path.join(self.patch_dir, STEAM_API64_DLL)
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"补丁文件不存在: {STEAM_API64_DLL}")
        size = self._safe_file_size(source_path)
        if size <= PATCH_SOURCE_MIN_SIZE:
            raise ValueError(
                f"补丁源文件大小异常 ({self._format_size(size)})，"
                f"应大于 {self._format_size(PATCH_SOURCE_MIN_SIZE)}"
            )

    def _verify_patch_at_location(self, dll_path):
        """
        校验单个位置的补丁是否打成功

        返回:
            tuple: (是否通过, 失败原因)
        """
        backup_path = self._backup_path(dll_path)
        reasons = []

        dll_size = self._safe_file_size(dll_path)
        if not self._is_valid_patched_dll(dll_path):
            reasons.append(
                f"steam_api64.dll 大小异常 ({self._format_size(dll_size)}，需 > 1MB)"
            )

        backup_size = self._safe_file_size(backup_path)
        if not self._is_valid_backup(backup_path):
            if backup_size == 0:
                reasons.append("steam_api64_o.dll 备份不存在")
            else:
                reasons.append(
                    f"steam_api64_o.dll 大小异常 ({self._format_size(backup_size)}，需 < 400KB)"
                )

        if reasons:
            return False, "; ".join(reasons)
        return True, ""

    def _verify_config(self):
        """校验 cream_api.ini 是否存在且有效"""
        config_path = os.path.join(self.game_path, 'cream_api.ini')
        if not os.path.exists(config_path):
            return False, "cream_api.ini 不存在"
        if self._safe_file_size(config_path) == 0:
            return False, "cream_api.ini 为空"
        return True, ""

    def _ensure_valid_backup(self, dll_path):
        """确保备份文件存在且大小合法"""
        backup_path = self._backup_path(dll_path)

        if self._is_valid_backup(backup_path):
            return backup_path

        if os.path.exists(backup_path):
            self.logger.warning(
                f"备份文件大小异常 ({self._format_size(self._safe_file_size(backup_path))})，将重建"
            )
            os.remove(backup_path)

        dll_size = self._safe_file_size(dll_path)
        if dll_size > 0 and dll_size < PATCHED_DLL_MIN_SIZE:
            shutil.copy2(dll_path, backup_path)
            self.logger.info(f"已从原版 DLL 创建备份: {backup_path}")
        else:
            fallback = os.path.join(self.patch_dir, STEAM_API64_O_DLL)
            if not os.path.exists(fallback):
                raise FileNotFoundError("无法创建备份：原版 DLL 不可用且 patches/steam_api64_o.dll 缺失")
            shutil.copy2(fallback, backup_path)
            self.logger.info(f"已从补丁目录创建备份: {backup_path}")

        if not self._is_valid_backup(backup_path):
            raise ValueError(f"备份创建后仍不符合要求: {backup_path}")

        return backup_path

    def _apply_patch_to_location(self, dll_path):
        """对单个位置执行备份 + 覆盖补丁"""
        self._ensure_valid_backup(dll_path)
        self.copy_patch_steam_api64_dll(STEAM_API64_DLL, dll_path)

    def _repair_patch_at_location(self, dll_path, reason):
        """根据校验失败原因修复并重试"""
        self.logger.info(f"尝试修复: {dll_path} ({reason})")
        backup_path = self._backup_path(dll_path)

        if "steam_api64_o.dll" in reason:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            self._ensure_valid_backup(dll_path)

        if "steam_api64.dll" in reason:
            self.copy_patch_steam_api64_dll(STEAM_API64_DLL, dll_path)

        ok, new_reason = self._verify_patch_at_location(dll_path)
        if not ok:
            raise RuntimeError(f"修复后校验仍失败: {new_reason}")

    def _write_cream_config(self, dlc_list):
        """生成并写入 cream_api.ini"""
        config_content = self.generate_cream_config(dlc_list)
        config_path = os.path.join(self.game_path, 'cream_api.ini')
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        self.logger.success("已生成配置文件: cream_api.ini")
        return config_path

    def _prepare_patch_targets(self):
        """
        扫描并准备需要打补丁的目标路径

        返回:
            list: steam_api64.dll 路径列表
        """
        locations = self.scan_steam_api64_locations()

        if not locations['steam_api64']:
            fallback_o = os.path.join(self.patch_dir, STEAM_API64_O_DLL)
            if os.path.exists(fallback_o):
                target_path = os.path.join(self.game_path, STEAM_API64_DLL)
                shutil.copy2(fallback_o, target_path)
                locations['steam_api64'].append(target_path)
                self.logger.info(
                    f"未在游戏目录发现 steam_api64.dll，已从补丁目录复制: {target_path}"
                )
            else:
                raise FileNotFoundError(
                    "未找到任何 steam_api64.dll 文件，且补丁目录中不存在 steam_api64_o.dll"
                )

        return locations['steam_api64']
    
    def _find_steam_api64_dll_paths(self):
        """
        快速定位 steam_api64.dll，避免 os.walk 扫描整个游戏目录导致 UI 卡死。
        Stellaris 的 steam_api64.dll 通常位于游戏根目录。
        """
        paths = []
        root_dll = os.path.join(self.game_path, STEAM_API64_DLL)
        if os.path.isfile(root_dll):
            paths.append(root_dll)

        try:
            for name in os.listdir(self.game_path):
                subdir = os.path.join(self.game_path, name)
                if not os.path.isdir(subdir):
                    continue
                if name.lower() in _SKIP_SCAN_DIRS:
                    continue
                candidate = os.path.join(subdir, STEAM_API64_DLL)
                if os.path.isfile(candidate):
                    paths.append(candidate)
        except OSError:
            pass

        return paths

    def scan_steam_api64_locations(self):
        """
        递归扫描游戏目录，查找所有 steam_api64.dll 位置（仅 64 位）
        
        返回:
            dict: {
                'steam_api64': [路径列表]
            }
        """
        # locations 存储在游戏根目录下发现的 steam_api64.dll 的路径列表。
        # 它是一个以 'steam_api64' 为键、值为绝对路径列表的映射。
        locations = {
            'steam_api64': []
        }
        
        self.logger.info("正在扫描游戏目录...")
        
        try:
            for dll_path in self._find_steam_api64_dll_paths():
                locations['steam_api64'].append(dll_path)
                self.logger.info(f"找到 {STEAM_API64_DLL}: {dll_path}")
            
            total = len(locations['steam_api64'])
            self.logger.info(f"扫描完成，共找到 {total} 个 DLL 文件（仅 64 位）")
            
            return locations
            
        except Exception as e:
            self.logger.log_exception(f"扫描目录失败", e)
            raise
    
    def backup_steam_api64_dll(self, dll_path):
        """
        备份原始 steam_api64.dll 文件
        
        参数:
            dll_path: steam_api64.dll 文件路径
            
        返回:
            str: 备份文件路径 (steam_api64_o.dll)
        """
        # 生成备份文件名 (steam_api64.dll -> steam_api64_o.dll)
        # 采用 '_o' 后缀保持与原始文件在同一目录：
        #  - 优点：可直接移动还原，不需要额外的全局索引
        #  - 风险：若有同名文件存在，需确保不会覆盖重要文件
        dir_name = os.path.dirname(dll_path)
        file_name = os.path.basename(dll_path)
        backup_name = file_name.replace('.dll', '_o.dll')
        backup_path = os.path.join(dir_name, backup_name)
        
        if self._is_valid_backup(backup_path):
            self.logger.info(f"备份已存在且有效，跳过: {backup_name}")
            return backup_path

        if os.path.exists(backup_path):
            self.logger.warning(f"备份文件大小异常，将重建: {backup_name}")
            os.remove(backup_path)
        
        # 创建备份
        try:
            dll_size = self._safe_file_size(dll_path)
            if dll_size > 0 and dll_size < PATCHED_DLL_MIN_SIZE:
                shutil.copy2(dll_path, backup_path)
            else:
                fallback = os.path.join(self.patch_dir, STEAM_API64_O_DLL)
                if not os.path.exists(fallback):
                    raise FileNotFoundError("无法创建备份：原版 DLL 不可用")
                shutil.copy2(fallback, backup_path)
            self.logger.info(f"已备份: {file_name} -> {backup_name}")
            return backup_path
        except Exception as e:
            self.logger.log_exception(f"备份失败", e)
            raise
    
    def restore_steam_api64_dll(self, dll_path):
        """
        还原 steam_api64.dll 文件（从 local backup 移动 back）
        
        参数:
            dll_path: steam_api64.dll 文件路径
            
        返回:
            bool: 是否成功
        """
        dir_name = os.path.dirname(dll_path)
        file_name = os.path.basename(dll_path)
        backup_name = file_name.replace('.dll', '_o.dll')
        backup_path = os.path.join(dir_name, backup_name)
        
        # 检查备份是否存在（如果没有备份，说明没有在该路径上打过补丁/备份）
        if not os.path.exists(backup_path):
            self.logger.warning(f"备份不存在，跳过还原: {backup_name}")
            return False
        
        try:
            # 删除补丁 DLL：删除当前文件以便后续用备份替换回原始文件
            if os.path.exists(dll_path):
                os.remove(dll_path)
            
            # 还原备份
            shutil.move(backup_path, dll_path)
            self.logger.success(f"已还原: {backup_name} -> {file_name}")
            return True
            
        except Exception as e:
            self.logger.log_exception(f"还原失败", e)
            return False
    
    def copy_patch_steam_api64_dll(self, dll_name, target_path):
        """
        复制补丁 steam_api64.dll 到目标位置
        
        参数:
            dll_name: 补丁 DLL 文件名（应为 steam_api64.dll）
            target_path: 目标覆盖路径
        """
        source_path = os.path.join(self.patch_dir, dll_name)
        # source_path 应指向有效补丁文件（位于 patches/ 下）。
        # 上层调用者应当保证 patches 已经包含所需的 DLL 文件。
        
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"补丁文件不存在: {dll_name}")
        
        try:
            shutil.copy2(source_path, target_path)
            self.logger.info(f"已复制补丁: {dll_name}")
        except Exception as e:
            self.logger.log_exception(f"复制补丁失败", e)
            raise
    
    def generate_cream_config(self, dlc_list):
        """
        生成 cream_api.ini 配置文件
        
        参数:
            dlc_list: DLC列表，每项包含 key 和 name
            
        返回:
            str: 配置文件内容
        """
        import requests
        import json
        from pathlib import Path
        from ..config import REQUEST_TIMEOUT, APPINFO_URL
        
        # 读取模板
        template_path = os.path.join(self.patch_dir, 'cream_api.ini')
        
        if not os.path.exists(template_path):
            raise FileNotFoundError("配置模板不存在: cream_api.ini")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # 尝试从本地缓存或服务器获取 Steam DLC ID 映射
        dlc_lines = []
        
        # 1. 优先尝试从服务器HTTP获取 appinfo 文件
        appinfo = None
        try:
            appinfo_url = APPINFO_URL
            self.logger.info(f"正在从服务器获取 Steam DLC ID 映射...")
            response = requests.get(appinfo_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            appinfo = response.json()
            # 保存到本地缓存
            cache_path = PathUtils.get_appinfo_path('stellaris_appinfo.json')
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(appinfo, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"从服务器获取失败: {e}")
            # 2. 如果HTTP失败，尝试读取本地缓存的 appinfo 文件
            local_appinfo_files = [
                'server_stellaris_appinfo.json',
                'stellaris_appinfo.json'
            ]
            for filename in local_appinfo_files:
                local_path = PathUtils.get_appinfo_path(filename)
                # 如果旧版文件位于项目根目录，则迁移到缓存目录
                legacy_path = Path(PathUtils.get_base_dir()) / filename
                try:
                    if legacy_path.exists() and not os.path.exists(local_path):
                        # 进行一次迁移复制，保留旧文件
                        shutil.copy2(str(legacy_path), str(local_path))
                        self.logger.info(f"已从旧位置迁移AppInfo: {filename} -> {local_path}")
                except Exception:
                    pass
                if os.path.exists(local_path):
                    try:
                        with open(local_path, 'r', encoding='utf-8') as f:
                            appinfo = json.load(f)
                            self.logger.info(f"使用本地缓存的 AppInfo: {filename}")
                            break
                    except Exception as e2:
                        self.logger.warning(f"读取本地 {filename} 失败: {e2}")
        
        # 3. 生成 DLC 配置
        try:
            if appinfo and 'dlcs' in appinfo:
                for dlc in appinfo['dlcs']:
                    dlc_id = dlc.get('id', '')
                    dlc_name = dlc.get('name', '')
                    if dlc_id and dlc_name:
                        dlc_lines.append(f"{dlc_id} = {dlc_name}")
                
                self.logger.success(f"已加载 {len(dlc_lines)} 个DLC的Steam ID映射")
            else:
                raise Exception("未找到有效的 AppInfo 数据")
                
        except Exception as e:
            # 如果所有方式都失败，使用注释模式
            self.logger.warning(f"无法获取Steam DLC ID映射: {e}")
            self.logger.warning("将使用注释模式生成配置文件")
            self.logger.warning("请使用服务器管理工具的功能6下载 AppInfo 到本地")
            
            for dlc in dlc_list:
                dlc_lines.append(f"; {dlc['name']}")
        
        dlc_text = '\n'.join(dlc_lines)
        
        # 替换占位符
        config = template.replace('SAC_DLC', dlc_text)
        
        return config
    
    def update_cream_config(self, dlc_list):
        """
        更新 cream_api.ini（不修改 steam_api64.dll / steam_api64_o.dll）

        返回:
            bool: 是否写入成功
        """
        try:
            self._write_cream_config(dlc_list)
            return True
        except Exception as e:
            self.logger.log_exception("更新 cream_api.ini 失败", e)
            return False

    def apply_patch(self, dlc_list):
        """
        应用补丁（含校验与重试）
        
        参数:
            dlc_list: DLC列表
            
        返回:
            tuple: (成功数量, 失败数量)
        """
        self.logger.info("\n" + "="*50)
        self.logger.info("开始应用 CreamAPI 补丁...")
        
        success = 0
        failed = 0
        
        try:
            self._verify_patch_source()
            dll_paths = self._prepare_patch_targets()

            for attempt in range(1, MAX_PATCH_ATTEMPTS + 1):
                self.logger.info(f"补丁应用第 {attempt}/{MAX_PATCH_ATTEMPTS} 次尝试...")

                # 无论 DLL 备份/补丁是否已就绪，每次尝试都刷新 cream_api.ini
                self.update_cream_config(dlc_list)

                for dll_path in dll_paths:
                    ok, reason = self._verify_patch_at_location(dll_path)
                    if ok:
                        continue
                    try:
                        if attempt == 1:
                            self._apply_patch_to_location(dll_path)
                        else:
                            self._repair_patch_at_location(dll_path, reason)
                    except Exception as e:
                        self.logger.log_exception(f"处理 {dll_path} 失败", e)

                location_results = []
                for dll_path in dll_paths:
                    ok, reason = self._verify_patch_at_location(dll_path)
                    location_results.append((dll_path, ok, reason))
                    if not ok:
                        self.logger.warning(f"校验未通过 [{dll_path}]: {reason}")

                config_valid, config_reason = self._verify_config()
                if not config_valid:
                    self.logger.warning(f"配置校验未通过: {config_reason}")

                all_locations_ok = all(ok for _, ok, _ in location_results)
                if all_locations_ok and config_valid:
                    success = len(dll_paths)
                    failed = 0
                    self.logger.success(f"补丁校验通过（第 {attempt} 次尝试）")
                    break

                if attempt < MAX_PATCH_ATTEMPTS:
                    self.logger.info("校验未完全通过，准备重试...")
                else:
                    failed = sum(1 for _, ok, _ in location_results if not ok)
                    if not config_valid:
                        failed += 1
                    success = 0
                    self.logger.log_exception(
                        f"补丁应用失败：已达最大重试次数 ({MAX_PATCH_ATTEMPTS})",
                        Exception("patch_verification_failed")
                    )
            
            self.logger.info("="*50)
            if failed == 0 and success > 0:
                self.logger.success(f"补丁应用完成！成功: {success}, 失败: {failed}")
            else:
                self.logger.warning(f"补丁应用结束。成功: {success}, 失败: {failed}")
            
            return success, failed
            
        except Exception as e:
            self.logger.log_exception(f"应用补丁失败", e)
            return success, max(failed, 1)

    def purge_patch_files(self):
        """
        删除补丁相关文件（不还原原版，供一键修复使用）

        返回:
            tuple: (成功数量, 失败数量)
        """
        self.logger.info("正在删除补丁相关文件...")
        success = 0
        failed = 0

        config_path = os.path.join(self.game_path, 'cream_api.ini')
        if os.path.exists(config_path):
            try:
                os.remove(config_path)
                success += 1
                self.logger.success("已删除: cream_api.ini")
            except Exception as e:
                failed += 1
                self.logger.log_exception("删除 cream_api.ini 失败", e)

        checked_dirs = set()
        candidate_paths = list(self._find_steam_api64_dll_paths())
        for dll_path in candidate_paths:
            checked_dirs.add(os.path.dirname(dll_path))

        checked_dirs.add(self.game_path)

        for dir_path in checked_dirs:
            for file_name in (STEAM_API64_DLL, STEAM_API64_O_DLL):
                file_path = os.path.join(dir_path, file_name)
                if not os.path.exists(file_path):
                    continue
                try:
                    os.remove(file_path)
                    success += 1
                    self.logger.success(f"已删除: {file_path}")
                except Exception as e:
                    failed += 1
                    self.logger.log_exception(f"删除 {file_name} 失败", e)

        return success, failed
    
    def remove_patch(self):
        """
        还原补丁（移除补丁并恢复原始文件）
        
        返回:
            tuple: (成功数量, 失败数量)
        """
        self.logger.info("\n" + "="*50)
        self.logger.info("开始移除补丁...")
        
        success = 0
        failed = 0
        
        try:
            # 1. 扫描DLL位置
            locations = self.scan_steam_api64_locations()
            
            # 2. 还原 steam_api64.dll：优先使用本地备份还原（更接近实际原始文件），
            #    若本地备份缺失，则使用 patches/ 下的 steam_api64_o.dll 作为最后手段还原。
            for dll_path in locations['steam_api64']:
                dir_name = os.path.dirname(dll_path)
                file_name = os.path.basename(dll_path)
                backup_name = file_name.replace('.dll', '_o.dll')
                backup_path = os.path.join(dir_name, backup_name)

                # 优先还原本地备份
                if os.path.exists(backup_path):
                    if self.restore_steam_api64_dll(dll_path):
                        success += 1
                    else:
                        failed += 1
                else:
                    # 如果本地备份不存在，尝试使用补丁目录下的 steam_api64_o.dll 恢复
                    fallback_o = os.path.join(self.patch_dir, 'steam_api64_o.dll')
                    if os.path.exists(fallback_o):
                        try:
                            # 删除当下的补丁文件（如果存在）
                            if os.path.exists(dll_path):
                                os.remove(dll_path)
                            shutil.copy2(fallback_o, dll_path)
                            self.logger.success(f"使用补丁目录中的 steam_api64_o.dll 恢复: {dll_path}")
                            success += 1
                        except Exception as e:
                            self.logger.log_exception(f"使用补丁目录中的 steam_api64_o.dll 恢复失败", e)
                            failed += 1
                    else:
                        self.logger.warning(f"未找到备份文件 {backup_name}，且补丁目录中没有 steam_api64_o.dll，跳过: {dll_path}")
                        failed += 1
            
            # 4. 删除配置文件
            config_path = os.path.join(self.game_path, 'cream_api.ini')
            if os.path.exists(config_path):
                try:
                    os.remove(config_path)
                    self.logger.success("已删除配置文件: cream_api.ini")
                except Exception as e:
                    self.logger.log_exception(f"删除配置文件失败", e)
            
            self.logger.info("="*50)
            self.logger.success(f"移除补丁完成！成功: {success}, 失败: {failed}")
            
            return success, failed
            
        except Exception as e:
            self.logger.log_exception(f"还原失败", e)
            return success, failed + 1
    
    def check_patch_status(self):
        """
        检查补丁状态（严格校验）
        
        判定标准：
        - steam_api64.dll 大小 > 1MB
        - 同目录 steam_api64_o.dll 大小 < 400KB
        - cream_api.ini 存在且非空
        
        返回:
            dict: {
                'patched': bool,
                'backup_exists': bool,
                'config_exists': bool,
                'valid_locations': int,
                'total_locations': int
            }
        """
        valid_locations = 0
        total_locations = 0
        backup_exists = False

        for dll_path in self._find_steam_api64_dll_paths():
            backup_path = self._backup_path(dll_path)
            total_locations += 1

            dll_ok = self._is_valid_patched_dll(dll_path)
            backup_ok = self._is_valid_backup(backup_path)

            if backup_ok:
                backup_exists = True

            if dll_ok and backup_ok:
                valid_locations += 1

        config_valid, _ = self._verify_config()
        config_path = os.path.join(self.game_path, 'cream_api.ini')
        config_exists = os.path.exists(config_path)

        patched = valid_locations > 0 and config_valid

        return {
            'patched': patched,
            'backup_exists': backup_exists,
            'config_exists': config_exists,
            'valid_locations': valid_locations,
            'total_locations': total_locations,
        }
