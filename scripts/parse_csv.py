#!/usr/bin/env python3
"""CSV → 忆哒格式 (thin wrapper over yida_utils.auto_parse)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import read_input, write_output, to_yida, validate, auto_parse, dedup, print_stats

def parse(content, field_names=None, has_header=True):
    items, fields = auto_parse(content, hint='csv')
    if field_names and items:
        items = [{fn: item.get(fn, "") for fn in field_names} for item in items]
        fields = field_names
    return items, fields

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--fields")
    ap.add_argument("--no-header", action="store_true")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    content = read_input(args.input)
    fn = args.fields.split(",") if args.fields else None
    items, fn = parse(content, fn)
    items = dedup(items)
    print_stats(items, {"字段": ", ".join(fn)})
    yida = to_yida(items, fn)
    validate(yida, expected_fields=len(fn))
    write_output(yida, args.output)
