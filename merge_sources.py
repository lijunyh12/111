import requests
import re

# 你的 .txt 链接列表（请确保 Token 有效）
urls_txt = [
    "https://taoiptv.com/lives/51023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/50023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/31023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/21023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/11023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/61023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/53023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/52023.txt?token=62c3858b7ba5763a",
    "https://taoiptv.com/lives/64023.txt?token=62c3858b7ba5763a",
]

# 新增的 M3U 链接
url_m3u = "https://iptv.445569.xyz/live.m3u"

def main():
    all_lines = []
    seen = set()
    print("开始获取并合并直播源...")

    # 1. 处理 .txt 源
    for url in urls_txt:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            text = resp.text

            if "Authentication Failed" in text or "认证token参数不正确" in text:
                print(f"⚠️ 跳过失效链接 (Token过期): {url}")
                continue

            for line in text.splitlines():
                line = line.strip()
                if line and line not in seen:
                    seen.add(line)
                    all_lines.append(line)
            
            print(f"✅ 成功获取 TXT: {url}")

        except Exception as e:
            print(f"❌ 获取失败 {url}: {e}")

    # 2. 处理 M3U 源 (解析 #EXTINF 和 链接)
    print(f"开始解析 M3U 源: {url_m3u}")
    try:
        resp = requests.get(url_m3u, timeout=15)
        resp.raise_for_status()
        m3u_text = resp.text
        
        # 简单解析 M3U：提取频道名和 URL
        lines = m3u_text.splitlines()
        current_name = ""
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF:"):
                # 提取逗号后面的频道名
                if "," in line:
                    current_name = line.split(",", 1)[1].strip()
            elif line and not line.startswith("#"):
                # 这是一个 URL
                if current_name:
                    # 按照你的 txt 格式拼接：频道名,URL
                    entry = f"{current_name},{line}"
                    if entry not in seen:
                        seen.add(entry)
                        all_lines.append(entry)
                    current_name = "" # 重置
                else:
                    # 如果没找到名字，直接加链接（可忽略）
                    if line not in seen:
                        seen.add(line)
                        all_lines.append(line)
        print(f"✅ 成功获取并解析 M3U")

    except Exception as e:
        print(f"❌ 获取 M3U 失败: {e}")

    # 3. 写入文件
    if not all_lines:
        print("🚨 警告：所有链接均无法获取有效内容，放弃写入文件。")
        return

    try:
        with open("zb.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(all_lines))
        print(f"🎉 合并完成！共写入 {len(all_lines)} 行到 zb.txt")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")

if __name__ == "__main__":
    main()
