import requests

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
]

def main():
    all_lines = []
    seen = set()
    print("开始获取并合并直播源...")

    for url in urls:
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
            
            print(f"✅ 成功获取: {url}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 获取失败 {url}: {e}")
        except Exception as e:
            print(f"❌ 发生未知错误 {url}: {e}")

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
