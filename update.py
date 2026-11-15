import requests
import sys
import re

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
    "https://iptv.445569.xyz/live.m3u",
]

# ---------------- 分类规则 ----------------
# 按顺序匹配，命中第一个就归入该类
CATEGORY_RULES = [
    # 直播平台放在最前面，优先级最高
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
    ("影视", [r"电影", r"影院", r"影视", r"CHC", r"剧场", r"港片", r"新片"]),
    ("少儿", [r"少儿", r"卡通", r"动画", r"中学生", r"教育", r"CETV"]),
    ("纪录", [r"纪录", r"发现", r"老故事", r"熊猫", r"旅游", r"环球"]),
    ("地方", [r"南京", r"江苏", r"上海", r"上视", r"海南", r"吉林", r"陕西",
              r"盐城", r"淮安", r"泰州", r"连云港", r"宿迁", r"徐州", r"南通",
              r"宜兴", r"溧水", r"镇江", r"广东", r"南方"]),
    ("音乐", [r"音乐", r"综艺", r"梨园", r"戏曲", r"秦腔", r"书画"]),
]

# 输出顺序（直播平台放最前面）
CATEGORY_ORDER = ["直播平台", "央视", "卫视", "地方", "体育", "影视", "少儿", "纪录", "音乐", "其他"]


def classify(name: str, url: str = "") -> str:
    """根据频道名（和链接）返回分类名，默认 '其他'"""
    text = f"{name} {url}"
    for cat, patterns in CATEGORY_RULES:
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return cat
    return "其他"


def format_txt_line(line: str) -> str:
    """把 '频道名,链接' 拆开，返回 '分类,频道名,链接'；无法拆分则归到其他"""
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
    """解析 M3U 格式，返回 (频道名, 链接) 的列表"""
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
    grouped = {}
    seen = set()
    print("开始获取并合并直播源...")

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
                print(f"⚠️ 跳过失效链接 (Token过期或HTML报错): {url}")
                continue

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
    if total == 0:
        print("🚨 警告：所有链接均未返回有效数据，为防止覆盖原文件，本次不写入 zb.txt。")
        sys.exit(0)

    if total < 10:
        print("🚨 警告：抓取到的有效数据过少（少于10行），为防止覆盖原文件，本次不写入。")
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
        print(f"🎉 合并完成！共写入 {len(out_lines)} 行到 zb.txt")
        for cat in CATEGORY_ORDER:
            if cat in grouped:
                print(f"   - {cat}: {len(grouped[cat])} 个频道")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
