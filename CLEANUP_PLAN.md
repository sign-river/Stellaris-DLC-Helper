# 单源架构简化计划

## 概述
项目已从多源架构（R2/GitHub/Gitee/国内云）简化为单源架构（仅GitLink），需要清理大量废弃的多源管理代码。

---

## 🗑️ 可以完全删除的文件

### 1. **src/core/source_manager.py** (956行)
**原因**：整个文件都是多源管理逻辑
- 多源配置加载
- 源优先级管理
- GitHub/Gitee Release格式处理
- 测速逻辑（`measure_speed`, `get_best_download_source`）
- URL映射和转换（`get_download_urls_for_dlc`）
- Gitee分片Release处理（ste1-26, ste27-39）

**新架构**：不需要SourceManager，直接从GitLink API获取

---

## 📝 需要大幅简化的文件

### 2. **src/core/dlc_manager.py**
**废弃逻辑**：
- ❌ `self.source_manager = SourceManager()` (28行)
- ❌ `_fetch_from_index_json()` - 备用方式已不需要
- ❌ `_original_fetch_dlc_list()` - 旧的多源获取逻辑
- ❌ `get_download_urls_for_dlc()` 调用 (127, 191行)
- ❌ `get_source_by_name("domestic_cloud")` (171, 259行)
- ❌ `fetch_dlc_data_from_source()` (176, 265行)
- ❌ `build_dlc_url_map()` (309行)

**保留逻辑**：
- ✅ `_load_dlc_names()` - 从pairings.json加载
- ✅ `_get_dlc_name()` - 获取DLC名称
- ✅ `_fetch_from_gitlink_api()` - 主要获取方式
- ✅ `fetch_dlc_list()` - 简化为只调用GitLink API
- ✅ `get_installed_dlcs()` - DLC安装检测
- ✅ `is_dlc_installed()` - DLC安装检测

---

### 3. **src/gui/settings_dialog.py**
**废弃逻辑**：
- ❌ `source_manager` 参数和相关逻辑 (20, 23, 237行)
- ❌ 源选择下拉框 (478-493行)
  - "github": "GitHub"
  - "domestic_cloud": "国内云"
  - "gitee": "Gitee"
  - "r2": "R2"
- ❌ 测速按钮和逻辑
- ❌ `default_source` 配置 (408, 411行)

**建议**：移除整个源选择部分的UI，简化设置对话框

---

### 4. **src/gui/main_window.py**
**废弃逻辑**：
- ❌ GitHub按钮和图标 (226-265行)
  - `_open_github()` 方法
  - GitHub图标加载逻辑
  - 按钮创建和布局

**建议**：如果要保留外部链接，改为GitLink仓库链接

---

### 5. **src/config.py**
**废弃逻辑**：
- ❌ `DLC_SOURCES` 多源配置 (19-26行)
- ❌ `_get_best_source_url()` (28-40行)
- ❌ `DLC_SERVER_URL` (42行)
- ❌ `DLC_INDEX_URL` (43行) - index.json已废弃
- ❌ `domestic_cloud` 判断逻辑 (32行)

**保留**：
- ✅ `UPDATE_URL_BASE` - GitLink更新服务
- ✅ `APPINFO_URL` - GitLink AppInfo
- ✅ 其他网络/缓存配置

---

## 🔧 需要修改的文件

### 6. **src/core/downloader.py**
**可能需要检查**：
- 是否使用了 `source_manager`
- 是否有多源切换逻辑
- 是否有备用URL尝试逻辑

### 7. **src/core/installer.py**
**可能需要检查**：
- 是否依赖 `source_manager`
- 是否有源选择逻辑

### 8. **src/config_loader.py**
**废弃逻辑**：
- ❌ `DEFAULT_CONFIG` 中的多源配置
- ❌ 源相关的默认值

---

## 🎯 简化后的架构

### **新的 DLCManager（简化版）**
```python
class DLCManager:
    def __init__(self, game_path):
        self.game_path = game_path
        self.dlc_names = {}
        self._load_dlc_names()
    
    def _load_dlc_names(self):
        # 从pairings.json加载
        
    def _get_dlc_name(self, dlc_key):
        # 获取DLC名称
    
    def fetch_dlc_list(self):
        # 直接调用GitLink API
        return self._fetch_from_gitlink_api()
    
    def _fetch_from_gitlink_api(self):
        # GitLink API获取逻辑
        # 返回: [{"key": "dlc001", "name": "...", "url": "...", "size": "..."}]
    
    def get_installed_dlcs(self):
        # DLC安装检测
    
    def is_dlc_installed(self, dlc_key):
        # DLC安装检测
```

### **新的 Downloader（可能需要简化）**
- 移除多源切换逻辑
- 移除备用URL尝试
- 直接使用提供的URL下载

---

## 📊 代码简化统计

### 可删除文件：
- ✅ `src/core/source_manager.py` - **956行**

### 可大幅简化的文件：
- ⚡ `src/core/dlc_manager.py` - 预计删除 **~200行**
- ⚡ `src/gui/settings_dialog.py` - 预计删除 **~100行**
- ⚡ `src/gui/main_window.py` - 预计删除 **~50行**
- ⚡ `src/config.py` - 预计删除 **~30行**
- ⚡ `src/config_loader.py` - 预计删除 **~50行**

### **总计：预计删除约 1,400 行代码**

---

## ⚠️ 注意事项

### 1. **pairings.json 依然需要**
- 用于DLC名称提取
- 格式：`dlc001_symbols_of_domination.zip` → "Symbols Of Domination"

### 2. **GitLink API 依赖**
- API地址：`https://gitlink.org.cn/api/signriver/file-warehouse/releases.json`
- Tag: `ste` (固定)
- 返回完整的DLC列表和下载URL

### 3. **无备用方案**
- 如果GitLink API失败，程序将无法获取DLC列表
- 考虑添加本地缓存作为应急方案

### 4. **测速逻辑可删除**
- 单源无需测速选择
- 启动速度更快

---

## 🚀 实施步骤建议

### 阶段1：删除核心多源代码
1. 删除 `source_manager.py`
2. 简化 `dlc_manager.py`
3. 简化 `config.py`

### 阶段2：清理UI
4. 简化 `settings_dialog.py`（移除源选择）
5. 修改 `main_window.py`（移除GitHub按钮或改为GitLink）

### 阶段3：清理配置
6. 简化 `config_loader.py`
7. 清理 `config.json` 默认配置

### 阶段4：测试
8. 测试DLC列表获取
9. 测试DLC下载
10. 测试设置界面
11. 测试完整流程

---

## 📋 待确认的问题

1. **Downloader 是否使用了 source_manager？**
   - 需要检查下载器实现
   - 可能需要修改URL处理逻辑

2. **是否保留本地DLC列表缓存？**
   - 作为GitLink API失败时的应急方案
   - 或者直接移除缓存机制

3. **GitHub按钮改为什么？**
   - 改为GitLink仓库链接？
   - 改为项目主页？
   - 直接删除？

4. **设置对话框还需要保留什么？**
   - 游戏路径设置？
   - 缓存清理？
   - 其他配置项？

---

**文档创建时间**: 2026-01-12  
**状态**: 待实施
