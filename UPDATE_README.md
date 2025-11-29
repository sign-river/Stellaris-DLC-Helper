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

- 更新失败时自动回滚到上一版本