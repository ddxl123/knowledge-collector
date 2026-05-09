#!/usr/bin/env python3
"""解析制表符分隔的多列数据 → 忆哒格式

自动检测列数：
  2列: word<TAB>meaning
  3列: word<TAB>phonetic<TAB>meaning

用法:
    python3 parse_tab.py <input_file>
    python3 parse_tab.py <input_file> -o out.txt
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats

def parse(content):
    lines = [l for l in content.strip().splitlines() if l.strip()]
    if not lines:
        return []

    # 跳过表头（首行无中文则视为表头）
    start = 0
    if not any('\u4e00' <= c <= '\u9fff' for c in lines[0]):
        start = 1

    items = []
    for line in lines[start:]:
        cols = line.split('\t')
        if len(cols) >= 3:
            items.append({
                "word": cols[0].strip(),
                "phonetic": cols[1].strip(),
                "meaning": cols[2].strip()
            })
        elif len(cols) == 2:
            items.append({
                "word": cols[0].strip(),
                "meaning": cols[1].strip()
            })
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析制表符分隔格式")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("-o", "--output", help="输出文件路径")
    args = ap.parse_args()

    content = read_input(args.input)
    items = parse(content)

    # 根据实际字段数选择输出
    if items and "phonetic" in items[0]:
        fields = ["word", "phonetic", "meaning"]
    else:
        fields = ["word", "meaning"]

    print_stats(items, {"字段数": len(fields)})

    yida = to_yida(items, fields)
    ok, errs = validate(yida)
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
