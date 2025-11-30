import requests
import time

def measure_speed(url, description, threshold_mb):
    print(f"正在测试 [{description}] ... ")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # 请求 200MB 数据
        "Range": "bytes=0-209715199" 
    }

    try:
        # 连接 3s 超时，读取 8s 超时
        with requests.get(url, headers=headers, stream=True, timeout=(3.0, 8.0)) as response:
            # 1. 检查状态码
            if not response.ok:
                print(f"   [X] 失败: 服务器返回状态码 {response.status_code}")
                return False, 0.0

            # 2. 检查 Content-Length (诊断文件是否变小了)
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
                if duration >= 5.0:
                    print("   [√] 停止原因: 满 5 秒时间到")
                    break
                
                if total_downloaded >= 70 * 1024 * 1024:
                    print("   [√] 停止原因: 速度太快 (超过100MB)")
                    break
            else:
                # 如果循环自然结束（即文件读完了，也没触发 break）
                print("   [!] 停止原因: 文件被下载完了 (文件太小?)")

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
        print("   [X] 连接超时 (3秒内未连上)\n")
        return False, 0.0
    except Exception as e:
        print(f"   [X] 发生错误: {e}\n")
        return False, 0.0

def get_best_download_url():
    # 请确保这里填的是那个 70MB 文件的地址
    url_r2 = "https://dlc.dlchelper.top/dlc/test/test.bin"
    url_github = "https://github.com/sign-river/File_warehouse/releases/download/test/test.bin"
    url_domestic = "http://47.100.2.190/dlc/test/test.bin" 
    url_gitee = "https://gitee.com/signriver/file_warehouse/releases/download/test/test.bin"
 

    print("=" * 40)
    print("开始诊断模式测速 (5秒采样)")
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