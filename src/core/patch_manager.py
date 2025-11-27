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


class PatchManager:
    """补丁管理器类"""
    
    def __init__(self, game_path, logger=None):
        """
        初始化补丁管理器
        
        Args:
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
    
    def scan_steam_api64_locations(self):
        """
        递归扫描游戏目录，查找所有 steam_api64.dll 位置（仅 64 位）
        
        Returns:
            dict: {
                'steam_api64': [路径列表]
            }
        """
        locations = {
            'steam_api64': []
        }
        
        self.logger.info("正在扫描游戏目录...")
        
        try:
            for root, dirs, files in os.walk(self.game_path):
                if STEAM_API64_DLL in files:
                    dll_path = os.path.join(root, STEAM_API64_DLL)
                    locations['steam_api64'].append(dll_path)
                    self.logger.info(f"找到 {STEAM_API64_DLL}: {dll_path}")
            
            total = len(locations['steam_api64'])
            self.logger.info(f"扫描完成，共找到 {total} 个 DLL 文件（仅 64 位）")
            
            return locations
            
        except Exception as e:
            self.logger.error(f"扫描目录失败: {str(e)}")
            raise
    
    def backup_steam_api64_dll(self, dll_path):
        """
        备份原始 steam_api64.dll 文件
        
        Args:
            dll_path: steam_api64.dll 文件路径
            
        Returns:
            str: 备份文件路径 (steam_api64_o.dll)
        """
        # 生成备份文件名 (steam_api64.dll -> steam_api64_o.dll)
        dir_name = os.path.dirname(dll_path)
        file_name = os.path.basename(dll_path)
        backup_name = file_name.replace('.dll', '_o.dll')
        backup_path = os.path.join(dir_name, backup_name)
        
        # 如果备份已存在，说明已经打过补丁了，不再备份
        if os.path.exists(backup_path):
            self.logger.info(f"备份已存在，跳过: {backup_name}")
            return backup_path
        
        # 创建备份
        try:
            shutil.copy2(dll_path, backup_path)
            self.logger.info(f"已备份: {file_name} -> {backup_name}")
            return backup_path
        except Exception as e:
            self.logger.error(f"备份失败: {str(e)}")
            raise
    
    def restore_steam_api64_dll(self, dll_path):
        """
        还原 steam_api64.dll 文件（从 local backup 移动 back）
        
        Args:
            dll_path: steam_api64.dll 文件路径
            
        Returns:
            bool: 是否成功
        """
        dir_name = os.path.dirname(dll_path)
        file_name = os.path.basename(dll_path)
        backup_name = file_name.replace('.dll', '_o.dll')
        backup_path = os.path.join(dir_name, backup_name)
        
        # 检查备份是否存在
        if not os.path.exists(backup_path):
            self.logger.warning(f"备份不存在，跳过还原: {backup_name}")
            return False
        
        try:
            # 删除补丁DLL
            if os.path.exists(dll_path):
                os.remove(dll_path)
            
            # 还原备份
            shutil.move(backup_path, dll_path)
            self.logger.success(f"已还原: {backup_name} -> {file_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"还原失败: {str(e)}")
            return False
    
    def copy_patch_steam_api64_dll(self, dll_name, target_path):
        """
        复制补丁 steam_api64.dll 到目标位置
        
        Args:
            dll_name: 补丁 DLL 文件名（应为 steam_api64.dll）
            target_path: 目标覆盖路径
        """
        source_path = os.path.join(self.patch_dir, dll_name)
        
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"补丁文件不存在: {dll_name}")
        
        try:
            shutil.copy2(source_path, target_path)
            self.logger.info(f"已复制补丁: {dll_name}")
        except Exception as e:
            self.logger.error(f"复制补丁失败: {str(e)}")
            raise
    
    def generate_cream_config(self, dlc_list):
        """
        生成 cream_api.ini 配置文件
        
        Args:
            dlc_list: DLC列表，每项包含 key 和 name
            
        Returns:
            str: 配置文件内容
        """
        import requests
        import json
        from pathlib import Path
        from ..config import REQUEST_TIMEOUT
        
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
            appinfo_url = "http://47.100.2.190/appinfo/stellaris_appinfo.json"
            self.logger.info(f"正在从服务器获取 Steam DLC ID 映射...")
            response = requests.get(appinfo_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            appinfo = response.json()
            # 保存到本地缓存
            cache_path = Path(__file__).parent.parent.parent / 'stellaris_appinfo.json'
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
                local_path = Path(__file__).parent.parent.parent / filename
                if local_path.exists():
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
    
    def apply_patch(self, dlc_list):
        """
        应用补丁
        
        Args:
            dlc_list: DLC列表
            
        Returns:
            tuple: (成功数量, 失败数量)
        """
        self.logger.info("\n" + "="*50)
        self.logger.info("开始应用 CreamAPI 补丁...")
        
        success = 0
        failed = 0
        
        try:
            # 1. 扫描DLL位置
            locations = self.scan_steam_api64_locations()

            # 如果没有找到任何目标 DLL，尝试使用 patches 目录下的 steam_api64_o.dll
            if not locations['steam_api64']:
                fallback_o = os.path.join(self.patch_dir, STEAM_API64_O_DLL)
                if os.path.exists(fallback_o):
                    # 将其复制到游戏根目录作为 steam_api64.dll
                    target_path = os.path.join(self.game_path, STEAM_API64_DLL)
                    try:
                        shutil.copy2(fallback_o, target_path)
                        locations['steam_api64'].append(target_path)
                        self.logger.info(f"未在游戏目录发现 steam_api64.dll，已从补丁目录复制: {target_path}")
                    except Exception as e:
                        self.logger.error(f"尝试使用补丁目录中的 steam_api64_o.dll 创建目标文件失败: {e}")
                        return 0, 1
                else:
                    self.logger.error("未找到任何 steam_api64.dll 文件！且补丁目录中不存在 steam_api64_o.dll")
                    return 0, 1
            
            # 2. 备份并替换 64 位 DLL
            
            # 3. 备份并替换 steam_api64.dll
            for dll_path in locations['steam_api64']:
                try:
                    self.backup_steam_api64_dll(dll_path)
                    self.copy_patch_steam_api64_dll(STEAM_API64_DLL, dll_path)
                    success += 1
                except Exception as e:
                    self.logger.error(f"处理 steam_api64.dll 失败: {str(e)}")
                    failed += 1
            
            # 4. 生成并复制配置文件（只在游戏根目录）
            try:
                config_content = self.generate_cream_config(dlc_list)
                config_path = os.path.join(self.game_path, 'cream_api.ini')
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(config_content)
                
                self.logger.success("已生成配置文件: cream_api.ini")
                
            except Exception as e:
                self.logger.error(f"生成配置文件失败: {str(e)}")
                failed += 1
            
            self.logger.info("="*50)
            self.logger.success(f"补丁应用完成！成功: {success}, 失败: {failed}")
            
            return success, failed
            
        except Exception as e:
            self.logger.error(f"应用补丁失败: {str(e)}")
            return success, failed + 1
    
    def remove_patch(self):
        """
        还原补丁（移除补丁并恢复原始文件）
        
        Returns:
            tuple: (成功数量, 失败数量)
        """
        self.logger.info("\n" + "="*50)
        self.logger.info("开始移除补丁...")
        
        success = 0
        failed = 0
        
        try:
            # 1. 扫描DLL位置
            locations = self.scan_steam_api64_locations()
            
            # 2. 还原 steam_api64.dll
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
                            self.logger.error(f"使用补丁目录中的 steam_api64_o.dll 恢复失败: {str(e)}")
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
                    self.logger.error(f"删除配置文件失败: {str(e)}")
            
            self.logger.info("="*50)
            self.logger.success(f"移除补丁完成！成功: {success}, 失败: {failed}")
            
            return success, failed
            
        except Exception as e:
            self.logger.error(f"还原失败: {str(e)}")
            return success, failed + 1
    
    def check_patch_status(self):
        """
        检查补丁状态
        
        Returns:
            dict: {
                'patched': bool,  # 是否已打补丁
                'backup_exists': bool,  # 备份是否存在
                'config_exists': bool  # 配置文件是否存在
            }
        """
        # 检查备份文件（仅 64 位）
        backup_exists = False
        for root, dirs, files in os.walk(self.game_path):
            if STEAM_API64_O_DLL in files:
                backup_exists = True
                break
        
        # 检查配置文件
        config_path = os.path.join(self.game_path, 'cream_api.ini')
        config_exists = os.path.exists(config_path)
        
        # 如果有备份或配置文件，说明已打补丁
        patched = backup_exists or config_exists
        
        return {
            'patched': patched,
            'backup_exists': backup_exists,
            'config_exists': config_exists
        }
