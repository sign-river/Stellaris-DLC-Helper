# 多源下载系统技术文档

## 概述

多源下载系统为 Stellaris DLC Helper 提供高可靠性的下载服务，通过多个下载源的自动切换确保用户在不同网络环境下都能成功下载DLC。

## 架构设计

### 核心组件

- **SourceManager**: 下载源管理器，负责源配置、URL生成和故障转移
- **DownloadManager**: 下载管理器，处理实际的文件下载和进度跟踪
- **ConfigLoader**: 配置加载器，读取和验证下载源配置

### 源类型支持

#### 1. R2 存储桶源
- **标识符**: `r2`
- **特点**: 直接URL映射，无需额外配置
- **URL格式**: `{base_url}/{dlc_id}.zip`
- **适用场景**: 主要下载源，全球CDN加速

#### 2. 国内云服务器源
- **标识符**: `domestic_cloud`
- **特点**: 支持index.json索引文件
- **URL格式**: `{base_url}{dlc_id}.zip`
- **适用场景**: 国内用户优化，网络加速

#### 4. Gitee发布源
- **标识符**: `gitee_release`
- **特点**: 分多个release发布，支持编号范围映射
- **URL格式**: `{base_url}{release_tag}/{mapped_filename}`
- **适用场景**: 备用下载源，支持分批发布

## 配置结构

### config.json 源配置

```json
{
  "sources": [
    {
      "name": "r2",
      "enabled": true,
      "priority": 1,
      "format": "r2",
      "base_url": "https://r2.example.com/dlc/"
    },
    {
      "name": "domestic_cloud",
      "enabled": true,
      "priority": 2,
      "format": "domestic_cloud",
      "base_url": "http://47.100.2.190/dlc/"
    },
    {
      "name": "github",
      "enabled": true,
      "priority": 3,
      "format": "github_release",
      "base_url": "https://github.com/sign-river/File_warehouse/releases/download/ste4.2/",
      "mapping_file": "pairings.json"
    },
    {
      "name": "gitee",
      "enabled": true,
      "priority": 4,
      "format": "gitee_release",
      "base_url": "https://gitee.com/signriver/file_warehouse/releases/download/",
      "mapping_file": "pairings.json",
      "releases": {
        "ste1-26": {"min": 1, "max": 26},
        "ste27-39": {"min": 27, "max": 39}
      }
    }
  ]
}
```

### pairings.json 映射文件

```json
{
  "Symbols Of Domination": "001.zip",
  "Anniversary Portraits": "002.zip",
  "Horizons Signal": "003.zip",
  "Stellaris: Galaxy Edition": "004.zip"
}
```

## 工作流程

### 1. 初始化阶段
1. 加载 `config.json` 配置
2. 验证所有启用源的配置完整性
3. 加载 `pairings.json` 映射文件（GitHub源）
4. 按优先级排序下载源

### 2. DLC列表获取
1. 从R2源获取 `index.json`（主索引）
2. 验证索引文件完整性
3. 解析DLC信息和元数据

### 3. 下载URL生成
1. 为每个DLC生成所有可用源的下载URL
2. R2和国内云源直接使用DLC ID映射
3. GitHub源通过映射文件转换为发布文件名
4. Gitee源根据DLC编号范围选择对应的release tag，然后使用映射文件名
5. 返回按优先级排序的URL列表

### 4. 下载执行
1. 按优先级尝试每个下载源
2. 失败时自动切换到下一个源
3. 记录下载统计和失败原因
4. 提供详细的进度反馈

## 错误处理

### 网络错误
- 超时重试（默认3次）
- 自动切换到备用源
- 详细错误日志记录

### 配置错误
- 启动时验证配置完整性
- 提供清晰的错误提示
- 支持配置热重载

### 文件完整性
- 下载完成后验证文件大小
- 支持断点续传（计划中）
- 自动清理失败的下载

## 扩展性设计

### 添加新源类型
1. 在 `SourceManager` 中添加新的格式处理器
2. 实现对应的URL生成逻辑
3. 更新配置验证规则
4. 添加相应的测试用例

### 自定义映射
- 支持不同的映射文件格式
- 允许动态映射加载
- 提供映射文件验证工具

## 性能优化

### 并发下载
- 支持多线程下载队列
- 智能带宽分配
- 内存使用优化

### 缓存策略
- 本地文件缓存
- URL结果缓存
- 配置缓存

## 测试和验证

### 单元测试
- `tools/final_test.py`: 完整系统测试
- 验证所有源的URL生成
- 测试故障转移逻辑

### 集成测试
- 实际下载验证
- 网络环境模拟
- 性能基准测试

## 监控和统计

### 下载统计
- 各源使用频率
- 下载成功率
- 平均下载速度

### 错误追踪
- 失败原因分类
- 网络问题诊断
- 配置问题识别

## 部署和维护

### 配置管理
- 版本化配置文件
- 向后兼容性保证
- 配置验证工具

### 监控告警
- 下载失败率阈值
- 源可用性检查
- 自动故障转移通知

## 安全考虑

- HTTPS强制使用
- 文件完整性验证
- 访问控制和限流
- 敏感信息保护

## 未来规划

- 支持更多云存储提供商
- 实现P2P下载功能
- 添加下载加速技术
- 支持自定义下载插件