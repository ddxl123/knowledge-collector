#!/usr/bin/env python3
"""解析缩进层级结构（词典式）→ 忆哒格式

格式示例:
    word1
      detail1
      detail2
    word2
      detail1

用法:
    python3 parse_indent.py <input_file>
    python3 parse_indent.py <input_file> -o out.txt
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats, parse_indented, dedup

def parse(content):
    return parse_indented(content)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析缩进层级格式")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("-o", "--output", help="输出文件路径")
    args = ap.parse_args()

    content = read_input(args.input)
    items = parse(content)
    items = dedup(items, key_fields=["key"])
    print_stats(items)

    yida = to_yida(items, ["key", "details"])
    ok, errs = validate(yida)
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
