#!/usr/bin/env python3
"""解析编号列表 → 忆哒格式

支持格式: 1. xxx, 1) xxx, 01. xxx 等

用法:
    python3 parse_numbered.py <input_file>
    python3 parse_numbered.py <input_file> -o out.txt
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats

def parse(content):
    """解析编号列表，自动拆分 word 和 meaning"""
    import re
    items = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\d+[.)\s]+(.+)$', line)
        if m:
            rest = m.group(1).strip()
            parts = rest.split(None, 1)
            if len(parts) == 2:
                items.append({"word": parts[0], "meaning": parts[1]})
            else:
                items.append({"word": rest, "meaning": ""})
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析编号列表格式")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("-o", "--output", help="输出文件路径")
    args = ap.parse_args()

    content = read_input(args.input)
    items = parse(content)
    print_stats(items)

    yida = to_yida(items, ["word", "meaning"])
    ok, errs = validate(yida)
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
