#!/usr/bin/env python3
"""解析 AGIEval 高考历史选择题 → 忆哒格式

数据源: GitHub CDN（JSONL 格式）
用法:
    python3 parse_gaokao_history.py                     # 在线获取
    python3 parse_gaokao_history.py <input_file>        # 从本地文件
    python3 parse_gaokao_history.py -o out.txt          # 保存到文件
"""

import sys, os, json, re, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats, dedup

CDN_URL = "https://cdn.jsdelivr.net/gh/ruixiangcui/AGIEval@main/data/v1/gaokao-history.jsonl"
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "raw_data", "gaokao_history.txt")

def fetch_content():
    print("🌐 正在从 CDN 获取高考历史真题...", file=sys.stderr)
    req = urllib.request.Request(CDN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")

def parse(content):
    items = []
    for i, line in enumerate(content.strip().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        question = obj.get("question", "")
        options = obj.get("options", [])
        label = obj.get("label", "")
        source = obj.get("other", {}).get("source", "高考历史真题")

        options_text = "\n".join(options)
        year_tag = ""
        year_match = re.search(r'(\d{4})', source)
        if year_match:
            year_tag = year_match.group(1)

        tags = ["高考", "历史", "选择题"]
        if year_tag:
            tags.append(year_tag)

        full_content = f"{question}\n\n{options_text}\n\n答案：({label})"

        items.append({
            "title": f"高考历史 #{i}",
            "content": full_content,
            "tags": ",".join(tags),
            "source": source
        })
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析高考历史选择题")
    ap.add_argument("input", nargs="?", help="输入文件路径（不提供则在线获取）")
    ap.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help="输出文件路径")
    args = ap.parse_args()

    if args.input:
        content = read_input(args.input)
    else:
        content = fetch_content()

    items = parse(content)
    items = dedup(items, key_fields=["title"])
    print_stats(items)

    yida = to_yida(items, ["title", "content", "tags", "source"])
    ok, errs = validate(yida, expected_fields=4)
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
