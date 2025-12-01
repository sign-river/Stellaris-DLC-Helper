import requests
import time

def test_speed(url, timeout=10):
    """
    简单的速度测试函数，返回每秒下载的字节数
    
    参数:
        url: 测试URL
        timeout: 超时时间（秒）
        
    返回:
        float: 速度（字节/秒），失败返回0
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        start_time = time.time()
        total_downloaded = 0
        
        with requests.get(url, headers=headers, stream=True, timeout=(7.0, timeout)) as response:
            if not response.ok:
                return 0
            
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    break
                
                total_downloaded += len(chunk)
                elapsed = time.time() - start_time
                
                # 超时或下载足够数据就停止
                if elapsed >= timeout or total_downloaded >= 70 * 1024 * 1024:
                    break
        
        final_duration = time.time() - start_time
        if final_duration <= 0.001:
            final_duration = 0.001
        
        return total_downloaded / final_duration
        
    except Exception:
        return 0

def measure_speed(url, description, threshold_mb):
    print(f"正在测试 [{description}] ... ")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # 请求 200MB 数据
        "Range": "bytes=0-209715199" 
    }

    try:
        # 【修改点1】连接超时放宽到 5s，读取超时放宽到 20s (防 R2 丢包报错)
        with requests.get(url, headers=headers, stream=True, timeout=(5.0, 20.0)) as response:
            # 1. 检查状态码
            if not response.ok:
                print(f"   [X] 失败: 服务器返回状态码 {response.status_code}")
                return False, 0.0

            # 2. 检查 Content-Length
            content_length = response.headers.get('Content-Length')
            if content_length:
                mb_size = int(content_length) / 1024 / 1024
                print(f"   [i] 服务器响应大小: {mb_size:.2f} MB")
            else:
                print(f"   [i] 服务器未返回文件大小 (可能是分块传输)")

            total_downloaded = 0
            start_time = time.time()
            first_chunk = True
            
            # 3. 开始下载循环
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk: break
                
                if first_chunk:
                    first_chunk = False
                    start_time = time.time() # 真正的计时开始
                    continue

                total_downloaded += len(chunk)
                
                current_time = time.time()
                duration = current_time - start_time
                
                # --- 停止条件诊断 ---
                # 【修改点2】确保这里是 10.0 秒
                if duration >= 10.0:
                    print("   [√] 停止原因: 满 10 秒时间到")
                    break
                
                if total_downloaded >= 70 * 1024 * 1024:
                    print("   [√] 停止原因: 速度太快 (超过70MB)")
                    break
            else:
                print("   [!] 停止原因: 文件被下载完了")

            # 4. 计算结果
            final_duration = time.time() - start_time
            if final_duration <= 0.001: final_duration = 0.001

            speed_mb = (total_downloaded / 1024 / 1024) / final_duration
            
            print(f"   [i] 耗时: {final_duration:.2f}秒 | 下载量: {total_downloaded/1024/1024:.2f} MB")
            print(f"   >>> 最终速度: {speed_mb:.2f} MB/s", end="")
            
            if speed_mb > threshold_mb:
                print(f" -> 达标 (>{threshold_mb} MB/s)\n")
                return True, speed_mb
            else:
                print(" -> 未达标\n")
                return False, speed_mb

    except requests.exceptions.ConnectTimeout:
        print("   [X] 连接超时 (5秒内未连上)\n")
        return False, 0.0
    except Exception as e:
        print(f"   [X] 发生错误: {e}\n")
        return False, 0.0

def get_best_download_url():
    # 确保这里填的是那个 70MB 文件的地址
    url_r2 = "https://dlc.dlchelper.top/dlc/test/test2.bin"
    url_github = "https://github.com/sign-river/File_warehouse/releases/download/test/test.bin"
    url_domestic = "http://47.100.2.190/dlc/test/test.bin" 
    url_gitee = "https://gitee.com/signriver/file_warehouse/releases/download/test/test.bin"

    print("=" * 40)
    # 【修改点3】更新文案显示
    print("开始诊断模式测速 (10秒采样)")
    print("=" * 40)
    
    # 1. R2
    ok, _ = measure_speed(url_r2, "R2云存储", 3.0)
    if ok: return "R2", url_r2

    # 2. GitHub
    ok, _ = measure_speed(url_github, "GitHub", 2.0)
    if ok: return "GitHub", url_github

    # 3. 国内
    ok, _ = measure_speed(url_domestic, "国内云服务器", 2.0)
    if ok: return "Domestic", url_domestic

    print("-" * 40)
    print("自动切换至 Gitee 兜底")
    return "Gitee", url_gitee

if __name__ == "__main__":
    src, url = get_best_download_url()
    print(f"最终选择: {src}")