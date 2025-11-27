#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器DLC管理工具
用于管理服务器端的DLC文件
"""

import os
import sys
import json
import paramiko
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tkinter import Tk, filedialog
from datetime import datetime

# 添加父目录到路径以导入config_loader
sys.path.insert(0, str(Path(__file__).parent))
from src.config_loader import get_config


class ServerConfig:
    """服务器配置管理"""
    
    @classmethod
    def get_server_info(cls) -> Tuple[str, str, str]:
        """
        获取服务器信息（IP、用户名、密码）
        从 config.json 的 server_management 配置中读取
        
        Returns:
            (ip, username, password)
        """
        # 获取配置
        ip = get_config('server_management', 'ssh_ip', default='')
        username = get_config('server_management', 'ssh_username', default='root')
        password = get_config('server_management', 'ssh_password', default='')
        
        # 如果IP为空，提示输入
        if not ip:
            print("\n请输入服务器IP地址")
            print("格式示例: 192.168.1.100 或 example.com")
            ip = input("服务器IP: ").strip()
        
        # 如果密码为空，提示输入
        if not password:
            import getpass
            password = getpass.getpass("服务器密码: ")
        
        # 保存配置
        cls.save_server_info(ip, username, password)
        
        return ip, username, password
    
    @classmethod
    def save_server_info(cls, ip: str, username: str, password: str):
        """保存服务器信息到 config.json"""
        try:
            config_file = Path(__file__).parent / 'config.json'
            
            # 如果config.json不存在，从example复制
            if not config_file.exists():
                example_file = Path(__file__).parent / 'config.json.example'
                if example_file.exists():
                    import shutil
                    shutil.copy(example_file, config_file)
            
            # 读取现有配置
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新server_management配置
            if 'server_management' not in config:
                config['server_management'] = {}
            
            config['server_management']['ssh_ip'] = ip
            config['server_management']['ssh_username'] = username
            config['server_management']['ssh_password'] = password
            
            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"配置已保存到 {config_file}")
            
        except Exception as e:
            print(f"配置保存失败: {e}")


class ServerManager:
    """服务器管理器"""
    
    def __init__(self):
        self.ssh = None
        self.sftp = None
        self.ip = None
        self.username = None
        self.password = None
        
        # 服务器路径配置
        self.server_base_path = "/var/www/dlc"
        self.server_files_path = f"{self.server_base_path}/files/281990"  # DLC存放在281990子目录
        self.server_index_path = f"{self.server_base_path}/index.json"
        self.server_appinfo_path = "/var/www/appinfo"
    
    def connect(self):
        """连接服务器"""
        try:
            self.ip, self.username, self.password = ServerConfig.get_server_info()
            
            print(f"\n正在连接服务器 {self.ip}...")
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.ip, username=self.username, password=self.password, timeout=10)
            self.sftp = self.ssh.open_sftp()
            print("✓ 连接成功！")
            return True
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print("已断开服务器连接")
    
    def upload_dlcs(self):
        """上传DLC文件"""
        if not self.sftp:
            print("✗ 未连接到服务器")
            return
        
        # 使用tkinter文件选择对话框
        print("\n正在打开文件选择对话框...")
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        files = filedialog.askopenfilenames(
            title="选择要上传的DLC文件",
            filetypes=[
                ("ZIP files", "*.zip"),
                ("All files", "*.*")
            ]
        )
        root.destroy()
        
        if not files:
            print("未选择文件")
            return
        
        print(f"\n已选择 {len(files)} 个文件")
        
        # 确保服务器目录存在
        try:
            self.sftp.stat(self.server_files_path)
        except FileNotFoundError:
            print(f"创建服务器目录: {self.server_files_path}")
            self._exec_command(f"mkdir -p {self.server_files_path}")
        
        # 上传文件
        success_count = 0
        for local_file in files:
            try:
                filename = os.path.basename(local_file)
                remote_file = f"{self.server_files_path}/{filename}"
                
                print(f"上传: {filename}...", end=' ')
                
                # 获取文件大小用于进度显示
                file_size = os.path.getsize(local_file)
                
                self.sftp.put(local_file, remote_file)
                print(f"✓ ({self._format_size(file_size)})")
                success_count += 1
                
            except Exception as e:
                print(f"✗ 失败: {e}")
        
        print(f"\n上传完成！成功: {success_count}/{len(files)}")
    
    def list_dlcs(self) -> List[Dict]:
        """
        列出服务器上的所有DLC
        
        Returns:
            DLC列表，格式: [{"name": "文件名", "size": 大小, "time": 时间}, ...]
        """
        if not self.sftp:
            print("✗ 未连接到服务器")
            return []
        
        try:
            files = self.sftp.listdir_attr(self.server_files_path)
            
            # 筛选zip文件并排序
            dlc_list = []
            for file in files:
                if file.filename.endswith('.zip'):
                    dlc_list.append({
                        "name": file.filename,
                        "size": file.st_size,
                        "time": datetime.fromtimestamp(file.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            # 按文件名排序
            dlc_list.sort(key=lambda x: x['name'])
            return dlc_list
            
        except Exception as e:
            print(f"✗ 获取DLC列表失败: {e}")
            return []
    
    def delete_dlcs(self):
        """删除服务器上的DLC"""
        dlc_list = self.list_dlcs()
        
        if not dlc_list:
            print("\n服务器上没有DLC文件")
            return
        
        # 显示DLC列表
        print("\n" + "="*80)
        print("服务器DLC列表:")
        print("="*80)
        for idx, dlc in enumerate(dlc_list, 1):
            print(f"{idx:3d}. {dlc['name']:50s} {self._format_size(dlc['size']):>10s}  {dlc['time']}")
        print("="*80)
        
        # 获取用户输入
        print("\n输入要删除的DLC序号（支持格式：5 或 5-15 或 1,3,5 或 组合 1,3,5-10）")
        print("输入 'q' 取消")
        user_input = input("请输入: ").strip()
        
        if user_input.lower() == 'q':
            return
        
        # 解析序号
        indices = self._parse_indices(user_input, len(dlc_list))
        if not indices:
            print("✗ 无效的序号")
            return
        
        # 确认删除
        print(f"\n将删除 {len(indices)} 个DLC:")
        for idx in sorted(indices):
            print(f"  - {dlc_list[idx-1]['name']}")
        
        confirm = input("\n确认删除? (y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
        
        # 执行删除
        success_count = 0
        for idx in indices:
            dlc = dlc_list[idx-1]
            try:
                remote_file = f"{self.server_files_path}/{dlc['name']}"
                self.sftp.remove(remote_file)
                print(f"✓ 已删除: {dlc['name']}")
                success_count += 1
            except Exception as e:
                print(f"✗ 删除失败 {dlc['name']}: {e}")
        
        print(f"\n删除完成！成功: {success_count}/{len(indices)}")
    
    def generate_index(self):
        """生成index.json文件"""
        print("\n正在生成 index.json...")
        
        dlc_list = self.list_dlcs()
        if not dlc_list:
            print("✗ 服务器上没有DLC文件")
            return
        
        # 构建符合程序期望的index结构
        # 格式: { "281990": { "dlcs": { "dlc001": {...}, ... } } }
        dlcs_dict = {}
        
        for dlc in dlc_list:
            # 尝试解析文件名获取DLC信息
            # 格式: dlc001_symbols_of_domination.zip
            name = dlc['name'].replace('.zip', '')
            parts = name.split('_', 1)
            
            if len(parts) == 2:
                key = parts[0]
                display_name = parts[1].replace('_', ' ').title()
            else:
                key = name
                display_name = name
            
            # 使用字典格式，key作为键名
            dlcs_dict[key] = {
                "name": display_name,
                "size": self._format_size(dlc['size']),
                "url": f"http://47.100.2.190/dlc/files/281990/{dlc['name']}"
            }
        
        # 按照程序期望的格式构建
        index_data = {
            "281990": {
                "name": "Stellaris",
                "version": "1.0.0",
                "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "dlcs": dlcs_dict
            }
        }
        
        # 保存到服务器
        try:
            # 先保存到本地临时文件
            temp_file = "temp_index.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            # 上传到服务器
            self.sftp.put(temp_file, self.server_index_path)
            os.remove(temp_file)
            
            print(f"✓ index.json 已生成并上传到服务器")
            print(f"  - 文件路径: {self.server_index_path}")
            print(f"  - DLC数量: {len(dlcs_dict)}")
            print(f"  - 格式: 已转换为程序兼容格式")
            
        except Exception as e:
            print(f"✗ 生成失败: {e}")
    
    def download_index(self):
        """下载index.json到本地"""
        if not self.sftp:
            print("✗ 未连接到服务器")
            return
        
        try:
            local_file = "server_index.json"
            self.sftp.get(self.server_index_path, local_file)
            print(f"\n✓ index.json 已下载到本地: {local_file}")
            
            # 显示内容
            with open(local_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"\n版本: {data.get('version')}")
                print(f"更新时间: {data.get('update_time')}")
                print(f"DLC总数: {data.get('total')}")
                
        except Exception as e:
            print(f"✗ 下载失败: {e}")
    
    def update_appinfo(self):
        """更新游戏AppID和DLC列表信息"""
        print("\n正在获取 Stellaris (281990) 的信息...")
        
        try:
            # 从Steam API获取主游戏信息
            url = "https://store.steampowered.com/api/appdetails/?appids=281990"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('281990', {}).get('success'):
                print("✗ 无法获取游戏信息")
                return
            
            game_data = data['281990']['data']
            
            # 提取DLC信息
            appinfo = {
                "app_id": "281990",
                "name": game_data.get('name', 'Stellaris'),
                "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "dlcs": []
            }
            
            # 获取每个DLC的详细信息
            if 'dlc' in game_data:
                print(f"找到 {len(game_data['dlc'])} 个DLC，正在获取详细信息...")
                for idx, dlc_id in enumerate(game_data['dlc'], 1):
                    try:
                        # 获取单个DLC的详细信息
                        dlc_url = f"https://store.steampowered.com/api/appdetails/?appids={dlc_id}"
                        dlc_response = requests.get(dlc_url, timeout=10)
                        dlc_data = dlc_response.json()
                        
                        dlc_name = f"DLC_{dlc_id}"  # 默认名称
                        if dlc_data.get(str(dlc_id), {}).get('success'):
                            dlc_info = dlc_data[str(dlc_id)]['data']
                            dlc_name = dlc_info.get('name', dlc_name)
                        
                        appinfo['dlcs'].append({
                            "id": str(dlc_id),
                            "name": dlc_name
                        })
                        
                        print(f"  [{idx}/{len(game_data['dlc'])}] {dlc_id}: {dlc_name}")
                        
                        # 避免请求过快
                        if idx < len(game_data['dlc']):
                            import time
                            time.sleep(0.5)
                            
                    except Exception as e:
                        print(f"  ⚠ 获取DLC {dlc_id} 信息失败: {e}")
                        appinfo['dlcs'].append({
                            "id": str(dlc_id),
                            "name": f"DLC_{dlc_id}"
                        })
            
            # DLC排序：按id从小到大
            try:
                appinfo['dlcs'].sort(key=lambda x: int(x['id']))
            except Exception as e:
                print(f"⚠ DLC排序失败: {e}")

            # 保存到本地
            local_file = "stellaris_appinfo.json"
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(appinfo, f, indent=2, ensure_ascii=False)

            print(f"✓ 游戏信息已保存到: {local_file}")
            print(f"  - 游戏名称: {appinfo['name']}")
            print(f"  - DLC数量: {len(appinfo['dlcs'])}")

            # 上传到服务器
            try:
                # 确保目录存在
                self._exec_command(f"mkdir -p {self.server_appinfo_path}")

                remote_file = f"{self.server_appinfo_path}/stellaris_appinfo.json"
                self.sftp.put(local_file, remote_file)
                print(f"✓ 已上传到服务器: {remote_file}")

            except Exception as e:
                print(f"✗ 上传到服务器失败: {e}")
            
        except Exception as e:
            print(f"✗ 获取游戏信息失败: {e}")
    
    def download_appinfo(self):
        """从服务器下载游戏AppID和DLC信息"""
        if not self.sftp:
            print("✗ 未连接到服务器")
            return
        
        try:
            remote_file = f"{self.server_appinfo_path}/stellaris_appinfo.json"
            local_file = "server_stellaris_appinfo.json"
            
            print(f"\n正在从服务器下载 AppID 信息...")
            self.sftp.get(remote_file, local_file)
            print(f"✓ 已下载到本地: {local_file}")
            
            # 显示内容
            with open(local_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"\n{'='*80}")
                print(f"游戏信息:")
                print(f"{'='*80}")
                print(f"AppID: {data.get('app_id')}")
                print(f"名称: {data.get('name')}")
                print(f"更新时间: {data.get('update_time')}")
                print(f"DLC总数: {len(data.get('dlcs', []))}")
                print(f"\n{'='*80}")
                print(f"DLC列表:")
                print(f"{'='*80}")
                
                # 显示前10个DLC作为示例
                dlcs = data.get('dlcs', [])
                for idx, dlc in enumerate(dlcs[:10], 1):
                    print(f"{idx:3d}. ID: {dlc['id']:10s} | {dlc['name']}")
                
                if len(dlcs) > 10:
                    print(f"... (还有 {len(dlcs) - 10} 个DLC，详见文件)")
                print(f"{'='*80}")
                
        except FileNotFoundError:
            print(f"✗ 服务器上没有找到 AppID 信息文件")
            print(f"  请先使用功能5更新游戏信息")
        except Exception as e:
            print(f"✗ 下载失败: {e}")
    
    def _exec_command(self, command: str) -> Tuple[str, str]:
        """
        执行SSH命令
        
        Returns:
            (stdout, stderr)
        """
        if not self.ssh:
            return "", "未连接到服务器"
        
        stdin, stdout, stderr = self.ssh.exec_command(command)
        return stdout.read().decode('utf-8'), stderr.read().decode('utf-8')
    
    def _parse_indices(self, input_str: str, max_index: int) -> List[int]:
        """
        解析用户输入的序号
        
        支持格式:
        - 单个: 5
        - 范围: 5-15
        - 多个: 1,3,5
        - 组合: 1,3,5-10,12
        
        Args:
            input_str: 用户输入
            max_index: 最大序号
            
        Returns:
            序号列表
        """
        indices = set()
        
        try:
            parts = input_str.split(',')
            for part in parts:
                part = part.strip()
                
                if '-' in part:
                    # 范围
                    start, end = map(int, part.split('-'))
                    if 1 <= start <= max_index and 1 <= end <= max_index and start <= end:
                        indices.update(range(start, end + 1))
                else:
                    # 单个
                    idx = int(part)
                    if 1 <= idx <= max_index:
                        indices.add(idx)
            
            return sorted(list(indices))
            
        except Exception:
            return []
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


def show_menu():
    """显示主菜单"""
    print("\n" + "="*60)
    print(" " * 15 + "Stellaris DLC 服务器管理工具")
    print("="*60)
    print("1. 上传DLC文件")
    print("2. 删除服务器DLC")
    print("3. 生成 index.json")
    print("4. 下载 index.json")
    print("5. 更新游戏AppID和DLC信息")
    print("6. 下载服务器AppID和DLC信息")
    print("7. 查看服务器DLC列表")
    print("0. 退出")
    print("="*60)


def main():
    """主程序"""
    print("\n欢迎使用 Stellaris DLC 服务器管理工具！")
    
    manager = ServerManager()
    
    # 连接服务器
    if not manager.connect():
        print("\n无法连接到服务器，程序退出")
        return
    
    try:
        while True:
            show_menu()
            choice = input("\n请选择操作 (0-7): ").strip()
            
            if choice == '1':
                manager.upload_dlcs()
            elif choice == '2':
                manager.delete_dlcs()
            elif choice == '3':
                manager.generate_index()
            elif choice == '4':
                manager.download_index()
            elif choice == '5':
                manager.update_appinfo()
            elif choice == '6':
                manager.download_appinfo()
            elif choice == '7':
                dlc_list = manager.list_dlcs()
                if dlc_list:
                    print("\n" + "="*80)
                    print("服务器DLC列表:")
                    print("="*80)
                    for idx, dlc in enumerate(dlc_list, 1):
                        print(f"{idx:3d}. {dlc['name']:50s} {manager._format_size(dlc['size']):>10s}  {dlc['time']}")
                    print("="*80)
                    print(f"共 {len(dlc_list)} 个DLC")
                else:
                    print("\n服务器上没有DLC文件")
            elif choice == '0':
                print("\n感谢使用，再见！")
                break
            else:
                print("\n✗ 无效的选项，请重新选择")
    
    finally:
        manager.disconnect()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
