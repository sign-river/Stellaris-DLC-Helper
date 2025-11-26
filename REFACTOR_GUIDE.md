# 项目重构说明

## 📁 新的项目结构

```
Stellaris-DLC-Helper/
├── main.py                         # 🚀 新的主入口文件
├── stellaris_dlc_helper.py         # 📦 旧版单文件（保留作备份）
├── requirements.txt                # 📋 依赖列表
├── README.md                       # 📖 项目说明（待更新）
├── README_NEW.md                   # 📖 新版项目说明
├── GIT_GUIDE.md                    # 📚 Git使用指南
├── .gitignore                      # 🚫 Git忽略配置
└── src/                            # 📂 源代码目录（新增）
    ├── __init__.py
    ├── config.py                   # ⚙️ 全局配置和常量
    ├── core/                       # 💎 核心功能模块
    │   ├── __init__.py
    │   ├── dlc_manager.py          # 📋 DLC列表管理和状态检查
    │   ├── downloader.py           # ⬇️ 文件下载和缓存管理
    │   └── installer.py            # 📦 DLC安装/卸载/还原
    ├── gui/                        # 🎨 图形界面模块
    │   ├── __init__.py
    │   └── main_window.py          # 🪟 主窗口和用户交互
    └── utils/                      # 🛠️ 工具模块
        ├── __init__.py
        ├── logger.py               # 📝 日志管理
        ├── path_utils.py           # 📍 路径工具
        └── operation_log.py        # 📊 操作记录管理
```

## 🔄 模块化改进

### 1. **配置模块** (`src/config.py`)
- 集中管理所有配置项和常量
- 版本号、服务器地址、字体配置等
- 便于统一修改和维护

### 2. **核心功能模块** (`src/core/`)

#### `dlc_manager.py` - DLC管理
- `fetch_dlc_list()` - 从服务器获取DLC列表
- `get_installed_dlcs()` - 检查已安装的DLC
- `is_dlc_installed()` - 检查单个DLC安装状态

#### `downloader.py` - 下载器
- `download()` - 通用文件下载
- `download_dlc()` - 下载DLC到缓存
- `is_cached()` - 检查缓存状态
- 支持进度回调

#### `installer.py` - 安装器
- `install()` - 安装DLC
- `uninstall()` - 卸载单个DLC
- `restore_game()` - 还原游戏（批量卸载）
- 自动记录操作日志

### 3. **GUI模块** (`src/gui/`)

#### `main_window.py` - 主窗口
- 所有UI组件的创建和管理
- 用户交互逻辑
- 调用核心模块完成功能

### 4. **工具模块** (`src/utils/`)

#### `logger.py` - 日志管理
- `info()` / `warning()` / `error()` / `success()` - 不同级别的日志
- 统一的日志格式和时间戳

#### `path_utils.py` - 路径工具
- `get_cache_dir()` - 获取缓存目录
- `get_dlc_cache_path()` - 获取DLC缓存路径
- `validate_stellaris_path()` - 验证游戏路径
- 跨平台路径处理

#### `operation_log.py` - 操作记录
- `load()` / `save()` - 加载/保存日志
- `add_operation()` - 添加操作记录
- `clear()` - 清空日志
- JSON格式存储

## 🎯 模块化的优势

### ✅ 代码组织
- **职责清晰**：每个模块负责特定功能
- **易于查找**：功能分类明确，快速定位代码
- **降低耦合**：模块间依赖关系清晰

### ✅ 可维护性
- **独立修改**：修改某个功能不影响其他模块
- **单元测试**：可以为每个模块编写测试
- **代码复用**：核心功能可以被其他界面调用

### ✅ 可扩展性
- **添加功能**：轻松添加新模块（如自动更新、补丁管理）
- **多界面支持**：可以基于核心模块开发CLI版本
- **插件系统**：为未来的插件架构打下基础

## 🚀 后续扩展方向

### 1. 自动更新模块 (`src/core/updater.py`)
```python
class Updater:
    def check_update()      # 检查新版本
    def download_update()   # 下载更新
    def apply_update()      # 应用更新
```

### 2. 补丁管理模块 (`src/core/patch_manager.py`)
```python
class PatchManager:
    def fetch_patches()     # 获取补丁列表
    def apply_patch()       # 应用补丁
    def rollback_patch()    # 回滚补丁
```

### 3. 备份模块 (`src/core/backup.py`)
```python
class BackupManager:
    def create_backup()     # 创建备份
    def restore_backup()    # 恢复备份
    def list_backups()      # 列出备份
```

### 4. 设置模块 (`src/core/settings.py`)
```python
class Settings:
    def load_settings()     # 加载设置
    def save_settings()     # 保存设置
    def reset_settings()    # 重置设置
```

## 📝 使用说明

### 运行程序
```bash
# 新版（推荐）
python main.py

# 旧版（备份）
python stellaris_dlc_helper.py
```

### 开发调试
```bash
# 测试单个模块
python -m src.core.dlc_manager
python -m src.core.downloader

# 运行单元测试（待添加）
python -m pytest tests/
```

### 打包发布
```bash
# 使用新的入口文件打包
pyinstaller --onefile --windowed --name stellaris_dlc_helper main.py
```

## 🔧 配置说明

所有配置项都在 `src/config.py` 中：

- `VERSION` - 版本号
- `STELLARIS_APP_ID` - Stellaris的Steam AppID
- `DLC_SERVER_URL` - DLC服务器地址
- `FONT1-4` - 界面字体配置
- `REQUEST_TIMEOUT` - 网络请求超时
- `CHUNK_SIZE` - 下载块大小

## 📦 兼容性

- ✅ **向后兼容**：保留了旧的单文件版本
- ✅ **缓存兼容**：使用相同的缓存目录结构
- ✅ **日志兼容**：操作日志格式保持不变
- ✅ **功能一致**：所有原有功能完整保留

## 🎉 重构完成

项目已成功重构为模块化结构，为后续功能扩展做好准备！
