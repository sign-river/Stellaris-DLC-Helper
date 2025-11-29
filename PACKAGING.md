# Stellaris DLC Helper 打包指南

## 概述

本项目使用 PyInstaller 将 Python 应用打包为独立的 Windows exe 文件。

## 文件结构

打包后的目录结构如下：

```
Stellaris-DLC-Helper/
├── Stellaris-DLC-Helper.exe    # 主程序
├── patches/                    # 补丁文件
│   └── cream_api.ini
├── config/                     # 配置文件
│   └── config.json
├── assets/                     # 资源文件
│   └── images/
│       └── README.md
├── libraries/                  # 额外库（可选）
└── README.txt                  # 使用说明
```

## 打包步骤

### 1. 准备环境

确保您的系统已安装 Python 3.7+。

### 2. 运行打包脚本

```bash
# 在项目根目录运行
python build.py
```

打包脚本会自动：
- 创建虚拟环境
- 安装最小依赖
- 使用 PyInstaller 打包
- 组织文件结构
- 清理临时文件

### 3. 手动打包（可选）

如果需要自定义打包，可以手动执行：

```bash
# 1. 创建虚拟环境
python -m venv build_venv
build_venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements-build.txt
pip install pyinstaller

# 3. 打包
pyinstaller Stellaris-DLC-Helper.spec

# 4. 组织文件
# 手动复制文件到正确位置
```

## 依赖优化

### 最小依赖包

`requirements-build.txt` 只包含运行所需的核心依赖：
- requests: HTTP请求
- customtkinter: 现代化UI
- Pillow: 图像处理

### 排除不必要的库

通过 PyInstaller spec 文件排除：
- 测试模块
- 调试工具
- 不需要的标准库组件

## 故障排除

### 打包失败

1. 检查 Python 版本（需要 3.7+）
2. 确保所有依赖都正确安装
3. 检查文件路径是否正确

### 运行时错误

1. 确保所有资源文件都在正确位置
2. 检查配置文件格式
3. 查看程序日志

### 文件大小优化

- 使用 `--onefile` 单文件模式
- 启用 UPX 压缩
- 排除不必要的依赖
- 使用虚拟环境只安装必要包

## 发布准备

打包完成后：
1. 测试 exe 文件是否正常运行
2. 压缩整个 `Stellaris-DLC-Helper` 文件夹
3. 创建发布说明
4. 上传到 GitHub Releases