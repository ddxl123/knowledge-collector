#!/usr/bin/env python3
"""解析 CSV 文件 → 忆哒格式

自动检测分隔符（逗号/制表符/分号），支持自定义字段映射。

用法:
    python3 parse_csv.py <input_file>
    python3 parse_csv.py <input_file> --fields word,meaning
    python3 parse_csv.py <input_file> --fields word,phonetic,meaning -o out.txt
"""

import sys, os, csv, io
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats, dedup

def detect_dialect(content, sample_lines=5):
    """自动检测 CSV 分隔符"""
    sample = "\n".join(content.strip().splitlines()[:sample_lines])
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=',\t;|')
        return dialect
    except csv.Error:
        # 默认逗号
        return csv.excel

def parse(content, field_names=None, has_header=True):
    """解析 CSV 内容。

    Args:
        content: CSV 文本内容
        field_names: 字段名列表（None 则从表头读取）
        has_header: 是否有表头行

    Returns:
        (items, field_names) 元组
    """
    dialect = detect_dialect(content)
    reader = csv.reader(io.StringIO(content), dialect)

    rows = list(reader)
    if not rows:
        return [], []

    # 确定字段名
    if field_names:
        start = 1 if has_header else 0
    elif has_header:
        field_names = [f.strip() for f in rows[0]]
        start = 1
    else:
        field_names = [f"col_{i}" for i in range(len(rows[0]))]
        start = 0

    items = []
    for row in rows[start:]:
        if not any(cell.strip() for cell in row):
            continue
        item = {}
        for i, fn in enumerate(field_names):
            item[fn] = row[i].strip() if i < len(row) else ""
        items.append(item)

    return items, field_names

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析 CSV 格式")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("--fields", help="字段名，逗号分隔（如 word,meaning）")
    ap.add_argument("--no-header", action="store_true", help="无表头行")
    ap.add_argument("-o", "--output", help="输出文件路径")
    args = ap.parse_args()

    content = read_input(args.input)

    field_names = args.fields.split(",") if args.fields else None
    has_header = not args.no_header

    items, field_names = parse(content, field_names, has_header)
    items = dedup(items)
    print_stats(items, {"字段": ", ".join(field_names)})

    yida = to_yida(items, field_names)
    ok, errs = validate(yida, expected_fields=len(field_names))
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
