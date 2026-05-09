#!/usr/bin/env python3
"""解析 'word - meaning' 破折号分隔格式 → 忆哒格式

用法:
    python3 parse_dash.py <input_file>              # 输出到 stdout
    python3 parse_dash.py <input_file> -o out.txt   # 保存到文件
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats

def parse(content):
    """匹配 word - meaning（支持 - – — 三种破折号）"""
    import re
    items = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^(\S+)\s*[-–—]\s*(.+)$', line)
        if m:
            items.append({"word": m.group(1), "meaning": m.group(2).strip()})
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析破折号分隔格式")
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
