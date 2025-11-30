# 多源下载部署指南

## 概述

Stellaris DLC Helper 支持四个下载源，为用户提供高可靠性的下载服务。本指南说明如何在各个平台部署DLC文件。

## 当前部署状态

根据连通性测试结果：

- ❌ **R2源**: 连接超时 (可能为临时网络问题)
- ❌ **国内云服务器**: HTTP 404 (未部署)
- ❌ **GitHub**: HTTP 302 (release不存在)
- ❌ **Gitee**: HTTP 404 (release不存在)

## 部署步骤

### 1. R2源 (Cloudflare R2)
**状态**: 已配置但连接超时
**URL**: `https://dlc.dlchelper.top/dlc/`
**要求**: 确保R2存储桶可访问，index.json存在

### 2. 国内云服务器
**状态**: 配置完成，等待部署
**URL**: `http://47.100.2.190/dlc/`
**部署要求**:

#### 目录结构
```
http://47.100.2.190/dlc/
├── index.json          # DLC列表文件
├── 281990/             # AppID目录
│   ├── dlc001_symbols_of_domination.zip
│   ├── dlc002_arachnoid.zip
│   └── ... (其他DLC文件)
```

#### index.json 格式
```json
{
  "281990": {
    "dlcs": {
      "dlc001_symbols_of_domination": {
        "name": "Symbols Of Domination",
        "url": "http://47.100.2.190/dlc/281990/dlc001_symbols_of_domination.zip",
        "size": 123456789
      },
      "dlc002_arachnoid": {
        "name": "Arachnoid Portrait Pack",
        "url": "http://47.100.2.190/dlc/281990/dlc002_arachnoid.zip",
        "size": 98765432
      }
    }
  }
}
```

#### 部署命令
```bash
# 上传index.json
scp index.json user@47.100.2.190:/var/www/html/dlc/

# 上传DLC文件
scp dlc_files/*.zip user@47.100.2.190:/var/www/html/dlc/281990/
```

### 3. GitHub源
**状态**: 配置完成，等待创建release
**仓库**: `https://github.com/sign-river/File_warehouse`
**Release**: `ste4.2`
**部署要求**:

#### 创建Release
1. 访问: https://github.com/sign-river/File_warehouse/releases
2. 点击 "Create a new release"
3. Tag version: `ste4.2`
4. Release title: `Stellaris DLC Collection v4.2`
5. 上传所有DLC文件，命名为:
   - `001.zip` (对应 Symbols Of Domination)
   - `002.zip` (对应 Arachnoid Portrait Pack)
   - `003.zip` (对应 Signup Bonus)
   - ... 依此类推到 `039.zip`

#### 文件映射
根据 `pairings.json`，确保文件名正确对应。

### 4. Gitee源
**状态**: 配置完成，等待创建releases
**仓库**: `https://gitee.com/signriver/file_warehouse`
**部署要求**:

#### 创建两个Release
1. **ste1-26**: 包含1-26编号的DLC
2. **ste27-39**: 包含27-39编号的DLC

#### Release 1: ste1-26
- Tag: `ste1-26`
- Title: `Stellaris DLC 1-26`
- 上传文件: `001.zip` 到 `026.zip`

#### Release 2: ste27-39
- Tag: `ste27-39`
- Title: `Stellaris DLC 27-39`
- 上传文件: `027.zip` 到 `039.zip`

## 验证部署

部署完成后，运行连通性测试：

```bash
python tools/connectivity_test.py
```

期望结果：
- ✅ R2源: 连通正常
- ✅ 国内云服务器: 连通正常
- ✅ GitHub: 连通正常
- ✅ Gitee: 连通正常

## DLC文件清单

根据 `pairings.json`，需要准备以下文件：

| 编号 | DLC名称 | 文件名 |
|------|---------|--------|
| 001 | Symbols Of Domination | 001.zip |
| 002 | Arachnoid Portrait Pack | 002.zip |
| 003 | Signup Bonus | 003.zip |
| 004 | Plantoid Species Pack | 004.zip |
| 010 | Creatures of the Void | 010.zip |
| ... | ... | ... |
| 039 | Stargazer | 039.zip |

## 注意事项

1. **文件完整性**: 确保所有zip文件完整且可解压
2. **命名一致性**: 严格按照 `pairings.json` 的映射关系命名
3. **权限设置**: 确保文件可公开访问
4. **备份策略**: 建议在多个源同时部署，以提高可靠性
5. **监控更新**: 定期检查连通性，及时处理故障

## 故障排除

### R2源问题
- 检查Cloudflare R2存储桶配置
- 验证CORS设置
- 确认域名解析正确

### 国内云服务器问题
- 检查Nginx/Apache配置
- 验证文件权限 (644 for files, 755 for directories)
- 确认防火墙设置

### GitHub/Gitee问题
- 确认仓库存在且公开
- 检查release tag名称是否正确
- 验证文件上传成功
- 等待CDN缓存生效 (可能需要几分钟)