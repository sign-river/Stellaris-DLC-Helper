# Stellaris DLC Helper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个用于下载、安装、管理和“解锁” Stellaris (AppID: 281990) DLC 的开源工具，提供桌面 GUI 和服务器管理 CLI 工具。

## ✨ 特性

- 🖥️ **现代化 GUI**：基于 CustomTkinter 的用户友好界面，支持批量操作 DLC
- 📦 **DLC 缓存**：自动缓存下载的文件，避免重复下载
- 🔓 **一键解锁**：通过补丁实现 DLC 解锁功能
- 🖧 **服务器管理**：CLI 工具支持 SSH 上传、删除 DLC 和生成索引
- 📝 **操作日志**：完整的日志记录和操作历史
- ⏯️ **断点续传**：支持下载中断后继续

## 🚀 安装

### 环境要求
- Python 3.8+
- Windows/Linux/macOS

### 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/sign-river/Stellaris-DLC-Helper.git
cd Stellaris-DLC-Helper
```

2. 创建虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 Windows: venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 📖 使用

### GUI 模式（推荐）
```bash
python main.py
```

首次运行时会自动从 `config.json.example` 生成配置文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT License - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系

- 项目主页：[GitHub](https://github.com/sign-river/Stellaris-DLC-Helper)
- QQ 群：1051774780

---

⭐ 如果这个项目对你有帮助，请给它一个星标！
