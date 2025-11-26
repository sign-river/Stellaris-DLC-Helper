# Stellaris DLC Helper

🌟 群星(Stellaris) DLC 一键解锁工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/downloads/)
[![GitHub release](https://img.shields.io/github/v/release/sign-river/Stellaris-DLC-Helper)](https://github.com/sign-river/Stellaris-DLC-Helper/releases)

> 专为群星(Stellaris)设计的轻量级DLC管理工具 | 云端下载 | 智能缓存 | 操作可还原

---

## ✨ 功能特性

- 🎮 **专注群星** - 针对Stellaris游戏优化，无需输入AppID
- ☁️ **云端下载** - 从远程服务器直接下载DLC文件
- 💾 **智能缓存** - 本地缓存已下载的DLC，避免重复下载
- 🔍 **自动检测** - 识别已安装的DLC，智能去重
- 📝 **操作记录** - 记录所有操作，支持精确还原
- 🎨 **纯中文界面** - 简洁易用的图形界面
- 🔄 **一键还原** - 随时恢复游戏原始状态
- 🏗️ **模块化设计** - 便于扩展和维护

---

## 📦 快速开始

### 下载使用（推荐）

1. 前往 [Releases](https://github.com/sign-river/Stellaris-DLC-Helper/releases/latest) 页面
2. 下载 `Stellaris.DLC.Helper.vX.X.X.zip`
3. 解压到任意位置
4. 运行 `stellaris_dlc_helper.exe`

### 从源码运行

```bash
# 克隆仓库
git clone https://github.com/sign-river/Stellaris-DLC-Helper.git
cd Stellaris-DLC-Helper

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

---

## 🎯 使用步骤

1. **选择游戏目录**
   - 点击"浏览"按钮
   - 选择你的Stellaris游戏根目录（包含stellaris.exe的文件夹）

2. **查看可用DLC**
   - 程序会自动加载服务器上的DLC列表
   - 已安装的DLC会标记为"已安装"

3. **下载安装DLC**
   - 勾选你想要的DLC
   - 点击"下载并安装选中的DLC"按钮
   - 等待下载和安装完成

4. **还原游戏（可选）**
   - 如果想移除已安装的DLC
   - 点击"还原游戏"按钮
   - 程序会自动删除所有通过本工具安装的DLC

---

## 🏗️ 项目结构

```
Stellaris-DLC-Helper/
├── main.py                      # 主入口文件
├── stellaris_dlc_helper.py      # 旧版单文件（保留作备份）
├── requirements.txt             # 依赖列表
├── README.md                    # 项目说明
├── GIT_GUIDE.md                 # Git使用指南
└── src/                         # 源代码目录
    ├── __init__.py
    ├── config.py                # 全局配置
    ├── core/                    # 核心功能模块
    │   ├── __init__.py
    │   ├── dlc_manager.py       # DLC管理（获取列表、检查安装）
    │   ├── downloader.py        # 下载模块
    │   └── installer.py         # 安装/卸载模块
    ├── gui/                     # 图形界面模块
    │   ├── __init__.py
    │   └── main_window.py       # 主窗口
    └── utils/                   # 工具模块
        ├── __init__.py
        ├── logger.py            # 日志管理
        ├── path_utils.py        # 路径工具
        └── operation_log.py     # 操作记录
```

---

## 💾 本地缓存

程序会在安装目录下创建缓存文件夹：

```
Stellaris_DLC_Cache/
├── dlc/                           # DLC文件缓存
│   └── 281990/                    # Stellaris的AppID
│       ├── dlc001_xxx.zip
│       └── dlc002_xxx.zip
└── operation_logs/                # 操作记录日志
    └── operations_xxxxx.json
```

**缓存优势：**
- ✅ 避免重复下载相同的DLC
- ✅ 节省时间和网络流量
- ✅ 离线重装时可直接使用缓存

**清理缓存：**
- 直接删除 `Stellaris_DLC_Cache` 文件夹即可

---

## 🔧 开发相关

### 模块说明

- **config.py** - 全局配置和常量
- **core/** - 核心业务逻辑
  - `dlc_manager.py` - DLC列表管理和状态检查
  - `downloader.py` - 文件下载和缓存管理
  - `installer.py` - DLC安装、卸载和还原
- **gui/** - 图形界面
  - `main_window.py` - 主窗口和用户交互
- **utils/** - 工具类
  - `logger.py` - 日志输出
  - `path_utils.py` - 路径处理
  - `operation_log.py` - 操作记录

### 打包发布

```bash
# 安装打包工具
pip install pyinstaller

# 打包为单个exe文件
pyinstaller --onefile --windowed --name stellaris_dlc_helper --icon=icon.ico main.py

# 打包后的文件在 dist/ 目录下
```

---

## 🛠️ 技术栈

- **Python 3.7+**
- **Tkinter** - GUI框架
- **requests** - HTTP请求

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

## 📮 联系方式

- 项目地址: [https://github.com/sign-river/Stellaris-DLC-Helper](https://github.com/sign-river/Stellaris-DLC-Helper)
- 问题反馈: [Issues](https://github.com/sign-river/Stellaris-DLC-Helper/issues)

---

**⚠️ 免责声明**

本工具仅供学习和研究使用。请支持正版游戏！
