#!/usr/bin/env python3
"""解析 KyleBing/english-vocabulary 四级词汇表 → 忆哒格式

数据源: GitHub CDN（制表符分隔 word<TAB>meaning）
用法:
    python3 parse_cet4.py                     # 在线获取
    python3 parse_cet4.py <input_file>        # 从本地文件
    python3 parse_cet4.py -o out.txt          # 保存到文件
"""

import sys, os, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats

CDN_URL = "https://cdn.jsdelivr.net/gh/KyleBing/english-vocabulary@master/3%20%E5%9B%9B%E7%BA%A7-%E4%B9%B1%E5%BA%8F.txt"
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "raw_data", "cet4_high_freq.txt")

def fetch_content():
    print("🌐 正在从 CDN 获取四级词汇数据...", file=sys.stderr)
    req = urllib.request.Request(CDN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")

def parse(content):
    items = []
    seen = set()
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        word = parts[0].strip()
        meaning = parts[1].strip()
        if word.lower() in seen:
            continue
        seen.add(word.lower())
        items.append({"word": word, "meaning": meaning})
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析四级词汇表")
    ap.add_argument("input", nargs="?", help="输入文件路径（不提供则在线获取）")
    ap.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help="输出文件路径")
    args = ap.parse_args()

    if args.input:
        content = read_input(args.input)
    else:
        content = fetch_content()

    items = parse(content)
    print_stats(items)

    yida = to_yida(items, ["word", "meaning"])
    ok, errs = validate(yida)
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
