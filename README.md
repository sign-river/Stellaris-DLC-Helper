# Stellaris DLC Helper

🌟 群星(Stellaris) DLC 一键解锁工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/sign-river/Stellaris-DLC-Helper)](https://github.com/sign-river/Stellaris-DLC-Helper/releases)

> 轻量级 DLC 管理工具 | 多源下载 | 智能缓存 | 自动更新

---

## ✨ 核心功能

- 🎮 **一键解锁** - 自动检测游戏路径，一键下载安装所有DLC
- ☁️ **多源下载** - R2、GitHub、国内云、Gitee四源智能切换
- 💾 **智能缓存** - 本地缓存已下载DLC，秒速安装
- 🔄 **自动更新** - 内置更新检查，支持静默升级
- 📝 **操作日志** - 完整记录所有操作，支持导出
- 🎨 **现代界面** - CustomTkinter现代化UI，清爽易用
- ⚙️ **源管理** - 可视化源配置，实时测速优选
- 🔒 **补丁管理** - CreamAPI补丁自动应用与还原

---

## 📦 快速开始

### 方式一：直接运行（推荐）

1. 前往 [Releases](https://github.com/sign-river/Stellaris-DLC-Helper/releases/latest) 下载最新版
2. 解压到任意目录
3. 运行 `Stellaris-DLC-Helper.exe`
4. 点击"一键解锁"即可

### 方式二：源码运行

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

## 💡 使用说明

1. **自动检测** - 程序启动后自动检测Steam游戏路径
2. **选择DLC** - 查看可用DLC列表（默认全选）
3. **一键解锁** - 点击"一键解锁"按钮，自动下载、安装DLC和应用补丁
4. **源管理** - 点击设置按钮可测速选择最快下载源
5. **还原游戏** - 需要时可一键还原到原始状态

---

## 💻 系统要求

- **操作系统**: Windows 7/8/10/11 (64位) - **仅支持Windows系统**
- **运行环境**: 无需Python，开箱即用
- **网络**: 需要互联网连接
- **磁盘空间**: 约100MB可用空间

> ⚠️ **重要提示**: 本工具目前仅实现了 Windows 平台的补丁功能。如需支持其他系统，欢迎在 [Issues](https://github.com/sign-river/Stellaris-DLC-Helper/issues) 中反馈或贡献代码。

---

## 🔧 主要特性

### 多源下载系统
- **R2 (Cloudflare)** - 全球CDN加速，默认源
- **GitHub Release** - 官方托管，稳定可靠
- **国内云服务器** - 国内访问优化
- **Gitee Release** - 备用源

程序自动选择最快源，支持实时测速和手动切换。

### 完整性校验
- SHA256哈希验证
- 断点续传支持
- 损坏文件自动重下载

### 操作日志
- 记录所有DLC操作
- 支持导出查看
- 精确还原支持

---

## ⚠️ 免责声明

本工具仅供学习和研究使用：

- ✅ 本工具为开源免费项目
- ✅ 如付费获得请立即退款
- ⚠️ 仅供个人学习测试使用
- ⚠️ 请在24小时内删除
- ⚠️ 喜欢游戏请购买正版支持开发者
- ⚠️ 使用本工具的后果由使用者自行承担

**推荐正版渠道：**
- Steam官方商店
- 各大正版游戏平台

---

## 🔒 隐私与安全

- ✅ 代码完全开源，可自行审查
- ✅ 不收集任何用户数据
- ✅ 所有操作在本地完成
- ✅ 仅连接到DLC下载服务器
- ✅ 无后门，无广告，无捆绑

---

## 📝 更新日志

查看完整更新日志：[CHANGELOG.md](docs/发行说明.md)

### 最新版本

**v1.0.0** (2025-12-01)
- 🎉 首次正式发布
- ✨ 现代化UI（CustomTkinter）
- 🌐 多源下载系统（4个源自动切换）
- 💾 智能缓存与断点续传
- 🔄 自动更新功能
- ⚙️ 可视化源管理与测速
- 📝 完整操作日志系统
- 🔒 完整性校验（SHA256）
- 🎨 中文路径完全支持

---

## 🛠️ 开发相关

### 项目结构

```
Stellaris-DLC-Helper/
├── src/                  # 源代码
│   ├── core/            # 核心功能
│   ├── gui/             # 界面模块
│   └── utils/           # 工具函数
├── docs/                # 文档
├── tools/               # 测试工具
├── patches/             # 补丁文件
└── assets/              # 资源文件
```

### 开发者指南

详细文档请查看：
- [开发者指南](docs/开发者指南.md) - 完整开发文档
- [打包指南](docs/打包指南.md) - 构建发布流程
- [部署指南](docs/部署指南.md) - 服务器部署说明

### 打包构建

```bash
# 安装打包依赖
pip install -r requirements-build.txt

# 执行打包
python build.py

# 快速模式（跳过压缩）
python build.py --fast
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📞 联系方式

- **问题反馈**: [GitHub Issues](https://github.com/sign-river/Stellaris-DLC-Helper/issues)
- **QQ交流群**: 1051774780
- **B站视频**: [使用教程](https://www.bilibili.com/video/BV12pbrzSEQY/)

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## ⭐ Star History

如果这个项目对你有帮助，请点个 Star 支持一下！

[![Star History Chart](https://api.star-history.com/svg?repos=sign-river/Stellaris-DLC-Helper&type=Date)](https://star-history.com/#sign-river/Stellaris-DLC-Helper&Date)

---

<div align="center">

**Made with ❤️ by [唏嘘南溪](https://github.com/sign-river)**

该程序为免费开源项目 | 如付费获得请立即退款

</div>

