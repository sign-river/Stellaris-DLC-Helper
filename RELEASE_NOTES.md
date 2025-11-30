# Stellaris DLC Helper v1.0.0

## 🎉 关于这个软件

**Stellaris DLC Helper** 是一款专为《群星》（Stellaris）游戏设计的DLC管理工具，帮助玩家轻松下载和安装游戏DLC。

### ✨ 主要功能
- 🎮 **自动识别游戏** - 无需手动配置，程序自动找到你的Stellaris游戏
- ☁️ **云端下载** - 从服务器直接下载DLC文件
- 💾 **智能缓存** - 本地缓存已下载的DLC，避免重复下载
- 🔄 **一键还原** - 可以随时恢复游戏到原始状态
- 🎨 **中文界面** - 简洁易用的中文用户界面

---

## 📥 下载安装

### 下载地址
前往 [GitHub Releases](https://github.com/sign-river/Stellaris-DLC-Helper/releases/tag/v1.0.0) 下载最新版本。

### 安装步骤
1. 下载 `Stellaris-DLC-Helper-v1.0.0.zip`
2. 解压到任意位置（已在包含中文字符的路径下测试通过，但某些老旧环境、第三方工具或杀毒软件可能会引起兼容性问题；若出现异常，请尝试将路径更换为不包含非ASCII字符）
3. 运行 `Stellaris-DLC-Helper.exe`

---

## 💻 系统要求

- **操作系统**: Windows 7/8/10/11 (64位)
- **内存**: 至少512MB可用内存
- **存储空间**: 约50MB可用磁盘空间
- **网络**: 需要互联网连接下载DLC

---

## 🚀 使用方法

1. **选择游戏目录** - 首次运行时选择你的Stellaris游戏安装目录
2. **查看可用DLC** - 程序会自动加载可用的DLC列表
3. **选择并下载** - 勾选你想要的DLC，点击"下载并安装"
4. **等待完成** - 程序会自动下载并安装选中的DLC
5. **开始游戏** - 启动Stellaris享受新的DLC内容

### 还原功能
如果你想移除已安装的DLC，只需点击"还原游戏"按钮，程序会自动清理所有通过此工具安装的内容。

---

## ⚠️ 重要提醒

### DLC来源声明
本工具提供的DLC文件仅供学习和测试使用。

**推荐获取方式：**
1. **Steam官方购买** - 支持游戏开发者
2. **CS.RIN.RU社区** - [Steam Content Sharing](https://cs.rin.ru/forum/viewforum.php?f=22)

### 法律声明
- 本工具仅供个人学习研究使用
- 请在下载后24小时内删除文件
- 使用本工具造成的任何后果由使用者自行承担
- **如果你喜欢这个游戏，请购买正版支持开发者**

---

## 🐛 已知问题

- 某些杀毒软件可能误报（这是正常现象，代码完全开源）
- 网络不稳定时可能需要多次重试
- 部分DLC可能因服务器问题暂时不可用

---

## 📞 获取帮助

- **项目主页**: https://github.com/sign-river/Stellaris-DLC-Helper
- **问题反馈**: [GitHub Issues](https://github.com/sign-river/Stellaris-DLC-Helper/issues)

---

**⭐ 喜欢这个工具的话，记得给项目点个Star！**

---

## 兼容性更新 (v1.0.0)
- 🔧 修复: 对游戏路径计算 MD5 时显式使用 UTF-8 编码以提高 Unicode 兼容性
- 🧪 新增测试脚本 `tools/test_unicode_paths.py`，用于在开发环境下检查中文路径兼容性
- 🌐 新增多源下载系统，支持 R2、国内云服务器、GitHub 和 Gitee 四个下载源，提高下载成功率
- 📁 新增文件名映射系统，通过 `pairings.json` 文件实现 GitHub 发布资产的灵活映射