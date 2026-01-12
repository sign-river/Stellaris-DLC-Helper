# Stellaris DLC Helper

🌟 群星(Stellaris) DLC 一键解锁工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/sign-river/Stellaris-DLC-Helper)](https://github.com/sign-river/Stellaris-DLC-Helper/releases)
[![QQ群](https://img.shields.io/badge/QQ群-1051774780-blue)](https://qm.qq.com/q/xxx)

> 轻量级 DLC 管理工具 | GitLink高速下载 | 实时速度显示 | 无缝自动更新

---

## ✨ 核心功能

- 🎮 **一键解锁** - 自动检测游戏路径，一键下载安装所有DLC
- 🚀 **高速下载** - GitLink国内高速源，稳定快速
- ⚡ **实时速度** - 下载过程实时显示速度和进度
- 💾 **断点续传** - 支持暂停/恢复下载，网络中断自动续传
- 🔄 **自动更新** - 内置更新检查，支持静默升级
- 📢 **公告推送** - 及时获取重要通知和维护信息
- 📊 **速度测试** - 独立测速功能，实时显示网络速度
- 📝 **操作日志** - 完整记录所有操作，支持导出
- 🎨 **现代界面** - CustomTkinter现代化UI，清爽易用
- 🔒 **补丁管理** - CreamAPI补丁自动应用与还原

---

## 📦 快速开始

### 方式一：直接运行（推荐）

1. 前往 [Releases](https://github.com/sign-river/Stellaris-DLC-Helper/releases/latest) 下载最新版
2. 解压到任意目录
3. 运行 `Stellaris_DLC_Helper.exe`
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

### 基本流程

1. **自动检测** - 程序启动后自动检测Steam游戏路径
2. **加载DLC** - 自动从GitLink获取DLC列表和游戏版本
3. **检查更新** - 自动检查程序更新和公告信息
4. **选择DLC** - 查看可用DLC列表（默认全选）
5. **一键解锁** - 点击"一键解锁"，自动完成下载、安装、打补丁
6. **开始游戏** - 享受完整游戏体验

### 进阶功能

- **速度测试** - 设置→测速选项卡，测试GitLink下载速度
- **实时速度** - 下载时实时显示速度和进度百分比
- **暂停/恢复** - 下载过程中可随时暂停恢复
- **清理缓存** - 清理已下载的DLC文件释放空间
- **还原游戏** - 一键还原到原始状态

---

## 💻 系统要求

- **操作系统**: Windows 7/8/10/11 (64位)
- **运行环境**: 无需Python，开箱即用
- **网络**: 需要互联网连接
- **磁盘空间**: 约100MB可用空间（DLC缓存需额外空间）

> ⚠️ **重要提示**: 本工具目前仅支持 Windows 平台。

---

## 🔧 主要特性

### GitLink高速下载

采用GitLink国内源，提供稳定快速的下载体验：

- **高速稳定** - 国内CDN加速，下载速度快
- **实时显示** - 下载过程实时显示速度和进度
- **断点续传** - 支持暂停/恢复，网络中断自动续传
- **完整性验证** - SHA256哈希校验，确保文件完整

### 速度测试功能

在设置中提供独立的速度测试功能：

- **实时更新** - 测速过程中每0.3秒更新速度显示
- **准确评估** - 使用70MB测试文件，准确评估网络速度
- **速度评级** - 自动评级（优秀⭐⭐⭐⭐⭐ / 良好⭐⭐⭐⭐ / 一般⭐⭐⭐）
- **大号显示** - 醒目的数字显示，一目了然

### 版本信息显示

- **游戏版本** - 显示当前DLC资源对应的游戏版本
- **自动排序** - DLC列表按编号自动排序（001→039）
- **文件大小** - 显示每个DLC的文件大小

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

查看完整更新日志：[更新说明](docs/更新说明.md)

### 最新版本特性

**v1.1.0** (2025-12-04)
- ✨ 全新智能测速系统
  - 三级阈值策略（海外2.5/国内云3.0/Gitee0.8）
  - 10秒实际下载测试，每2秒显示实时速度
  - 5分钟智能缓存，防止循环测速
- 🎯 多源下载优化
  - 自动识别梯子用户日志](docs/更新日志.md)

### 最新版本特性

**v1.0.4** (2026-01-12)
- 🚀 **简化为单一GitLink源**
  - 移除多源配置，专注GitLink单一高速源
  - 删除废弃的启动测速功能
  - 简化配置管理，提升用户体验
- 📊 **新增独立测速功能**
  - 在设置中新增"测速"选项卡
  - 实时显示下载速度（每0.3秒更新）
  - 大号数字显示测速结果
  - 根据速度自动评级（⭐⭐⭐⭐⭐）
  - 使用70MB测试文件，准确评估网络速度
- 🎨 **UI优化**
  - 设置对话框布局优化，统一使用可滚动容器
  - 测速界面左右分栏显示（左侧描述，右侧速度）
  - 速度显示根据快慢使用不同颜色（绿→黄→红）
- 🐛 **Bug修复**
  - 修复下载进度条参数顺序错误
  - 修复Lambda闭包导致的进度显示问题
  - 修复DLC列表文件大小不显示的问题
  - 修复恢复下载时进度超过100%的问题
  - 修复GitLink API返回格式化字符串的解析
- ⚡ **性能优化**
  - 优化启动速度，减少网络超时等待
  - DLC列表按编号自动排序
  - 显示游戏版本信息docs/使用手册.md#常见问题)** - FAQ
- **[故障排除](docs/使用手册.md#故障排除)** - 问题解决

### 开发者文档
- **[开发文档](docs/开发文档.md)** - 完整开发指南
- **[打包指南](docs/打包指南.md)** - 构建发布流程
- **[部署指南](docs/部署指南.md)** - 服务器部署

### 专题文档
- **[配置管理说明](docs/配置管理说明.md)** - 配置文件管理
- **[错误处理使用指南](docs/错误处理使用指南.md)** - 错误处理机制

---

## 🛠️ 技术栈

- **语言**: Python 3.8+
- **GUI**: CustomTkinter与版本信息
- `Downloader` - 下载引擎（支持断点续传、实时速度）
- `Updater` - 自动更新系统
- `ErrorHandler` - 统一错误处理
- `SpeedTest` - 速度测试功能
### 核心模块

- `DLCManager` - DLC列表管理
- `SourceManager` - 多源智能管理
- `Downloader` - 下载引擎（支持断点续传）
- `Updater` - 自动更新系统
- `ErrorHandler` - 统一错误处理

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 提交规范

```bash
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试
chore: 构建/工具
```

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

