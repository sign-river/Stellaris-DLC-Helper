# 服务器DLC管理工具使用说明

## 功能概述

`server_manager.py` 是一个独立的服务器管理工具，用于管理服务器端的 Stellaris DLC 文件。

## 安装依赖

```bash
pip install paramiko requests
```

## 首次使用

1. 配置文件会自动从 `config.json.example` 创建

2. 编辑 `config.json` 填入服务器信息（可选，也可以运行时输入）：
```json
{
  "server_management": {
    "ssh_ip": "your-server-ip",
    "ssh_username": "root",
    "ssh_password": "your-password"
  }
}
```

3. 运行管理工具：
```bash
python server_manager.py
```

## 功能说明

### 1. 上传DLC文件
- 自动弹出文件选择对话框
- 支持一次选择多个文件批量上传
- 显示上传进度和结果
- 上传到服务器路径：`<server_base_path>/files/`

### 2. 删除服务器DLC
- 显示服务器上所有DLC的有序列表
- 支持多种序号输入方式：
  - 单个：`5`
  - 范围：`5-15`
  - 多个：`1,3,5`
  - 组合：`1,3,5-10,12`
- 删除前需要确认

### 3. 生成 index.json
- 自动扫描服务器DLC文件
- 生成标准格式的 index.json
- 自动上传到服务器：`<server_base_path>/index.json`
- 保持DLC列表有序

### 4. 下载 index.json
- 从服务器下载 index.json 到本地
- 保存为 `server_index.json`
- 显示基本统计信息

### 5. 更新游戏AppID和DLC信息
- 从 Steam API 获取 Stellaris (281990) 的最新信息
- 生成 `stellaris_appinfo.json` 文件
- 上传到服务器：`<server_appinfo_path>/stellaris_appinfo.json`
- 用于生成 cream_api.ini 所需的DLC列表

### 6. 查看服务器DLC列表
- 显示服务器上所有DLC
- 包含文件名、大小、修改时间
- 按文件名排序

## 服务器路径结构

```
<server_base_path>/
├── dlc/
│   ├── files/              # DLC文件存储目录
│   │   ├── dlc001_xxx.zip
│   │   ├── dlc002_xxx.zip
│   │   └── ...
│   └── index.json          # DLC索引文件
└── appinfo/
    └── stellaris_appinfo.json  # 游戏AppID和DLC信息
```

## 注意事项

1. **安全性**：
   - 服务器配置信息存储在 `config.json` 的 `server_management` 字段中
   - `config.json` 包含敏感信息，已在 `.gitignore` 中忽略
   - 请勿将此文件提交到版本控制

2. **权限要求**：
   - 确保服务器用户有权限访问 `<server_base_path>` 目录
   - 如果目录不存在，工具会自动创建

3. **网络要求**：
   - 需要能够SSH连接到服务器
   - 默认使用22端口
   - 更新AppID信息需要访问 Steam API

4. **文件格式**：
   - 推荐DLC文件命名格式：`dlc001_description.zip`
   - 这样可以自动解析生成更友好的显示名称

## 示例操作流程

### 首次部署DLC
```bash
# 1. 运行工具
python server_manager.py

# 2. 选择 "1. 上传DLC文件"
# 3. 在弹出的对话框中选择所有DLC文件
# 4. 等待上传完成

# 5. 选择 "3. 生成 index.json"
# 6. 自动生成并上传索引文件

# 7. 选择 "5. 更新游戏AppID和DLC信息"
# 8. 获取最新的Steam数据
```

### 更新单个DLC
```bash
# 1. 选择 "1. 上传DLC文件"
# 2. 选择新的DLC文件上传

# 3. 选择 "3. 生成 index.json"
# 4. 更新索引文件
```

### 清理旧DLC
```bash
# 1. 选择 "6. 查看服务器DLC列表"
# 2. 记录要删除的DLC序号

# 3. 选择 "2. 删除服务器DLC"
# 4. 输入序号（如：1,3,5-10）

# 5. 选择 "3. 生成 index.json"
# 6. 更新索引文件
```

## 故障排除

### 连接失败
- 检查服务器IP是否正确
- 检查SSH服务是否运行
- 检查防火墙设置
- 验证用户名和密码

### 上传失败
- 检查服务器磁盘空间
- 检查文件权限
- 检查网络连接稳定性

### Steam API访问失败
- 检查网络连接
- Steam API可能有访问限制
- 可以稍后重试
