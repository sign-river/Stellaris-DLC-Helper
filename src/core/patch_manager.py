#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补丁管理模块
负责应用和还原 CreamAPI 补丁
"""

import os
import shutil
from ..utils import PathUtils, Logger


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
    
    def scan_steam_api_locations(self):
        """
        递归扫描游戏目录，查找所有 steam_api.dll 位置
        
        Returns:
            dict: {
                'steam_api': [路径列表],
                'steam_api64': [路径列表]
            }
        """
        locations = {
            'steam_api': [],
            'steam_api64': []
        }
        
        self.logger.info("正在扫描游戏目录...")
        
        try:
            for root, dirs, files in os.walk(self.game_path):
                if 'steam_api.dll' in files:
                    dll_path = os.path.join(root, 'steam_api.dll')
                    locations['steam_api'].append(dll_path)
                    self.logger.info(f"找到 steam_api.dll: {dll_path}")
                
                if 'steam_api64.dll' in files:
                    dll_path = os.path.join(root, 'steam_api64.dll')
                    locations['steam_api64'].append(dll_path)
                    self.logger.info(f"找到 steam_api64.dll: {dll_path}")
            
            total = len(locations['steam_api']) + len(locations['steam_api64'])
            self.logger.info(f"扫描完成，共找到 {total} 个DLL文件")
            
            return locations
            
        except Exception as e:
            self.logger.error(f"扫描目录失败: {str(e)}")
            raise
    
    def backup_dll(self, dll_path):
        """
        备份原始DLL文件
        
        Args:
            dll_path: DLL文件路径
            
        Returns:
            str: 备份文件路径
        """
        # 生成备份文件名 (steam_api.dll -> steam_api_o.dll)
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
    
    def restore_dll(self, dll_path):
        """
        还原DLL文件
        
        Args:
            dll_path: DLL文件路径
            
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
    
    def copy_patch_dll(self, dll_name, target_path):
        """
        复制补丁DLL到目标位置
        
        Args:
            dll_name: DLL文件名 (steam_api.dll 或 steam_api64.dll)
            target_path: 目标路径
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
        # 读取模板
        template_path = os.path.join(self.patch_dir, 'cream_api.ini')
        
        if not os.path.exists(template_path):
            raise FileNotFoundError("配置模板不存在: cream_api.ini")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # 生成DLC列表文本
        dlc_lines = []
        for dlc in dlc_list:
            # 从 dlc key 中提取数字ID（如果有的话）
            # 例如: dlc001_plantoids -> 使用 name
            # 实际的 Steam DLC ID 需要另外维护，这里先用名称
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
            locations = self.scan_steam_api_locations()
            
            if not locations['steam_api'] and not locations['steam_api64']:
                self.logger.error("未找到任何 steam_api.dll 文件！")
                return 0, 1
            
            # 2. 备份并替换 steam_api.dll
            for dll_path in locations['steam_api']:
                try:
                    self.backup_dll(dll_path)
                    self.copy_patch_dll('steam_api.dll', dll_path)
                    success += 1
                except Exception as e:
                    self.logger.error(f"处理 steam_api.dll 失败: {str(e)}")
                    failed += 1
            
            # 3. 备份并替换 steam_api64.dll
            for dll_path in locations['steam_api64']:
                try:
                    self.backup_dll(dll_path)
                    self.copy_patch_dll('steam_api64.dll', dll_path)
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
        self.logger.info("开始还原游戏...")
        
        success = 0
        failed = 0
        
        try:
            # 1. 扫描DLL位置
            locations = self.scan_steam_api_locations()
            
            # 2. 还原 steam_api.dll
            for dll_path in locations['steam_api']:
                if self.restore_dll(dll_path):
                    success += 1
                else:
                    failed += 1
            
            # 3. 还原 steam_api64.dll
            for dll_path in locations['steam_api64']:
                if self.restore_dll(dll_path):
                    success += 1
                else:
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
            self.logger.success(f"还原完成！成功: {success}, 失败: {failed}")
            
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
        # 检查备份文件
        backup_exists = False
        for root, dirs, files in os.walk(self.game_path):
            if 'steam_api_o.dll' in files or 'steam_api64_o.dll' in files:
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
