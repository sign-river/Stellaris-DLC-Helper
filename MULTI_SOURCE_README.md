# 多源下载配置指南

## 概述

从 v1.0.0 开始，Stellaris DLC Helper 支持多源下载，以改善国内用户的下载体验。目前支持以下下载源：

- **R2 (Cloudflare)**: 默认源，海外CDN
- **国内云服务器**: 阿里云/腾讯云等国内服务器
- **Gitee**: 码云平台
- **GitHub**: GitHub Releases

## 配置方法

### 1. 修改 config.json

在 `config.json` 的 `server.sources` 数组中配置各个下载源：

```json
{
  "server": {
    "sources": [
      {
        "name": "r2",
        "url": "https://dlc.dlchelper.top/dlc/",
        "priority": 1,
        "enabled": true,
        "format": "standard"
      },
      {
        "name": "domestic_cloud",
        "url": "http://47.100.2.190/dlc/",
        "priority": 2,
        "enabled": true,
        "format": "standard"
      },
      {
        "name": "gitee",
        "url": "https://gitee.com/api/v5/repos/your-org/your-repo/releases/assets/",
        "priority": 3,
        "enabled": true,
        "format": "gitee_release"
      },
      {
        "name": "github",
        "url": "https://api.github.com/repos/your-org/your-repo/releases/assets/",
        "priority": 4,
        "enabled": true,
        "format": "github_release"
      }
    ]
  }
}
```

### 2. 配置参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | string | 源的唯一标识符 |
| `url` | string | 源的基础URL |
| `priority` | number | 优先级（数字越小优先级越高） |
| `enabled` | boolean | 是否启用该源 |
| `format` | string | 数据格式类型 |

### 3. 支持的格式类型

#### standard (标准格式)
- 适用于R2和普通云服务器
- 数据结构：`{app_id: {dlcs: {dlc_key: {name, url, size}}}}`

#### gitee_release
- 适用于Gitee仓库的Releases
- 需要配置Gitee API URL
- TODO: 实现Gitee API数据解析

### GitHub Releases

```json
{
  "name": "github",
  "url": "https://github.com/sign-river/File_warehouse/releases/download/ste4.2/",
  "priority": 3,
  "enabled": true,
  "format": "github_release",
  "repo": "sign-river/File_warehouse",
  "tag": "ste4.2",
  "mapping_file": "pairings.json"
}
```

**映射文件格式** (`pairings.json`):
```json
{
  "dlc001_symbols_of_domination.zip": "001.zip",
  "dlc002_arachnoid.zip": "002.zip",
  ...
}
```

**下载URL示例**:
- 原始文件名: `dlc001_symbols_of_domination.zip`
- 映射后文件名: `001.zip`
- 下载URL: `https://github.com/sign-river/File_warehouse/releases/download/ste4.2/001.zip`

#### custom
- 自定义格式
- TODO: 根据具体需求实现

## 具体配置示例

### 国内云服务器

```json
{
  "name": "domestic_cloud",
  "url": "http://47.100.2.190/dlc/",
  "priority": 2,
  "enabled": true,
  "format": "standard"
}
```

**服务器结构**：
- 根目录：`http://47.100.2.190/`
- DLC目录：`http://47.100.2.190/dlc/`
- AppInfo目录：`http://47.100.2.190/appinfo/`
- Update目录：`http://47.100.2.190/update/`

**访问示例**：
- DLC列表：`http://47.100.2.190/dlc/index.json`
- AppInfo：`http://47.100.2.190/appinfo/stellaris_appinfo.json`
- 版本检查：`http://47.100.2.190/update/version.json`

## 工作原理

1. **源管理**: `SourceManager` 类管理所有配置的下载源
2. **数据合并**: 从多个源获取DLC列表并智能合并
3. **Fallback下载**: 如果主URL下载失败，自动尝试备用URL
4. **优先级排序**: 按配置的优先级决定源的使用顺序

## 测试

运行测试脚本验证配置：

```bash
python tools/test_multi_source.py
```

## 注意事项

- 确保至少启用一个源
- 不同源的文件格式可能不同，需要相应实现解析逻辑
- 网络超时和重试机制仍然适用
- 缓存机制对所有源共享

## 待完善功能

- [ ] Gitee Release API 集成
- [ ] GitHub Release API 集成
- [ ] 自定义格式支持
- [ ] 源健康检查和自动切换
- [ ] 下载速度测试和最优源选择