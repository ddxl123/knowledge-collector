#!/usr/bin/env python3
"""解析编号列表 → 忆哒格式

支持格式: 1. xxx, 1) xxx, 01. xxx 等
智能拆分 word 和 meaning（支持多种分隔符）

用法:
    python3 parse_numbered.py <input_file>
    python3 parse_numbered.py <input_file> --fields title,content
    python3 parse_numbered.py <input_file> -o out.txt
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import to_yida, validate, read_input, write_output, print_stats, dedup

# 常见分隔符模式（按优先级尝试）
SEPARATORS = [
    r'\s+[-–—:]\s+',     # 破折号/冒号
    r'\s{2,}',            # 多个空格
    r'\t',                # 制表符
    r'(?<=\w)\s+(?=[a-zA-Z\u4e00-\u9fff])',  # 单个空格（仅在单词后跟字母/中文之间）
]

def parse(content, field_names=None):
    """解析编号列表。

    Args:
        content: 原始文本
        field_names: 指定字段名（None 则自动拆分为 word + meaning）

    Returns:
        (items, field_names) 元组
    """
    items = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\d+[.)\s]+(.+)$', line)
        if not m:
            continue

        rest = m.group(1).strip()

        if field_names and len(field_names) == 1:
            # 单字段模式
            items.append({field_names[0]: rest})
            continue

        # 尝试智能拆分
        word, meaning = _split_word_meaning(rest)

        if field_names and len(field_names) >= 2:
            item = {field_names[0]: word, field_names[1]: meaning}
            # 多余字段留空
            for fn in field_names[2:]:
                item[fn] = ""
            items.append(item)
        else:
            items.append({"word": word, "meaning": meaning})

    return items, field_names or ["word", "meaning"]


def _split_word_meaning(text):
    """智能拆分单词和释义。"""
    # 尝试各种分隔符
    for sep_pattern in SEPARATORS:
        parts = re.split(sep_pattern, text, maxsplit=1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return parts[0].strip(), parts[1].strip()

    # 兜底：如果文本较短（<20字符），可能是纯单词
    if len(text) < 20:
        return text, ""

    # 文本较长时，取前几个词作为 word，其余作为 meaning
    words = text.split(None, 3)
    if len(words) >= 2:
        return words[0], " ".join(words[1:])

    return text, ""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="解析编号列表格式")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("--fields", help="字段名，逗号分隔（如 word,meaning 或 title,content）")
    ap.add_argument("-o", "--output", help="输出文件路径")
    args = ap.parse_args()

    content = read_input(args.input)

    field_names = args.fields.split(",") if args.fields else None
    items, field_names = parse(content, field_names)

    if not items:
        print("⚠️  未找到编号列表数据", file=sys.stderr)
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
