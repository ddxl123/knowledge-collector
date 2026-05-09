#!/usr/bin/env python3
"""解析 JSON/JSONL 文件 → 忆哒格式

支持两种格式：
  - JSON 数组: [{"word": "...", "meaning": "..."}, ...]
  - JSONL（每行一个 JSON 对象）

用法:
    python3 parse_json.py <input_file>
    python3 parse_json.py <input_file> --fields word,meaning
    python3 parse_json.py <input_file> --fields title,content,answer -o out.txt
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats

def parse(content, field_names=None):
    """解析 JSON 或 JSONL 内容。

    Args:
        content: JSON 文本内容
        field_names: 要提取的字段名（None 则使用所有字段）

    Returns:
        (items, field_names) 元组
    """
    content = content.strip()
    items = []

    # 尝试 JSON 数组
    if content.startswith('['):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                items = data
        except json.JSONDecodeError:
            pass

    # JSONL 或 JSON 数组解析失败
    if not items:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    items.append(obj)
            except json.JSONDecodeError:
                continue

    if not items:
        return [], []

    # 确定字段名
    if field_names is None:
        # 使用第一个对象的所有 key
        field_names = list(items[0].keys())

    # 只保留指定字段
    filtered = []
    for item in items:
        filtered_item = {}
        for fn in field_names:
            val = item.get(fn, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val, ensure_ascii=False)
            filtered_item[fn] = str(val)
        filtered.append(filtered_item)

    return filtered, field_names

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析 JSON/JSONL 格式")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("--fields", help="字段名，逗号分隔（如 word,meaning）")
    ap.add_argument("-o", "--output", help="输出文件路径")
    args = ap.parse_args()

    content = read_input(args.input)

    field_names = args.fields.split(",") if args.fields else None
    items, field_names = parse(content, field_names)
    print_stats(items, {"字段": ", ".join(field_names)})

    yida = to_yida(items, field_names)
    ok, errs = validate(yida, expected_fields=len(field_names))
    if not ok:
        print("⚠️  格式验证警告:", file=sys.stderr)
        for e in errs:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
