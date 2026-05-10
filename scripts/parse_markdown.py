#!/usr/bin/env python3
"""解析 Markdown 表格 → 忆哒格式

支持标准 Markdown 表格格式：
    | word | meaning |
    |------|---------|
    | abandon | v. 放弃 |

用法:
    python3 parse_markdown.py <input_file>
    python3 parse_markdown.py <input_file> --fields word,meaning
    python3 parse_markdown.py <input_file> -o out.txt
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats, parse_markdown_table, dedup

def parse(content, field_names=None):
    """解析 Markdown 表格内容。

    Args:
        content: Markdown 文本
        field_names: 指定字段名（None 则使用表头）

    Returns:
        (items, field_names) 元组
    """
    items, headers = parse_markdown_table(content)

    if not items:
        return [], []

    if field_names:
        # 只保留指定字段
        filtered = []
        for item in items:
            filtered_item = {}
            for fn in field_names:
                filtered_item[fn] = item.get(fn, "")
            filtered.append(filtered_item)
        return filtered, field_names

    return items, headers

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析 Markdown 表格")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("--fields", help="字段名，逗号分隔（如 word,meaning）")
    ap.add_argument("-o", "--output", help="输出文件路径")
    args = ap.parse_args()

    content = read_input(args.input)

    field_names = args.fields.split(",") if args.fields else None
    items, field_names = parse(content, field_names)

    if not items:
        print("⚠️  未找到 Markdown 表格数据", file=sys.stderr)
        sys.exit(1)

    items = dedup(items)
    print_stats(items, {"字段": ", ".join(field_names)})

    yida = to_yida(items, field_names)
    ok, errs = validate(yida, expected_fields=len(field_names))
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
