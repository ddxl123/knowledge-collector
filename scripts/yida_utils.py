#!/usr/bin/env python3
"""忆哒格式共享工具模块

所有解析脚本应 import 此模块，避免重复代码。
用法：
    from yida_utils import to_yida, validate, write_output, read_input
"""

import sys
import re
import os


def to_yida(items, field_names=None):
    """将解析结果转换为忆哒批量生成碎片格式。

    Args:
        items: list of dict，每个 dict 是一条知识点
        field_names: 字段名列表，如 ["word", "meaning"]。
                     若为 None，则使用 dict 的所有 key（按插入顺序）。

    Returns:
        忆哒格式字符串，如 "{{word}}{{meaning}}▮{{word}}{{meaning}}"

    Example:
        >>> to_yida([{"word": "abandon", "meaning": "v. 放弃"}])
        '{{abandon}}{{v. 放弃}}'
        >>> to_yida([{"q": "1+1=?", "a": "2", "tag": "数学"}], ["q", "a", "tag"])
        '{{1+1=?}}{{2}}{{数学}}'
    """
    if not items:
        return ""

    if field_names is None:
        field_names = list(items[0].keys())

    fragments = []
    for item in items:
        fields = []
        for fn in field_names:
            val = item.get(fn, "")
            # 转义字段值中的 {{ }} 边界情况
            val = str(val).strip()
            fields.append(f"{{{{{val}}}}}")
        fragments.append("".join(fields))

    return "▮".join(fragments)


def validate(yida_str, expected_fields=None):
    """验证忆哒格式字符串的正确性。

    Args:
        yida_str: 忆哒格式字符串
        expected_fields: 每个知识点期望的字段数（None 则自动检测）

    Returns:
        (is_valid, errors) 元组
    """
    errors = []

    if not yida_str:
        return True, []

    fragments = yida_str.split("▮")

    if expected_fields is None:
        # 自动检测第一个片段的字段数
        first = fragments[0]
        expected_fields = first.count("{{")

    for i, frag in enumerate(fragments):
        open_count = frag.count("{{")
        close_count = frag.count("}}")

        if open_count != close_count:
            errors.append(f"片段 #{i+1}: 括号不匹配 ({{ ={open_count}, }} ={close_count})")

        if open_count != expected_fields:
            errors.append(f"片段 #{i+1}: 期望 {expected_fields} 个字段，实际 {open_count} 个")

        # 检查空字段
        field_values = re.findall(r'\{\{(.*?)\}\}', frag)
        for j, val in enumerate(field_values):
            if not val.strip():
                errors.append(f"片段 #{i+1}, 字段 #{j+1}: 内容为空")

    return len(errors) == 0, errors


def read_input(path=None):
    """读取输入内容。支持文件路径或 stdin。

    Args:
        path: 文件路径。None 则从 stdin 读取。

    Returns:
        文件内容字符串
    """
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    elif path:
        print(f"⚠️  文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    else:
        return sys.stdin.read()


def write_output(content, path=None, preview_lines=5):
    """输出结果。写入文件（如有路径）并打印预览。

    Args:
        content: 忆哒格式字符串
        path: 输出文件路径（None 则只打印到 stdout）
        preview_lines: 预览的片段数
    """
    if path:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 已保存到 {path}", file=sys.stderr)

    # 打印预览
    fragments = content.split("▮")
    total = len(fragments)
    preview = "▮".join(fragments[:preview_lines])

    if total > preview_lines:
        print(f"📊 共 {total} 条，预览前 {preview_lines} 条：", file=sys.stderr)

    print(preview)

    if total > preview_lines:
        print(f"\n... 还有 {total - preview_lines} 条，已保存到文件", file=sys.stderr)


def print_stats(items, extra=None):
    """打印解析统计信息。"""
    print(f"📊 共解析 {len(items)} 条", file=sys.stderr)
    if extra:
        for k, v in extra.items():
            print(f"   {k}: {v}", file=sys.stderr)


# === 通用解析模式 ===

def parse_delimited(content, delimiter, min_cols=2, skip_header=True):
    """通用分隔符解析。

    Args:
        content: 原始文本
        delimiter: 分隔符（如 '\\t', ' - ', ':', '|'）
        min_cols: 最少列数
        skip_header: 是否跳过首行（自动检测：首行无中文则跳过）

    Returns:
        list of dict，key 为 col_0, col_1, ...
    """
    lines = [l for l in content.strip().splitlines() if l.strip()]
    if not lines:
        return []

    start = 0
    if skip_header:
        first = lines[0]
        if not any('\u4e00' <= c <= '\u9fff' for c in first):
            start = 1

    items = []
    for line in lines[start:]:
        cols = [c.strip() for c in line.split(delimiter)]
        if len(cols) >= min_cols:
            item = {f"col_{i}": col for i, col in enumerate(cols)}
            items.append(item)

    return items


def parse_numbered_list(content, pattern=r'^\d+[.)\s]+(.+)$'):
    """解析编号列表。

    Args:
        content: 原始文本
        pattern: 编号正则（需有一个捕获组）

    Returns:
        list of dict，key 为 "content"
    """
    items = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(pattern, line)
        if m:
            items.append({"content": m.group(1).strip()})
    return items


def parse_key_value(content, separator=r'\s*[-–—:]\s*', key_first=True):
    """解析 key-value 对。

    Args:
        content: 原始文本
        separator: 键值分隔正则
        key_first: True=key在前，False=value在前

    Returns:
        list of dict，key 为 "key", "value"
    """
    items = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(separator, line, maxsplit=1)
        if len(parts) == 2:
            if key_first:
                items.append({"key": parts[0].strip(), "value": parts[1].strip()})
            else:
                items.append({"key": parts[1].strip(), "value": parts[0].strip()})
    return items


def parse_indented(content, key_pattern=None):
    """解析缩进层级结构。

    Args:
        content: 原始文本
        key_pattern: 识别主键行的正则（None 则非缩进行即为主键）

    Returns:
        list of dict，key 为 "key", "details"
    """
    items = []
    current = None

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        is_indented = line[0] in (' ', '\t')

        if is_indented:
            if current:
                current["details"] += (" " + stripped if current["details"] else stripped)
            continue

        # 新主键行
        if current:
            items.append(current)

        if key_pattern:
            m = re.match(key_pattern, line.strip())
            if m:
                current = {"key": m.group(1).strip(), "details": ""}
            else:
                current = {"key": line.strip(), "details": ""}
        else:
            current = {"key": line.strip(), "details": ""}

    if current:
        items.append(current)

    return items
