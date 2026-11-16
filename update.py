import requests
import sys
import re
import os
import time

# 尝试导入 playwright
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

TOKEN_FILE = "token.txt"

def get_token_from_file():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                return token
    return None

def save_token_to_file(token):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token)
    print(f"💾 Token 已保存到 {TOKEN_FILE}。")

def get_latest_token_auto():
    if not HAS_PLAYWRIGHT:
        print("\n❌ 未检测到 playwright 库，请先运行: pip install playwright")
        return None

    print("🚀 正在调用 Chrome 浏览器...")
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir="./browser_data",
                headless=False, 
                channel="chrome", 
                ignore_default_args=["--enable-automation"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            
            # 隐藏自动化特征
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            dialog_text = []
            page.on("dialog", lambda dialog: (dialog_text.append(dialog.message), dialog.accept()))

            print("🌐 正在打开网页...")
            page.goto("https://taoiptv.com/87468408/", wait_until="domcontentloaded", timeout=30000)
            
            print("\n================== ⚠️ 自动处理中 ==================")
            print("👉 脚本正在通过底层 JS 强行点击“获取Token”按钮。")
            print("👉 如果脚本没点中，你手动去浏览器里点一下也可以，脚本会自动拦截结果。")
            print("====================================================\n")
            
            token = None
            start_time = time.time()
            cloudflare_clicked = False
            
            while time.time() - start_time < 120:
                # 1. 尝试自动点击 Cloudflare 验证
                if not cloudflare_clicked:
                    try:
                        cf_iframe = page.frame_locator('iframe[src*="challenges.cloudflare.com"]')
                        checkbox = cf_iframe.locator('input[type="checkbox"], .ctp-checkbox-label, body').first
                        if checkbox.is_visible(timeout=1000):
                            checkbox.click(force=True, timeout=2000)
                            print("🖱️ 发现 Cloudflare 验证，已自动点击！")
                            cloudflare_clicked = True
                            page.wait_for_timeout(3000)
                    except Exception:
                        pass 

                # 2. 尝试自动点击“获取Token”按钮 (注入 JavaScript 暴力点击)
                try:
                    # 注入 JS，寻找文字包含“获取Token”的元素
                    is_clicked = page.evaluate("""
                        () => {
                            let elements = document.querySelectorAll('a, button, span, div, p');
                            for (let el of elements) {
                                // 获取内部文字，并去除所有空白字符，兼容换行
                                let text = (el.innerText || el.textContent || "").replace(/\\s+/g, '');
                                if (text === '获取Token' || text === '获取' || text === 'Token') {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    if is_clicked:
                        # 如果点中了，稍微等一小下，防止频繁触发
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # 3. 检测剪贴板 (如果你手动点了，或者 JS 点成功了，这里马上就能抓到)
                try:
                    clip = page.evaluate("navigator.clipboard.readText()")
                    if clip:
                        match = re.search(r'\b([a-zA-Z0-9]{16})\b', clip)
                        # 排除掉 0x4AAAA 这种无用的 ID
                        if match and "0x4AAAA" not in clip:
                            token = match.group(1)
                            print(f"✅ 成功从剪贴板抓取到 Token: {token}")
                            break
                except Exception:
                    pass
                
                # 4. 检测网页源码文本 (如果剪贴板读不到，就暴力提取页面上的 16 位字符)
                try:
                    page_text = page.locator("body").inner_text()
                    # 找出所有 16 位字母数字
                    matches = re.findall(r'\b[a-zA-Z0-9]{16}\b', page_text)
                    for m in matches:
                        # 排除已知的错误特征
                        if not m.startswith("0x4AAAA") and "PHPSESSID" not in m:
                            token = m
                            print(f"✅ 成功从网页源码抓取到 Token: {token}")
                            break
                    if token:
                        break
                except Exception:
                    pass
                
                # 5. 检测弹窗
                if dialog_text:
                    for text in dialog_text:
                        match = re.search(r'\b([a-zA-Z0-9]{16})\b', text)
                        if match and "0x4AAAA" not in text:
                            token = match.group(1)
                            print(f"✅ 成功从弹窗抓取到 Token: {token}")
                            break
                    if token:
                        break
                        
                time.sleep(1)

            if not token:
                print("\n⌛ 自动提取超时。")
                token = input("👉 请在弹出的浏览器里手动操作，然后将 16 位 Token 粘贴到这里并回车：").strip()

            context.close()
            return token
        except Exception as e:
            print(f"❌ 获取发生错误: {e}")
            return None

# ---------------- 分类规则 ----------------
CATEGORY_RULES = [
    ("直播平台", [r"虎牙", r"斗鱼", r"快手", r"TikTok", r"Twitch", r"YY",
                  r"B站", r"哔哩哔哩", r"抖音", r"yximgs", r"douyincdn",
                  r"tiktokcdn", r"baheyi\.pages\.dev/(huya|douyu|kugou|laifeng|twitch)"]),
    ("央视", [r"CCTV", r"CGTN", r"中央"]),
    ("卫视", [r"卫视", r"东方卫视", r"江苏卫视", r"广东卫视", r"北京卫视",
              r"辽宁卫视", r"河北卫视", r"江西卫视", r"河南卫视", r"陕西卫视",
              r"湖北卫视", r"吉林卫视", r"青海卫视", r"东南卫视", r"海南卫视",
              r"海峡卫视", r"宁夏卫视", r"重庆卫视", r"三沙卫视", r"黑龙江卫视",
              r"兵团卫视", r"大湾区卫视", r"农林卫视"]),
    ("体育", [r"体育", r"赛事", r"篮球", r"足球", r"NBA", r"CBA", r"WCBA",
              r"羽毛球", r"斯诺克", r"台球", r"钓鱼", r"武术", r"电竞"]),
    ("影视", [r"电影", r"影院", r"影视", r"剧场", r"港片", r"新片"]), 
    ("少儿", [r"少儿", r"卡通", r"动画", r"中学生", r"教育", r"CETV"]),
    ("纪录", [r"纪录", r"发现", r"老故事", r"熊猫", r"旅游", r"环球"]),
    ("地方", [r"南京", r"江苏", r"上海", r"上视", r"海南", r"吉林", r"陕西",
              r"盐城", r"淮安", r"泰州", r"连云港", r"宿迁", r"徐州", r"南通",
              r"宜兴", r"溧水", r"镇江", r"广东", r"南方"]),
    ("音乐", [r"音乐", r"综艺", r"梨园", r"戏曲", r"秦腔", r"书画"]),
]

CATEGORY_ORDER = ["直播平台", "央视", "卫视", "地方", "体育", "影视", "少儿", "纪录", "音乐", "其他"]

def classify(name: str, url: str = "") -> str:
    name_upper = name.upper().strip()
    if name_upper.startswith("CCTV") or name_upper.startswith("CHC"):
        return "央视"

    text = f"{name} {url}"
    for cat, patterns in CATEGORY_RULES:
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return cat
    return "其他"

def format_txt_line(line: str) -> str:
    line = line.strip()
    if not line or line.startswith("#"):
        return line
    if "," not in line:
        return line
    name, url = line.split(",", 1)
    name = name.strip()
    url = url.strip()
    if not url:
        return line
    cat = classify(name, url)
    return f"{cat},{name},{url}"

def parse_m3u(text):
    channels = []
    lines = text.splitlines()
    current_name = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            if ',' in line:
                current_name = line.split(',')[-1].strip()
            else:
                match = re.search(r'tvg-name="([^"]+)"', line)
                current_name = match.group(1).strip() if match else "未知频道"
        elif not line.startswith("#") and current_name:
            channels.append(f"{current_name},{line}")
            current_name = None
    return channels

def main():
    print("="*50)
    print("淘IPTV 直播源自动更新程序")
    print("="*50)

    token = get_token_from_file()

    if not token:
        print("⚠️ 本地未找到缓存的 Token，启动浏览器获取...")
        token = get_latest_token_auto()

    if not token:
        print("\n🚨 脚本无法自动提取到 Token。")
        token = input("👉 请直接手动将 16 位 Token 粘贴到这里并回车：").strip()
        if not token:
            print("❌ 输入为空，程序终止。")
            sys.exit(1)

    if len(token) != 16:
        print(f"⚠️ 注意：你输入的 Token 长度为 {len(token)}，正常情况下应该是 16 位。")

    save_token_to_file(token)
    print(f"\n🔗 当前使用的 Token 为: {token}")

    urls = [
        f"https://taoiptv.com/lives/51023.txt?token={token}",
        f"https://taoiptv.com/lives/50023.txt?token={token}",
        f"https://taoiptv.com/lives/31023.txt?token={token}",
        f"https://taoiptv.com/lives/21023.txt?token={token}",
        f"https://taoiptv.com/lives/11023.txt?token={token}",
        f"https://taoiptv.com/lives/61023.txt?token={token}",
        f"https://taoiptv.com/lives/53023.txt?token={token}",
        f"https://taoiptv.com/lives/52023.txt?token={token}",
        f"https://taoiptv.com/lives/64023.txt?token={token}",
        "https://iptv.445569.xyz/live.m3u",
    ]

    grouped = {}
    seen = set()
    print("\n开始获取并合并直播源...")

    has_valid_data = False

    for url in urls:
        try:
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
                print(f"⚠️ 跳过失效链接 (Token无效): {url}")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                    print("🗑️ 已清除失效的本地 Token 缓存，请重新运行程序获取新 Token。")
                continue

            has_valid_data = True

            if text.startswith("#EXTM3U") or "#EXTINF" in text:
                print(f"🔍 检测到 M3U 格式，正在解析: {url}")
                parsed_lines = parse_m3u(text)
                for line in parsed_lines:
                    if "," not in line:
                        continue
                    name, link = line.split(",", 1)
                    name = name.strip()
                    link = link.strip()
                    cat = classify(name, link)
                    key = (cat, name, link)
                    if key in seen:
                        continue
                    seen.add(key)
                    grouped.setdefault(cat, []).append(f"{name},{link}")
                print(f"✅ 成功解析 M3U: {url} (提取到 {len(parsed_lines)} 个频道)")
            else:
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    formatted = format_txt_line(line)
                    if "," not in formatted:
                        continue
                    parts = formatted.split(",", 2)
                    if len(parts) < 3:
                        continue
                    cat, name, link = parts
                    key = (cat, name, link)
                    if key in seen:
                        continue
                    seen.add(key)
                    grouped.setdefault(cat, []).append(f"{name},{link}")
                print(f"✅ 成功获取 TXT: {url}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 获取失败 {url}: {e}")
        except Exception as e:
            print(f"❌ 发生未知错误 {url}: {e}")

    total = sum(len(v) for v in grouped.values())
    
    if not has_valid_data or total == 0:
        print("\n🚨 警告：所有链接均未返回有效数据！")
        print("👉 原因：Token 不正确或已过期。")
        print("👉 建议：删除 token.txt 文件，重新运行程序。")
        sys.exit(0)

    if total < 10:
        print("\n🚨 警告：抓取到的有效数据过少（少于10行），为防止覆盖原文件，本次不写入。")
        sys.exit(0)

    out_lines = []
    for cat in CATEGORY_ORDER:
        if cat not in grouped or not grouped[cat]:
            continue
        out_lines.append(f"{cat},#genre#")
        out_lines.extend(grouped[cat])
    for cat, items in grouped.items():
        if cat in CATEGORY_ORDER:
            continue
        out_lines.append(f"{cat},#genre#")
        out_lines.extend(items)

    try:
        with open("zb.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines))
        print(f"\n🎉 合并完成！共写入 {len(out_lines)} 行到 zb.txt")
        for cat in CATEGORY_ORDER:
            if cat in grouped:
                print(f"   - {cat}: {len(grouped[cat])} 个频道")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
