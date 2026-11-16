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

def save_token_to_file(token):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token)
    print(f"💾 Token 已保存到 {TOKEN_FILE}。")

def get_latest_token_auto():
    """纯自动模式：使用无头浏览器并开启深度伪装提取 Token"""
    if not HAS_PLAYWRIGHT:
        print("\n❌ 未检测到 playwright 库，请检查依赖是否安装正确。")
        return None

    print("🚀 正在启动云端无头浏览器 (深度伪装模式)...")
    
    with sync_playwright() as p:
        try:
            # 启动无头 Chromium，并加入防自动化检测参数
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai"
            )
            
            # 注入深度反侦测脚本（覆盖 webdriver、伪造插件、掩盖无头特征）
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                window.chrome = { runtime: {} };
                
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter.apply(this, arguments);
                };
            """)

            page = context.new_page()

            print("🌐 正在打开网页...")
            page.goto("https://taoiptv.com/87468408/", wait_until="domcontentloaded", timeout=30000)
            
            token = None
            cloudflare_clicked = False
            
            print("⏳ 检测页面状态并尝试绕过 Cloudflare...")
            # 等待最多 30 秒，尝试过盾或加载页面
            for i in range(30):
                try:
                    # 尝试自动点击 Cloudflare 验证框
                    if not cloudflare_clicked:
                        try:
                            cf_iframe = page.frame_locator('iframe[src*="challenges.cloudflare.com"]')
                            checkbox = cf_iframe.locator('input[type="checkbox"], .ctp-checkbox-label, body').first
                            if checkbox.is_visible(timeout=500):
                                checkbox.click(force=True, timeout=1000)
                                print("🖱️ 发现 Cloudflare 验证框，已尝试自动点击！")
                                cloudflare_clicked = True
                                page.wait_for_timeout(2000)
                        except Exception:
                            pass

                    html_content = page.content()
                    if "copyToken" in html_content or "获取Token" in html_content:
                        print("✅ 页面加载成功，正在提取 Token...")
                        break
                except Exception:
                    pass 
                
                time.sleep(1)

            # 尝试提取 DOM 属性
            try:
                page.wait_for_selector("#copyToken", state="attached", timeout=5000)
                token = page.locator("#copyToken").get_attribute("data-clipboard-text")
                if token:
                    print(f"✅ 成功从网页 DOM 节点提取到 Token: {token}")
            except Exception:
                # 备选正则
                try:
                    html_content = page.content()
                    match = re.search(r'id=["\']copyToken["\'][^>]*data-clipboard-text=["\']([a-zA-Z0-9]{16})["\']', html_content)
                    if match:
                        token = match.group(1)
                        print(f"✅ 成功从 HTML 源码正则提取到 Token: {token}")
                except:
                    pass

            browser.close()
            return token
        except Exception as e:
            print(f"❌ 浏览器操作发生错误: {e}")
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
    """根据频道名和链接进行分类"""
    name_upper = name.upper().strip()
    # 强制规则：CCTV 和 CHC 开头归为央视
    if name_upper.startswith("CCTV") or name_upper.startswith("CHC"):
        return "央视"

    text = f"{name} {url}"
    for cat, patterns in CATEGORY_RULES:
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return cat
    return "其他"

def parse_m3u(text):
    """解析 M3U 格式"""
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

def main():
    print("="*50)
    print("淘IPTV 直播源自动更新程序 (纯自动提取版)")
    print("="*50)

    # 1. 纯自动获取 Token
    token = get_latest_token_auto()

    if not token:
        print("\n🚨 严重警告：无法自动提取到 Token！")
        print("👉 原因：GitHub 云服务器 IP 被 Cloudflare 拦截，且未能在无头模式下破解。")
        print("👉 建议：如果你的运行环境能打开网页，请尝试多运行几次，或者优化你的网络代理。")
        sys.exit(1) # 直接退出，避免无意义的下载请求

    save_token_to_file(token)
    print(f"\n🔗 当前使用的 Token 为: {token}")

    # 2. 生成 URL 列表
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

    # 3. 抓取与解析
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

    # 4. 安全校验与写入
    total_channels = len(raw_channels)
    
    if not has_valid_data or total_channels == 0:
        print("\n🚨 警告：所有链接均未返回有效数据！为防止覆盖原文件，本次不写入。")
        sys.exit(0)

    if total_channels < 10:
        print("\n🚨 警告：抓取到的有效数据过少（少于10行），为防止覆盖原文件，本次不写入。")
        sys.exit(0)

    # 5. 重新按分类分组
    grouped = {}
    for cat, name, link in raw_channels:
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
