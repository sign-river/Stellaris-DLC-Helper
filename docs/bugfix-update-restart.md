# 修复：自动更新重启报错问题

## 问题描述

### 问题 1：开发环境下重启报错
在开发环境自动更新完成后，点击"立即重启"按钮会报错：
```
FileNotFoundError: [Errno 2] No such file or directory: 
'C:\\Users\\32173\\AppData\\Local\\Temp\\_MEI80762\\customtkinter\\assets\\themes\\blue.json'
```

### 问题 2：生产环境（exe）下重启报错
在打包后的 exe 环境中，更新完成后点击"立即重启"也会报错：
```
ImportError: cannot import name '_imaging' from 'PIL'
(C:\Users\32173\AppData\Local\Temp\_MEI160202\PIL\__init__.py)
```

## 问题原因

### 问题 1 的原因
程序没有正确区分 **开发环境（Python 脚本模式）** 和 **生产环境（打包后的 exe 模式）**，导致在开发环境下运行时，更新完成后尝试启动不存在的 exe 文件。

### 问题 2 的原因
在 PyInstaller 打包的 exe 中：
1. exe 运行时会将资源解压到临时目录 `_MEI<随机数>`
2. 使用 `os.execl()` 重启 exe 时，会在**同一个进程空间**中替换程序
3. 但是旧的 `_MEI` 临时目录可能已经损坏或不完整
4. 导致新进程无法正确加载 PIL 等模块

**正确的做法**：在 exe 模式下应该使用 `subprocess.Popen()` 启动**新的独立进程**，然后退出当前进程。这样新进程会创建自己的 `_MEI` 临时目录。

## 修复方案

### 1. 修改 `src/gui/update_dialog.py` 的 `_restart_app()` 方法

**最终修复后的代码：**
```python
def _restart_app(self):
    """重启应用程序"""
    try:
        # 检查是否正在下载DLC，如果是则暂停下载
        if hasattr(self.master, 'is_downloading') and self.master.is_downloading:
            self.logger.info("检测到正在下载DLC，正在暂停下载...")
            self.master.pause_download()
            # 保存下载状态标记
            self._save_download_state()

        import sys
        import os
        import subprocess
        
        # 判断是否为打包后的 exe 模式
        is_frozen = getattr(sys, 'frozen', False)
        
        # 如果 exe 替换已排程（在 apply_update 中写入 .new 并创建替换脚本），且是 exe 模式，直接退出主进程以便批处理替换
        if is_frozen and hasattr(self.updater, 'exe_replacement_pending') and self.updater.exe_replacement_pending:
            # 触发退出，让替换批处理接管并重启
            self.logger.info("exe 替换已排程，退出以完成替换")
            os._exit(0)
        
        # 在 exe 模式下，使用 subprocess.Popen 启动新进程然后退出
        # 这样可以避免 PyInstaller 临时目录 _MEI 的问题
        if is_frozen:
            exe_path = sys.executable
            self.logger.info(f"exe 模式：启动新进程后退出: {exe_path}")
            # 启动新进程（不等待）
            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
            # 短暂延迟确保新进程启动
            import time
            time.sleep(0.5)
            # 退出当前进程
            os._exit(0)
        else:
            # 开发环境：直接重启当前进程
            python = sys.executable
            self.logger.info(f"开发环境：重启程序: {python} {sys.argv}")
            os.execl(python, python, *sys.argv)
    except Exception as e:
        self.logger.error(f"重启失败: {e}")
        messagebox.showerror("错误", f"重启失败: {e}")
```

**关键改进：**
1. **添加 exe 模式检测**：使用 `getattr(sys, 'frozen', False)` 判断是否为打包后的 exe
2. **exe 模式使用独立进程**：使用 `subprocess.Popen()` 启动新进程，避免 `_MEI` 临时目录问题
3. **开发模式使用 execl**：在开发环境下继续使用 `os.execl()` 重启 Python 脚本
4. **三种情况分别处理**：
   - exe 模式 + exe_replacement_pending：等待批处理替换并重启
   - exe 模式 + 无需替换：启动新进程后退出
   - 开发模式：直接 execl 重启

### 2. 修改 `src/core/updater.py` 的 `_replace_files()` 方法

**修改后的代码：**
```python
# 如果有待替换的文件，生成替换脚本/调用 helper 统一处理
if scheduled_replacements:
    try:
        import sys
        # 仅在 exe 模式下才使用替换脚本
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            self._create_replace_script(scheduled_replacements, owner_pid=os.getpid())
        else:
            # 开发环境下直接尝试覆盖（可能需要手动重启）
            self.logger.warning("开发环境检测到待替换文件，请手动重启程序")
            for new_file, dst_file in scheduled_replacements:
                self.logger.info(f"待替换: {new_file} -> {dst_file}")
    except Exception as e:
        self.logger.warning(f"创建统一替换脚本失败: {e}")
```

### 3. 修改 `src/core/updater.py` 的 `_create_replace_script()` 方法

在方法开头添加 exe 模式检查：

```python
def _create_replace_script(self, new_dst_pairs, owner_pid: int = None) -> None:
    """创建 Windows 批处理脚本用于等待主程序退出再替换 exe 并重启（或使用 helper exe）。"""
    import sys
    # 仅在 exe 模式下使用此方法
    if not getattr(sys, 'frozen', False):
        self.logger.warning("_create_replace_script 仅在 exe 模式下使用")
        return
    
    # ... 原有代码
```

### 4. 修改 `src/gui/update_dialog.py` 的 `_show_success()` 方法

只在 exe 模式下显示 exe 替换提示：

```python
import sys
is_frozen = getattr(sys, 'frozen', False)

message_text = "程序已成功更新到最新版本。\n请重启程序以应用更改。"
# 仅在 exe 模式下且有 exe 替换时显示特殊提示
if is_frozen and hasattr(self.updater, 'exe_replacement_pending') and self.updater.exe_replacement_pending:
    message_text = '更新已准备好，但需要重新启动以完成替换（会在退出后自动应用）。\n请点击"立即重启"以退出并完成更新。'
```

## 修复效果

- ✅ **开发环境**：直接使用 `os.execl()` 重启 Python 脚本，不会尝试启动不存在的 exe
- ✅ **打包后的 exe（可直接替换）**：使用 `subprocess.Popen()` 启动新进程，避免 `_MEI` 临时目录问题
- ✅ **打包后的 exe（需要延迟替换）**：正确使用 updater_helper 或批处理脚本进行 exe 替换和重启
- ✅ **避免混淆**：清晰区分三种模式，避免在错误的环境下使用错误的重启方式
- ✅ **更好的提示**：根据不同模式显示合适的提示信息

## 为什么 exe 模式要用 subprocess.Popen 而不是 os.execl？

PyInstaller 打包的 exe 运行机制：
1. **启动时**：exe 将所有资源（Python 解释器、库文件等）解压到临时目录 `_MEI<随机数>`
2. **运行时**：从 `_MEI` 目录加载所有模块和资源
3. **退出时**：清理 `_MEI` 临时目录

使用 `os.execl()` 的问题：
- 在**同一个进程**中替换程序映像
- 但是旧的 `_MEI` 目录可能已经部分清理或损坏
- 新程序尝试从旧的 `_MEI` 目录加载模块，导致 ImportError

使用 `subprocess.Popen()` 的优势：
- 启动**全新的独立进程**
- 新进程会创建**新的 `_MEI` 目录**
- 完全避免临时目录混淆问题

## 测试建议

1. **开发环境测试**：
   - 运行 `python main.py`
   - 触发自动更新
   - 下载更新后点击"立即重启"
   - ✅ 验证程序是否正确重启，不会报找不到文件的错误

2. **打包后 exe 测试（可直接替换文件）**：
   - 运行打包后的 exe 文件
   - 触发自动更新
   - 下载更新后点击"立即重启"
   - ✅ 验证程序是否启动新进程并正确重启

3. **打包后 exe 测试（文件被占用，需要延迟替换）**：
   - 运行打包后的 exe 文件
   - 触发自动更新
   - 下载更新后点击"立即重启"
   - ✅ 验证 updater_helper 是否正确替换 exe 并重启

## 相关文件

- `src/gui/update_dialog.py` - 更新对话框，处理重启逻辑
- `src/core/updater.py` - 更新器核心，处理文件替换
- `tools/updater_helper.py` - 辅助工具，用于替换正在运行的 exe
