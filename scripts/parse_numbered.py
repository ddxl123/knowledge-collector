#!/usr/bin/env python3
"""编号列表 → 忆哒格式 (thin wrapper)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import read_input, write_output, to_yida, validate, auto_parse, dedup, print_stats

def parse(content, field_names=None):
    items, fields = auto_parse(content, hint='numbered')
    if field_names and len(field_names) >= 2 and items:
        # 重新映射: word → field_names[0], meaning → field_names[1]
        remapped = []
        for item in items:
            remapped.append({field_names[0]: item.get("word", ""), field_names[1]: item.get("meaning", "")})
        return remapped, field_names
    return items, fields

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--fields")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    content = read_input(args.input)
    fn = args.fields.split(",") if args.fields else None
    items, fn = parse(content, fn)
    items = dedup(items)
    print_stats(items, {"字段": ", ".join(fn)})
    yida = to_yida(items, fn)
    write_output(yida, args.output)
