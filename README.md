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

---

## 📦 快速开始

### 下载使用

1. 前往 [Releases](https://github.com/sign-river/Stellaris-DLC-Helper/releases/latest) 页面
2. 下载 `Stellaris.DLC.Helper.vX.X.X.zip`
3. 解压到任意位置
4. 运行 `stellaris_dlc_helper.exe`

### 使用步骤

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

## 🎯 界面预览

```
┌──────────────────────────────────────────┐
│  Stellaris DLC Helper                    │
├──────────────────────────────────────────┤
│  游戏路径: [__________________]  [浏览]   │
├──────────────────────────────────────────┤
│  可用DLC (共15个):                        │
│  ☐ Symbols of Domination (0.07 MB)      │
│  ☐ Arachnoid Portrait Pack (1.2 MB)     │
│  ☑ Overlord (已安装)                     │
│  ☐ Ancient Relics Story Pack (2.5 MB)   │
│  ...                                    │
│                                         │
│  [全选] [反选] [刷新列表]                  │
├──────────────────────────────────────────┤
│  [下载并安装选中的DLC]  [还原游戏]         │
└──────────────────────────────────────────┘
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

## 🔄 还原系统

本工具使用基于操作日志的精确还原系统：

**工作原理：**
1. 每次安装DLC时记录详细操作信息
2. 还原时按逆序执行相反操作
3. 自动删除安装的DLC目录
4. 恢复备份的原始文件（如有）

**操作日志示例：**
```json
{
  "game_path": "E:\\Games\\Stellaris",
  "operations": [
    {
      "type": "install_dlc",
      "details": {
        "dlc_key": "dlc001_symbols_of_domination",
        "dlc_name": "Stellaris: Symbols of Domination",
        "install_path": "E:\\Games\\Stellaris\\dlc\\dlc001_xxx"
      },
      "timestamp": "2025-01-27 14:30:00"
    }
  ]
}
```

---

## 🌐 DLC服务器

**服务器地址：** https://dlc.dlchelper.top/dlc/

**文件结构：**
```
/dlc/
├── index.json          # DLC索引文件
└── files/
    └── 281990/         # Stellaris的DLC目录
        ├── dlc001_symbols_of_domination.zip
        ├── dlc002_arachnoid.zip
        └── ...
```

**DLC命名规范：**
- 格式：`dlc###_descriptive_name.zip`
- 编号按顺序排列
- 使用清晰的英文描述

---

## 💻 系统要求

### Windows 可执行文件版本
- Windows 7/8/10/11 (64位)
- 互联网连接（用于下载DLC）
- 约50MB可用磁盘空间

### Python 源码版本
- Python 3.7+
- 依赖模块：
  ```
  requests>=2.28.0
  ```
- 安装依赖：
  ```bash
  pip install -r requirements.txt
  ```

---

## 🛠️ 从源码运行

1. **克隆仓库**
   ```bash
   git clone https://github.com/sign-river/Stellaris-DLC-Helper.git
   cd Stellaris-DLC-Helper
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python stellaris_dlc_helper.py
   ```

---

## 📦 打包为可执行文件

使用 PyInstaller 打包：

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包命令
pyinstaller --onefile --windowed --icon=icon.ico stellaris_dlc_helper.py
```

生成的exe文件位于 `dist/` 目录。

---

## ⚠️ 重要说明

### 关于DLC来源

本工具提供的DLC文件仅供学习和测试使用。

**推荐获取方式：**
1. **Steam官方购买** - 支持游戏开发者
2. **CS.RIN.RU论坛** - [Steam Content Sharing](https://cs.rin.ru/forum/viewforum.php?f=22)

### 关于游戏本体

本工具**不提供**游戏本体文件。你需要：
- 从Steam购买正版游戏
- 或从其他渠道获取游戏本体

### 法律声明

- ⚠️ 本工具仅供个人学习研究使用
- ⚠️ 请在下载后24小时内删除
- ⚠️ 如果你喜欢这个游戏，请购买正版支持开发者
- ⚠️ 使用本工具造成的任何后果由使用者自行承担

---

## 🔒 隐私与安全

**网络请求说明：**
- 仅连接到DLC服务器：`https://dlc.dlchelper.top`
- 不收集任何用户数据
- 不上传任何信息
- 所有操作在本地完成

**病毒误报：**
- 某些杀毒软件可能误报
- 代码完全开源，可自行审查
- 可在 [VirusTotal](https://www.virustotal.com/) 验证

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

**开发计划：**
- [ ] 添加DLC描述和截图
- [ ] 支持多语言（英文）
- [ ] 添加DLC更新检查
- [ ] 优化下载速度（多线程）

---

## 📝 更新日志

### v1.0.0 (2025-01-27)
- 🎉 首次发布
- ✨ 基础DLC下载和安装功能
- 💾 本地缓存系统
- 🔄 操作记录与还原功能
- 🎨 纯中文图形界面

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- **Paradox Interactive** - Stellaris游戏开发商
- **CS.RIN.RU社区** - 提供技术支持和资源
- **所有贡献者** - 感谢你们的支持

---

## 📮 联系方式

- **GitHub Issues**: [提交问题](https://github.com/sign-river/Stellaris-DLC-Helper/issues)
- **讨论区**: [GitHub Discussions](https://github.com/sign-river/Stellaris-DLC-Helper/discussions)

---

**⭐ 如果觉得有用，请给项目点个Star！**

