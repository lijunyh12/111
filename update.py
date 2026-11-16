import requests
import sys
import re
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入 playwright
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

TOKEN_FILE = "token.txt"

def get_token_from_env():
    """优先从环境变量 (GitHub Secrets) 获取 Token"""
    return os.environ.get("IPTV_TOKEN", "").strip()

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
        print("\n❌ 未检测到 playwright 库")
        return None

    print("🚀 正在调用无头浏览器 (Linux环境)...")
    with sync_playwright() as p:
        try:
            # GitHub Actions 必须使用 headless=True
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                permissions=["clipboard-read", "clipboard-write"]
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            dialog_text = []
            page.on("dialog", lambda dialog: (dialog_text.append(dialog.message), dialog.accept()))

            print("🌐 正在打开网页...")
            page.goto("https://taoiptv.com/87468408/", wait_until="domcontentloaded", timeout=30000)
            
            print("⏳ 等待页面渲染...")
            page.wait_for_timeout(5000)
            
            token = None
            start_time = time.time()
            cloudflare_clicked = False
            
            # 由于服务器没界面，只能全自动点，最多等 30 秒
            while time.time() - start_time < 30:
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

                # 2. 尝试点击“获取Token”
                try:
                    is_clicked = page.evaluate("""
                        () => {
                            let elements = document.querySelectorAll('a, button, span, div, p');
                            for (let el of elements) {
                                let text = (el.innerText || el.textContent || "").replace(/\\s+/g, '');
                                if (text === '获取Token' || text === '获取') {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    if is_clicked:
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # 3. 检测剪贴板 / 源码 / 弹窗
                try:
                    clip = page.evaluate("navigator.clipboard.readText()")
                    if clip:
                        match = re.search(r'\b([a-zA-Z0-9]{16})\b', clip)
                        if match and "0x4AAAA" not in clip:
                            token = match.group(1)
                            print(f"✅ 成功从剪贴板抓取到 Token: {token}")
                            break
                except Exception:
                    pass
                
                try:
                    page_text = page.locator("body").inner_text()
                    matches = re.findall(r'\b[a-zA-Z0-9]{16}\b', page_text)
                    for m in matches:
                        if not m.startswith("0x4AAAA") and "PHPSESSID" not in m:
                            token = m
                            print(f"✅ 成功从网页源码抓取到 Token: {token}")
                            break
                    if token:
                        break
                except Exception:
                    pass
                
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

            browser.close()
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
            channels.append((current_name, line))
            current_name = None
    return channels

def check_stream(channel_info, timeout=5, max_cost=3.0):
    """测速函数：请求流地址，检查是否有效且速度达标"""
    cat, name, url = channel_info
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    start_time = time.time()
    try:
        # stream=True 表示不直接下载视频文件，只建立连接
        with requests.get(url, headers=headers, timeout=timeout, stream=True) as resp:
            if resp.status_code != 200:
                return None
            
            # 读取一小块数据，防止某些防反盗链返回假 200（如 HTML 网页）
            chunk = next(resp.iter_content(1024), None)
            if not chunk:
                return None
            
            # 如果读取到的是 HTML 代码，说明失效了
            if b"<html" in chunk.lower() or b"<head" in chunk.lower():
                return None

        cost_time = time.time() - start_time
        
        # 超过规定的最长时间直接判定为慢，丢弃
        if cost_time > max_cost:
            return None
            
        # 保留带有测速耗时的打印，方便查看
        return (cat, name, url, cost_time)
    except Exception:
        # 连接超时、请求失败等情况
        return None

def main():
    print("="*50)
    print("淘IPTV 直播源自动更新程序 (带测速)")
    print("="*50)

    # 1. 获取 Token 逻辑 (环境变量 -> 本地文件 -> 无头浏览器)
    token = get_token_from_env()
    
    if token:
        print(f"✅ 成功从 GitHub Secrets 读取到 Token: {token}")
    else:
        token = get_token_from_file()
        if token:
            print(f"✅ 成功从本地文件读取到 Token: {token}")
    
    if not token:
        print("⚠️ 未找到缓存的 Token，启动无头浏览器获取...")
        token = get_latest_token_auto()

    if not token:
        print("\n🚨 脚本无法自动提取到 Token。由于是在服务器环境，无法手动输入。")
        print("👉 建议：将你本地成功获取的 Token 填入 GitHub 仓库的 Secrets (名称设为 IPTV_TOKEN) 中。")
        sys.exit(1)

    save_token_to_file(token)
    print(f"\n🔗 当前使用的 Token 为: {token}")

    # 2. 生成带最新 Token 的 URL 列表
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

    raw_channels = [] # 存储 (cat, name, url)
    seen = set()
    print("\n开始获取并解析直播源...")

    has_valid_data = False

    # 3. 抓取与初步解析数据
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
                continue

            has_valid_data = True

            if text.startswith("#EXTM3U") or "#EXTINF" in text:
                print(f"🔍 检测到 M3U 格式，正在解析: {url}")
                parsed_lines = parse_m3u(text)
                for name, link in parsed_lines:
                    cat = classify(name, link)
                    key = (cat, name, link)
                    if key not in seen:
                        seen.add(key)
                        raw_channels.append((cat, name, link))
                print(f"✅ 成功解析 M3U: {url} (提取到 {len(parsed_lines)} 个频道)")
            else:
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "," not in line:
                        continue
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        name, link = parts[0].strip(), parts[1].strip()
                        if not link: continue
                        cat = classify(name, link)
                        key = (cat, name, link)
                        if key not in seen:
                            seen.add(key)
                            raw_channels.append((cat, name, link))
                print(f"✅ 成功获取 TXT: {url}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 获取失败 {url}: {e}")
        except Exception as e:
            print(f"❌ 发生未知错误 {url}: {e}")

    # 4. 并发测速与过滤
    valid_channels = []
    total_channels = len(raw_channels)
    
    if total_channels > 0:
        print(f"\n🔍 开始测速：共收集到 {total_channels} 个频道，正在并发测速剔除失效/慢速源...")
        # 控制并发数为 20，超时 5 秒，允许耗时 3 秒内
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(check_stream, ch, 5, 3.0): ch for ch in raw_channels}
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % 50 == 0:
                    print(f"   ... 已测速 {completed}/{total_channels} ...")
                
                result = future.result()
                if result:
                    valid_channels.append(result)
        
        print(f"✅ 测速完毕！存活频道: {len(valid_channels)} 个（剔除 {total_channels - len(valid_channels)} 个）")
    else:
        print("\n🚨 警告：没有收集到任何频道！")
        sys.exit(0)

    if len(valid_channels) == 0:
        print("\n🚨 警告：所有链接均失效或速度过慢，为防止覆盖原文件，本次不写入。")
        sys.exit(0)

    if len(valid_channels) < 10:
        print("\n🚨 警告：测速后存活的数据过少（少于10个），为防止覆盖原文件，本次不写入。")
        sys.exit(0)

    # 5. 重新按分类分组并写入
    grouped = {}
    for cat, name, link, _ in valid_channels:
        grouped.setdefault(cat, []).append(f"{name},{link}")

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
