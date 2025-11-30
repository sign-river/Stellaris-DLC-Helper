# 自动更新功能说明

## 功能概述

实现完整的自动更新功能：检查更新、下载安装、版本回滚。

## 核心文件

- `src/core/updater.py` - 更新核心逻辑
- `src/gui/update_dialog.py` - 更新对话框UI
- `src/gui/main_window.py` - 主界面集成

## 功能特性

- ✅ 启动时自动检查更新
- ✅ 手动检查更新按钮
- ✅ 下载进度显示
- ✅ 自动备份和回滚
- ✅ 文件完整性验证

## 使用流程

1. **自动检查** - 程序启动后自动检查更新
2. **更新提示** - 发现新版本显示对话框
3. **下载安装** - 用户确认后自动下载安装
4. **完成重启** - 更新完成后提示重启

## 服务器配置

需要在服务器设置以下文件结构：

```
update/
├── version.json          # 版本信息
└── v{版本}/
    ├── 更新包.zip        # 完整更新包
    └── update.log        # 更新日志
```

## 版本信息格式

```json
{
  "latest_version": "1.1.0",
  "force_update": false,
  "update_url": "https://example.com/update/v1.1.0/app.zip",
  "update_log": "https://example.com/update/v1.1.0/changelog.txt",
  "min_version": "1.0.0",
  "release_date": "2024-11-30",
  "file_size": "25.5MB",
  "checksum": "SHA256哈希值"
}
```

## 注意事项

- 更新包为完整的应用程序压缩文件
- 配置文件会自动保留
- 更新失败时自动回滚到上一版本

---

# 多源下载系统部署说明

## 概述

多源下载系统支持三个下载源：R2、国内云服务器和GitHub，提供更好的下载可靠性和用户体验。

## 下载源配置

### 1. R2源 (优先级1)
- **类型**: `r2`
- **配置**: 无需额外配置，直接使用R2存储桶
- **URL格式**: `https://r2.example.com/dlc/{dlc_id}.zip`

### 2. 国内云服务器 (优先级2)
- **类型**: `domestic_cloud`
- **配置**: 
  ```json
  {
    "name": "domestic_cloud",
    "enabled": true,
    "priority": 2,
    "format": "domestic_cloud",
    "base_url": "http://47.100.2.190/dlc/"
  }
  ```
- **部署要求**:
  - 在服务器根目录创建 `dlc/` 文件夹
  - 上传 `index.json` 文件（包含所有DLC信息）
  - 上传所有DLC的zip文件

### 3. GitHub源 (优先级3)
- **类型**: `github_release`
- **配置**:
  ```json
  {
    "name": "github",
    "enabled": true,
    "priority": 3,
    "format": "github_release",
    "base_url": "https://github.com/sign-river/File_warehouse/releases/download/ste4.2/",
    "mapping_file": "pairings.json"
  }
  ```
- **部署要求**:
  - 创建GitHub仓库发布版本 `ste4.2`
  - 上传所有DLC文件，使用数字编号（如001.zip, 002.zip等）
  - 创建 `pairings.json` 文件映射DLC名称到文件名

## pairings.json 格式

```json
{
  "Symbols Of Domination": "001.zip",
  "Anniversary Portraits": "002.zip",
  "Horizons Signal": "003.zip"
}
```

## 部署步骤

1. **配置GitHub发布**:
   - 前往 https://github.com/sign-river/File_warehouse/releases
   - 创建新发布版本 `ste4.2`
   - 上传所有DLC文件并记录映射关系

2. **配置国内云服务器**:
   - 上传 `index.json` 到 `http://47.100.2.190/dlc/`
   - 上传所有DLC zip文件到同一目录

3. **更新配置文件**:
   - 编辑 `config.json` 中的 `sources` 数组
   - 确保所有源都设置为 `enabled: true`
   - 验证优先级设置正确

4. **测试验证**:
   - 运行 `python tools/final_test.py` 验证配置
   - 检查所有DLC都能生成正确的下载URL

## 故障排除

- **GitHub源无法访问**: 检查发布版本名称和文件映射
- **国内云服务器失败**: 验证服务器响应和文件存在
- **R2源问题**: 检查存储桶配置和权限
- **映射文件错误**: 验证 `pairings.json` 格式和文件名对应关系