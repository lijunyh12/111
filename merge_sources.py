import requests
import sys
import re

# ==========================================
# 在这里填入你获取到的最新有效链接
# ==========================================
urls = [
    "https://taoiptv.com/lives/51023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/50023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/31023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/21023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/11023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/61023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/53023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/52023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/64023.txt?token=62c3858b7ba5763a",
    "https://iptv.445569.xyz/live.m3u",  # 新增的 M3U 链接
]

def parse_m3u(text):
    """解析 M3U 格式，返回 (频道名, 链接) 的列表"""
    channels = []
    lines = text.splitlines()
    current_name = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 提取频道名，例如：#EXTINF:-1 tvg-name="CCTV1",CCTV1
        if line.startswith("#EXTINF"):
            # 尝试从逗号后提取名称
            if ',' in line:
                current_name = line.split(',')[-1].strip()
            else:
                # 如果没有逗号，尝试从 tvg-name 提取
                match = re.search(r'tvg-name="([^"]+)"', line)
                if match:
                    current_name = match.group(1).strip()
                else:
                    current_name = "未知频道"

        # 提取链接（非 # 开头的行）
        elif not line.startswith("#") and current_name:
            channels.append(f"{current_name},{line}")
            current_name = None  # 重置，准备读取下一个

    return channels

def main():
    all_lines = []
    seen = set()
    print("开始获取并合并直播源...")

    for url in urls:
        try:
            # 设置 User-Agent，防止被简单的反爬虫机制拦截
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            text = resp.text.strip()

            if not text:
                print(f"⚠️ 跳过空数据链接: {url}")
                continue

            if "Authentication Failed" in text or "认证token参数不正确" in text or "<html" in text.lower():
                print(f"⚠️ 跳过失效链接 (Token过期或HTML报错): {url}")
                continue

            # 判断是否为 M3U 格式
            if text.startswith("#EXTM3U") or "#EXTINF" in text:
                print(f"🔍 检测到 M3U 格式，正在解析: {url}")
                parsed_lines = parse_m3u(text)
                for line in parsed_lines:
                    if line not in seen:
                        seen.add(line)
                        all_lines.append(line)
                print(f"✅ 成功解析 M3U: {url} (提取到 {len(parsed_lines)} 个频道)")
            
            else:
                # 原有的 TXT 格式解析逻辑
                for line in text.splitlines():
                    line = line.strip()
                    if line and line not in seen:
                        seen.add(line)
                        all_lines.append(line)
                print(f"✅ 成功获取 TXT: {url}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 获取失败 {url}: {e}")
        except Exception as e:
            print(f"❌ 发生未知错误 {url}: {e}")

    # 核心判断：如果没有抓到任何数据，直接退出，不覆盖原文件
    if not all_lines:
        print("🚨 警告：所有链接均未返回有效数据，为防止覆盖原文件，本次不写入 zb.txt。")
        sys.exit(0)

    if len(all_lines) < 10:
         print("🚨 警告：抓取到的有效数据过少（少于10行），可能所有源都失效了，为防止覆盖原文件，本次不写入。")
         sys.exit(0)

    # 写入文件
    try:
        with open("zb.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(all_lines))
        print(f"🎉 合并完成！共写入 {len(all_lines)} 行到 zb.txt")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
