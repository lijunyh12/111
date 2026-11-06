import requests
import sys

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
]

def main():
    all_lines = []
    seen = set()
    print("开始获取并合并直播源...")

    for url in urls:
        try:
            # 发送请求
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            text = resp.text.strip()

            # 1. 拦截空数据
            if not text:
                print(f"⚠️ 跳过空数据链接: {url}")
                continue

            # 2. 拦截 Token 失效返回的 HTML 报错页面
            if "Authentication Failed" in text or "认证token参数不正确" in text or "<html" in text.lower():
                print(f"⚠️ 跳过失效链接 (Token过期或HTML报错): {url}")
                continue

            # 3. 正常解析有效内容
            for line in text.splitlines():
                line = line.strip()
                # 过滤空行，并进行整行去重
                if line and line not in seen:
                    seen.add(line)
                    all_lines.append(line)
            
            print(f"✅ 成功获取: {url}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 获取失败 {url}: {e}")
        except Exception as e:
            print(f"❌ 发生未知错误 {url}: {e}")

    # ==========================================
    # 核心判断：如果没有抓到任何数据，直接退出，不覆盖原文件
    # ==========================================
    if not all_lines:
        print("🚨 警告：所有链接均未返回有效数据，为防止覆盖原文件，本次不写入 zb.txt。")
        sys.exit(0) # 正常退出，GitHub Actions 不会报错，只是没有文件变更

    # 如果只抓到了极少量的数据（比如只有几行），也可能存在问题，可以选择拦截
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
        sys.exit(1) # 写入失败则报错退出

if __name__ == "__main__":
    main()
