# 补丁目录

这个目录用于存放 CreamAPI 补丁文件。

## 📁 补丁文件

补丁包含3个文件，直接放在 `patches/` 目录下：

```
patches/
├── README.md           # 本说明文件
├── steam_api.dll       # Steam API 32位补丁
├── steam_api64.dll     # Steam API 64位补丁
└── cream_api.ini       # CreamAPI 配置文件
```

## 📝 文件说明

- **steam_api.dll** - 32位 Steam API 模拟器
- **steam_api64.dll** - 64位 Steam API 模拟器
- **cream_api.ini** - 配置文件（包含AppID和DLC列表）

## 🎯 补丁应用流程

程序会自动执行以下步骤：

### 1. 扫描游戏目录
递归扫描游戏根目录，查找所有 `steam_api.dll` 和 `steam_api64.dll` 文件位置

### 2. 备份原始文件
```
steam_api.dll → steam_api_o.dll
steam_api64.dll → steam_api64_o.dll
```

### 3. 替换补丁文件
将 `patches/` 目录下的补丁文件复制到游戏目录，覆盖原始文件

### 4. 生成配置文件
- 读取 `cream_api.ini` 模板
- 将 `SAC_DLC` 占位符替换为从服务器获取的实际DLC列表
- 生成格式示例：
```ini
[dlc]
1158310 = Ancient Relics Story Pack
1140001 = Utopia
1158300 = MegaCorp
...
```
- 复制到游戏目录

## 🔄 移除补丁流程

移除补丁时会：
1. 删除补丁的 `steam_api.dll` 和 `steam_api64.dll`
2. 将备份文件还原：
   - `steam_api_o.dll → steam_api.dll`
   - `steam_api64_o.dll → steam_api64.dll`
3. 删除 `cream_api.ini` 配置文件

## ⚠️ 注意事项

- 程序会递归搜索游戏目录，为所有找到的 Steam API 位置应用补丁
- 应用补丁前会自动创建完整备份
- DLC列表会从服务器动态获取，无需手动配置
- 仅支持 Stellaris (AppID: 281990)
