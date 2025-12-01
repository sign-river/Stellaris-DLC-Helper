# Stellaris DLC Helper

🌟 群星(Stellaris) DLC 一键解锁工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
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
2. 下载 `Stellaris.DLC.Helper.v1.0.0.zip`
3. 解压到任意位置
4. 运行 `Stellaris-DLC-Helper.exe`

### 使用步骤

1. **选择游戏目录** - 点击"浏览"按钮，选择Stellaris游戏根目录
2. **查看可用DLC** - 程序自动加载服务器上的DLC列表
3. **下载安装DLC** - 勾选所需DLC，点击"下载并安装选中的DLC"
4. **还原游戏** - 如需移除DLC，点击"还原游戏"按钮

---

## 💻 系统要求

- **操作系统**: Windows 7/8/10/11 (64位)
- **网络**: 需要互联网连接下载DLC
- **磁盘空间**: 约50MB可用空间
- **Python版本** (源码运行): Python 3.7+

---

## ⚠️ 重要说明

### 关于DLC来源

本工具提供的DLC文件仅供学习和测试使用。

**推荐获取方式：**
1. **Steam官方购买** - 支持游戏开发者
2. **CS.RIN.RU论坛** - [Steam Content Sharing](https://cs.rin.ru/forum/viewforum.php?f=22)

### 法律声明

- ⚠️ 本工具仅供个人学习研究使用
- ⚠️ 请在下载后24小时内删除
- ⚠️ 如果你喜欢这个游戏，请购买正版支持开发者
- ⚠️ 使用本工具造成的任何后果由使用者自行承担

---

## 🧭 关于中文路径

从 v1.0.0 开始，我们已在包含中文字符的安装路径下进行了测试，程序在这些路径下通常能正常运行（包括缓存、日志记录、DLC解压/安装等核心功能）。

不过，仍有一些潜在兼容性因素需要注意：
- 某些旧版 Windows 或第三方工具/脚本可能不完全支持 Unicode 路径
- 部分杀毒软件或系统策略可能在带中文路径时拦截写/读操作
- ZIP 文件内部路径编码（例如由旧工具打包的 ZIP）仍可能导致文件名乱码

如果你遇到路径相关的异常：
1. 请尝试将程序或游戏目录移动到不包含非 ASCII 字符的位置再试
2. 如为杀软误报，请尝试临时关闭或加入白名单
3. 欢迎在 GitHub 提交 issue，或使用 `tools/test_unicode_paths.py` 在本地复现并提供错误信息

---

## 🔒 隐私与安全

- 仅连接到DLC服务器：`https://dlc.dlchelper.top`
- 不收集任何用户数据
- 所有操作在本地完成
- 代码完全开源，可自行审查

---

## 📝 更新日志

### v1.0.0 (2025-11-30)
- 🎉 首次发布
- ✨ 基础DLC下载和安装功能
- 💾 本地缓存系统
- 🔄 操作记录与还原功能
- 🎨 纯中文图形界面
- 🌐 多源下载支持（R2、GitHub、国内云服务器、Gitee）
- 🔧 提高中文路径兼容性
- 🧪 新增测试脚本用于验证功能

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

## 📮 联系方式

- **GitHub Issues**: [提交问题](https://github.com/sign-river/Stellaris-DLC-Helper/issues)
- **项目地址**: https://github.com/sign-river/Stellaris-DLC-Helper

---

**⭐ 如果觉得有用，请给项目点个Star！**

---

## 🛠 开发者文档

开发者维护、部署和打包指南已整合为 `docs/开发者指南.md`（中文）。
- 包含：打包说明、部署步骤、源码结构、测试工具、调试与清理操作等。
- 如需贡献或了解实现细节，请先阅读 `docs/开发者指南.md`。

