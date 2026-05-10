#!/usr/bin/env python3
"""高考真题 → 忆哒格式 (thin wrapper)

数据源: AGIEval (GitHub)
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import (
    read_input, write_output, to_yida, validate,
    dedup, print_stats, retry_fetch,
)

CDN_URL = "https://cdn.jsdelivr.net/gh/ruixiangcui/AGIEval@main/data/v1/gaokao-history.jsonl"
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "raw_data", "gaokao_history.txt")

def fetch_content():
    return retry_fetch(CDN_URL)

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
        src = obj.get("other", {}).get("source", "高考历史真题")
        options_text = "\n".join(options)
        year_match = re.search(r'(\d{4})', src)
        tags = ["高考", "历史", "选择题"]
        if year_match:
            tags.append(year_match.group(1))
        full_content = f"{question}\n\n{options_text}\n\n答案：({label})"
        items.append({"title": f"#{i}", "content": full_content, "tags": ",".join(tags), "source": src})
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="本地文件（不提供则在线获取）")
    ap.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    if args.input:
        content = read_input(args.input)
    else:
        content = fetch_content()

    items = parse(content)
    items = dedup(items, key_fields=["title"])
    print_stats(items)
    yida = to_yida(items, ["title", "content", "tags", "source"])
    write_output(yida, args.output)
