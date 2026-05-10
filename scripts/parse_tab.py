#!/usr/bin/env python3
"""制表符分隔 → 忆哒格式 (thin wrapper)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import read_input, write_output, to_yida, validate, auto_parse, dedup, print_stats

def parse(content):
    return auto_parse(content, hint='tab')

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    content = read_input(args.input)
    items, fields = parse(content)
    items = dedup(items)
    print_stats(items, {"字段数": len(fields)})
    yida = to_yida(items, fields)
    write_output(yida, args.output)
