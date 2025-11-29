# Stellaris DLC Helper 打包指南

## 概述

本项目使用 PyInstaller 将 Python 应用打包为独立的 Windows exe 文件。打包脚本会自动创建虚拟环境、安装依赖、构建可执行文件并组织文件结构。

## 打包输出结构

打包后的目录结构如下：

```
Stellaris-DLC-Helper/
├── Stellaris-DLC-Helper.exe    # 主程序可执行文件
├── patches/                    # 补丁文件目录
│   └── cream_api.ini          # CreamAPI配置文件
├── config/                     # 配置文件目录
│   └── config.json            # 程序配置文件
├── assets/                     # 资源文件目录
│   └── images/
│       └── README.md          # 图片资源说明
├── version.json                # 版本信息文件（打包时生成）
└── README.txt                  # 使用说明（可选）
```

## 快速打包

### 自动打包（推荐）

```bash
# 在项目根目录运行
python build.py
```

打包脚本会自动执行以下步骤：
1. 创建虚拟环境 (`build_venv`)
2. 安装最小依赖 (从 `requirements-build.txt` 读取)
3. 使用 PyInstaller 构建 exe 文件
4. 组织文件结构到 `Stellaris-DLC-Helper` 目录
5. 生成版本信息文件
6. 清理临时文件

### 手动打包

如果需要自定义打包，可以手动执行：

```bash
# 1. 创建虚拟环境
python -m venv build_venv
build_venv\Scripts\activate

# 2. 安装构建依赖
pip install -r requirements-build.txt
pip install pyinstaller>=5.0.0

# 3. 构建exe文件
pyinstaller Stellaris-DLC-Helper.spec

# 4. 组织文件结构
# 复制必要文件到Stellaris-DLC-Helper目录
```

## 依赖管理

### 构建依赖 (`requirements-build.txt`)

仅包含运行所需的核心依赖：
- `requests>=2.28.0` - HTTP请求库
- `customtkinter>=5.2.0` - 现代化UI框架
- `Pillow>=9.0.0` - 图像处理库

### 开发依赖 (`requirements.txt`)

包含所有开发和测试依赖，以及构建依赖。

### 依赖优化策略

- 使用虚拟环境隔离依赖
- 只安装运行时必需的包
- 通过 PyInstaller spec 文件排除不必要的模块
- 启用压缩减小文件大小

## PyInstaller 配置

项目使用 `Stellaris-DLC-Helper.spec` 文件进行打包配置：

```python
# 主要配置项
exe_name = 'Stellaris-DLC-Helper'
main_script = 'main.py'
onefile = True  # 单文件模式
windowed = True  # 无控制台窗口
icon = 'icon.ico'  # 程序图标
```

## 故障排除

### 打包失败

**问题**: 虚拟环境创建失败
**解决**:
- 确保 Python 版本 >= 3.7
- 检查磁盘空间是否足够
- 删除旧的 `build_venv` 目录后重试

**问题**: 依赖安装失败
**解决**:
- 检查网络连接
- 确认 `requirements-build.txt` 文件存在且格式正确
- 手动安装有问题的包

**问题**: PyInstaller 构建失败
**解决**:
- 确保 `Stellaris-DLC-Helper.spec` 文件存在
- 检查主脚本 `main.py` 是否可执行
- 查看 PyInstaller 错误日志

### 运行时错误

**问题**: exe 文件无法启动
**解决**:
- 检查是否所有必需文件都在正确位置
- 验证配置文件 `config/config.json` 格式
- 查看 Windows 事件日志

**问题**: 缺少 DLL 或模块
**解决**:
- 重新打包，确保所有依赖都被包含
- 检查 PyInstaller spec 文件的 `hiddenimports` 配置

### 文件大小优化

- 使用 `--onefile` 模式打包为单个 exe 文件
- 启用 UPX 压缩（如果安装了 UPX）
- 排除不必要的依赖和模块
- 使用虚拟环境只安装必需包

## 发布准备

### 测试打包结果

1. **功能测试**
   ```bash
   # 运行打包后的exe文件
   .\Stellaris-DLC-Helper\Stellaris-DLC-Helper.exe
   ```

2. **完整性检查**
   - 验证所有文件都存在
   - 检查配置文件是否正确
   - 测试基本功能是否正常

### 创建发布包

```bash
# 1. 压缩整个目录
Compress-Archive -Path "Stellaris-DLC-Helper" -DestinationPath "Stellaris-DLC-Helper-v1.0.0.zip"

# 2. 计算文件哈希（可选）
Get-FileHash "Stellaris-DLC-Helper-v1.0.0.zip" -Algorithm SHA256
```

### GitHub Releases

1. 前往项目 Releases 页面
2. 创建新 release
3. 上传打包的 zip 文件
4. 添加发布说明和更新日志

## 最佳实践

- ✅ 使用自动打包脚本确保一致性
- ✅ 在干净的环境中进行打包
- ✅ 测试打包结果后再发布
- ✅ 保留打包日志以便调试
- ✅ 使用版本控制管理打包配置

## 清理

打包完成后，可以清理临时文件：

```bash
# 删除构建文件
rmdir /s build_venv
rmdir /s build
rmdir /s dist
rmdir /s Stellaris-DLC-Helper
```