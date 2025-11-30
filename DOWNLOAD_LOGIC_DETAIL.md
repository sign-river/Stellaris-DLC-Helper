# 多源下载系统详细逻辑说明

## 概述

Stellaris DLC Helper 实现了智能的多源下载系统，支持4个下载源的自动切换和故障转移。系统按优先级尝试下载源，确保用户在不同网络环境下都能成功下载。

## 系统架构

### 核心组件

1. **SourceManager**: 管理下载源配置、URL生成和优先级排序
2. **DLCManager**: 负责DLC列表获取和合并
3. **DLCDownloader**: 执行实际的文件下载，支持断点续传

### 下载流程

```
1. 获取DLC列表 → 2. 生成多源URL → 3. 按优先级下载 → 4. 自动故障转移
```

## 各下载源详细逻辑

### 1. R2源 (Cloudflare R2) - 优先级1

**配置信息**:
```json
{
  "name": "r2",
  "format": "standard",
  "url": "https://dlc.dlchelper.top/dlc/",
  "priority": 1
}
```

**工作逻辑**:

#### 数据获取
- **入口**: `https://dlc.dlchelper.top/dlc/index.json`
- **格式**: 标准JSON格式，包含完整的DLC列表
- **内容**: `{ "281990": { "dlcs": { "dlc001_xxx": {...}, ... } } }`

#### URL生成
```python
# 原始URL: https://dlc.dlchelper.top/dlc/281990/dlc001_symbols_of_domination.zip
# 生成逻辑: 直接替换域名部分
original_url = "https://dlc.dlchelper.top/dlc/281990/dlc001_symbols_of_domination.zip"
relative_path = "281990/dlc001_symbols_of_domination.zip"  # 移除基础URL部分
final_url = f"https://dlc.dlchelper.top/dlc/{relative_path}"
```

**特点**:
- ✅ 主力下载源，全球CDN加速
- ✅ 包含完整的DLC元数据（名称、大小等）
- ✅ 作为其他源的基准URL

### 2. 国内云服务器 - 优先级2

**配置信息**:
```json
{
  "name": "domestic_cloud",
  "format": "standard",
  "url": "http://47.100.2.190/dlc/",
  "priority": 2
}
```

**工作逻辑**:

#### 数据获取
- **入口**: `http://47.100.2.190/dlc/index.json`
- **格式**: 与R2相同的标准JSON格式
- **作用**: 提供国内用户优化的访问

#### URL生成
```python
# 使用与R2相同的逻辑，但替换为国内服务器域名
original_url = "https://dlc.dlchelper.top/dlc/281990/dlc001_symbols_of_domination.zip"
# 替换为: http://47.100.2.190/dlc/281990/dlc001_symbols_of_domination.zip
```

**特点**:
- ✅ 国内网络优化，减少国际链路延迟
- ✅ 相同的数据格式，便于统一处理
- ✅ 自动故障转移到R2

### 3. GitHub源 - 优先级3

**配置信息**:
```json
{
  "name": "github",
  "format": "github_release",
  "url": "https://github.com/sign-river/File_warehouse/releases/download/ste4.2/",
  "mapping_file": "pairings.json",
  "priority": 3
}
```

**工作逻辑**:

#### 数据获取
- **特殊性**: GitHub源不获取index.json，直接标记为成功
- **原因**: DLC列表从R2获取，GitHub只作为下载源
- **映射表**: 使用 `pairings.json` 进行文件名映射

#### URL生成流程
```python
# 1. 从DLC信息中提取原始文件名
original_url = "https://dlc.dlchelper.top/dlc/281990/dlc001_symbols_of_domination.zip"
filename = "dlc001_symbols_of_domination.zip"

# 2. 通过映射表查找对应的GitHub文件名
mappings = {
  "dlc001_symbols_of_domination.zip": "001.zip",
  "dlc002_arachnoid.zip": "002.zip",
  ...
}
github_filename = mappings[filename]  # "001.zip"

# 3. 拼接最终URL
base_url = "https://github.com/sign-river/File_warehouse/releases/download/ste4.2/"
final_url = f"{base_url}{github_filename}"
# 结果: https://github.com/sign-river/File_warehouse/releases/download/ste4.2/001.zip
```

**特点**:
- ✅ 开源分发，无需服务器成本
- ✅ 稳定的GitHub CDN
- ✅ 通过文件名映射支持灵活的发布策略

### 4. Gitee源 - 优先级4

**配置信息**:
```json
{
  "name": "gitee",
  "format": "gitee_release",
  "url": "https://gitee.com/signriver/file_warehouse/releases/download/",
  "mapping_file": "pairings.json",
  "releases": {
    "ste1-26": {"min": 1, "max": 26},
    "ste27-39": {"min": 27, "max": 39}
  },
  "priority": 4
}
```

**工作逻辑**:

#### 数据获取
- **特殊性**: 与GitHub相同，不获取index.json
- **原因**: DLC列表统一从R2获取

#### URL生成流程
```python
# 1. 提取原始文件名并查找映射
filename = "dlc001_symbols_of_domination.zip"
gitee_filename = mappings[filename]  # "001.zip"

# 2. 根据文件名编号选择正确的release tag
file_num = int("001.zip".split('.')[0])  # 提取数字: 1

# 3. 匹配release范围
releases = {
  "ste1-26": {"min": 1, "max": 26},    # 1 <= 1 <= 26 ✓
  "ste27-39": {"min": 27, "max": 39}  # 不匹配
}
selected_tag = "ste1-26"

# 4. 拼接最终URL
base_url = "https://gitee.com/signriver/file_warehouse/releases/download/"
final_url = f"{base_url}/{selected_tag}/{gitee_filename}"
# 结果: https://gitee.com/signriver/file_warehouse/releases/download/ste1-26/001.zip
```

**特点**:
- ✅ 国内用户优化，访问速度快
- ✅ 分release发布，避免单release文件过多
- ✅ 智能编号匹配，无需手动配置

## 下载执行逻辑

### 多源故障转移

```python
def download(url, dest_path, fallback_urls=None):
    urls_to_try = [url]  # 主URL
    if fallback_urls:
        urls_to_try.extend(fallback_urls)  # 添加备用URL

    for current_url in urls_to_try:
        try:
            print(f"尝试从 {current_url} 下载...")
            return _download_single_attempt(current_url, dest_path)
        except Exception as e:
            print(f"从 {current_url} 下载失败: {e}")
            if current_url != urls_to_try[-1]:  # 不是最后一个
                print("尝试下一个源...")
                continue

    raise Exception("所有下载源都失败")
```

### 断点续传机制

```python
def _download_single_attempt(url, dest_path):
    # 检查临时文件
    temp_path = dest_path + ".tmp"
    downloaded = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0

    # 设置断点续传头
    headers = {}
    if downloaded > 0:
        headers['Range'] = f'bytes={downloaded}-'

    response = session.get(url, stream=True, headers=headers)

    # 处理响应
    if response.status_code == 416:  # 范围无效，文件已完整
        os.rename(temp_path, dest_path)
        return True

    response.raise_for_status()

    # 继续下载...
```

## 优先级和排序

### 源优先级排序
```python
sources.sort(key=lambda x: x.get("priority", 999))
# 数字越小优先级越高: R2(1) > 国内云(2) > GitHub(3) > Gitee(4)
```

### DLC排序
```python
dlc_list.sort(key=lambda x: _extract_dlc_number(x))
# 按DLC编号排序: dlc001, dlc002, dlc003...
```

## 缓存策略

### 本地缓存
- **位置**: `Stellaris_DLC_Cache/dlc/`
- **命名**: `{dlc_key}.zip`
- **检查**: 下载前先检查缓存是否存在

### 智能缓存
```python
def is_cached(dlc_key):
    cache_dir = PathUtils.get_dlc_cache_dir()
    for file in os.listdir(cache_dir):
        if file.startswith(f"{dlc_key}.") and file.endswith('.zip'):
            return True
    return False
```

## 错误处理

### 网络错误重试
- **超时**: 30秒超时设置
- **重试**: 自动切换到下一个源
- **日志**: 详细记录失败原因

### 文件完整性
- **大小验证**: 下载完成后检查文件大小
- **哈希验证**: 计划中功能
- **自动清理**: 失败下载的临时文件清理

## 性能优化

### 连接复用
```python
self.session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=0
)
```

### 分块下载
- **块大小**: 8KB
- **进度回调**: 实时更新下载进度
- **暂停/恢复**: 支持下载控制

## 监控和统计

### 下载统计
- 各源使用频率
- 下载成功率
- 平均下载速度

### 错误追踪
- 失败原因分类
- 网络问题诊断
- 源可用性监控

这个多源下载系统确保了极高的可靠性和用户体验，通过智能的故障转移和缓存策略，为用户提供稳定的DLC下载服务。</content>
<parameter name="filePath">e:\Stellaris-DLC-Helper\DOWNLOAD_LOGIC_DETAIL.md