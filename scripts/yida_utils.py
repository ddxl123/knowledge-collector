#!/usr/bin/env python3
"""忆哒格式共享工具模块

所有解析脚本应 import 此模块，避免重复代码。
用法：
    from yida_utils import to_yida, validate, write_output, read_input
    from yida_utils import dedup, clean_field, merge, auto_parse, batch_process
"""

import sys
import re
import os
import json
import csv
import io
import codecs


# ============================================================
# 核心转换
# ============================================================

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
            val = clean_field(str(val).strip())
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

        # 检查非法字符（字段值中不应包含 {{ }} ▮）
        for j, val in enumerate(field_values):
            for ch in ['{{', '}}', '▮']:
                if ch in val:
                    errors.append(f"片段 #{i+1}, 字段 #{j+1}: 包含非法字符 '{ch}'")

    return len(errors) == 0, errors


# ============================================================
# 输入/输出
# ============================================================

def _detect_encoding(path, sample_size=8192):
    """检测文件编码。优先尝试 UTF-8，回退到 GBK/GB2312。"""
    # 尝试 UTF-8 (with BOM detection)
    with open(path, 'rb') as f:
        raw = f.read(sample_size)

    # BOM 检测
    if raw.startswith(codecs.BOM_UTF8):
        return 'utf-8-sig'
    if raw.startswith(codecs.BOM_UTF16_LE):
        return 'utf-16-le'
    if raw.startswith(codecs.BOM_UTF16_BE):
        return 'utf-16-be'

    # 尝试 UTF-8
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass

    # 尝试 GBK（覆盖 GB2312/GB18030）
    try:
        raw.decode('gbk')
        return 'gbk'
    except UnicodeDecodeError:
        pass

    # 尝试 GB18030
    try:
        raw.decode('gb18030')
        return 'gb18030'
    except UnicodeDecodeError:
        pass

    # 兜底
    return 'utf-8'


def read_input(path=None):
    """读取输入内容。支持文件路径或 stdin。自动检测编码。

    Args:
        path: 文件路径。None 则从 stdin 读取。

    Returns:
        文件内容字符串
    """
    if path and os.path.isfile(path):
        enc = _detect_encoding(path)
        with open(path, encoding=enc) as f:
            content = f.read()
        if enc != 'utf-8':
            print(f"📝 检测到编码: {enc}", file=sys.stderr)
        return content
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

    Returns:
        写入的文件路径（如有），否则 None
    """
    if path:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 已保存到 {path}", file=sys.stderr)

    fragments = content.split("▮")
    total = len(fragments)
    preview = "▮".join(fragments[:preview_lines])

    if total > preview_lines:
        print(f"📊 共 {total} 条，预览前 {preview_lines} 条：", file=sys.stderr)

    print(preview)

    if total > preview_lines:
        print(f"\n... 还有 {total - preview_lines} 条，已保存到文件", file=sys.stderr)

    return path


def print_stats(items, extra=None):
    """打印解析统计信息。"""
    print(f"📊 共解析 {len(items)} 条", file=sys.stderr)
    if extra:
        for k, v in extra.items():
            print(f"   {k}: {v}", file=sys.stderr)


# ============================================================
# 数据清洗与合并
# ============================================================

def clean_field(value):
    """清洗字段值，移除忆哒格式保留字符。

    Args:
        value: 原始字段值

    Returns:
        清洗后的字符串
    """
    if not isinstance(value, str):
        value = str(value)
    # 移除 {{ }} ▮ 等保留字符
    value = value.replace('{{', '').replace('}}', '').replace('▮', '')
    # 合并多余空白
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def dedup(items, key_fields=None, case_insensitive=True):
    """按指定字段去重。

    Args:
        items: list of dict
        key_fields: 用于去重的字段名列表。None 则使用第一个 dict 的所有 key。
        case_insensitive: 是否忽略大小写

    Returns:
        去重后的 list of dict
    """
    if not items:
        return []

    if key_fields is None:
        key_fields = list(items[0].keys())

    seen = set()
    result = []

    for item in items:
        vals = []
        for kf in key_fields:
            v = str(item.get(kf, ""))
            if case_insensitive:
                v = v.lower()
            vals.append(v)
        key = tuple(vals)
        if key not in seen:
            seen.add(key)
            result.append(item)

    removed = len(items) - len(result)
    if removed > 0:
        print(f"🔄 去重: {len(items)} → {len(result)} (移除 {removed} 条)", file=sys.stderr)

    return result


def merge(*item_lists):
    """合并多个数据源的 items 列表。

    Args:
        *item_lists: 多个 list of dict

    Returns:
        合并后的 list of dict（自动去重）
    """
    all_items = []
    for items in item_lists:
        if items:
            all_items.extend(items)

    if not all_items:
        return []

    # 合并后自动去重
    return dedup(all_items)


# ============================================================
# 通用解析模式
# ============================================================

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


def parse_markdown_table(content):
    """解析 Markdown 表格。

    支持标准 Markdown 表格格式：
        | Header1 | Header2 |
        |---------|---------|
        | val1    | val2    |

    Returns:
        (items, field_names) 元组
    """
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    if len(lines) < 3:
        return [], []

    # 解析表头
    header_line = lines[0]
    headers = [h.strip() for h in header_line.strip('|').split('|')]

    # 跳过分隔线（第二行）
    data_start = 2

    items = []
    for line in lines[data_start:]:
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.strip('|').split('|')]
        item = {}
        for i, h in enumerate(headers):
            item[h] = cols[i] if i < len(cols) else ""
        items.append(item)

    return items, headers


# ============================================================
# 自动格式检测
# ============================================================

def auto_parse(content, hint=None):
    """自动检测输入格式并解析。

    支持直接传入 hint='csv'/'json' 等格式名，
    也支持 hint 为解析模块名如 'parse_csv'。

    Args:
        content: 原始文本内容
        hint: 格式提示（csv/json/tab/dash/markdown/numbered/indent 或 parse_csv 等）

    Returns:
        (items, field_names) 元组
    """
    content = content.strip()
    if not content:
        return [], []

    # 标准化 hint（支持 'parse_csv' → 'csv'）
    if hint and hint.startswith('parse_'):
        hint = hint[6:]  # 去掉 'parse_' 前缀

    # 根据 hint 快速匹配
    if hint == 'csv':
        return _parse_csv_auto(content)
    elif hint == 'json':
        return _parse_json_auto(content)
    elif hint == 'tab':
        return _parse_tab_auto(content)
    elif hint == 'dash':
        return _parse_dash_auto(content)
    elif hint == 'markdown':
        return parse_markdown_table(content)
    elif hint == 'numbered':
        items = parse_numbered_list(content)
        return items, ["content"]
    elif hint == 'indent':
        items = parse_indented(content)
        return items, ["key", "details"]

    # 自动检测
    # 忆哒格式（已转换过的）— 优先检测，避免被 JSON 解析器误判
    if '▮' in content and '{{' in content:
        return _parse_yida_auto(content)

    # JSON 数组或 JSONL
    if content.startswith('[') or content.startswith('{'):
        return _parse_json_auto(content)

    # Markdown 表格（有 | 和 |---| 分隔线）
    if re.search(r'\|.*\|', content) and re.search(r'\|[\s\-:]+\|', content):
        return parse_markdown_table(content)

    # CSV（逗号或分号分隔，且行内逗号/分号数量一致）
    csv_result = _try_csv(content)
    if csv_result:
        return csv_result

    # 制表符分隔
    lines = [l for l in content.splitlines() if l.strip()]
    if lines and '\t' in lines[0]:
        return _parse_tab_auto(content)

    # 破折号分隔
    if re.search(r'\S+\s*[-–—]\s+\S+', content):
        return _parse_dash_auto(content)

    # 缩进层级
    if any(l[0] in (' ', '\t') for l in lines if l):
        items = parse_indented(content)
        return items, ["key", "details"]

    # 编号列表
    if re.search(r'^\d+[.)\s]', content, re.MULTILINE):
        items = parse_numbered_list(content)
        return items, ["content"]

    # 兜底：按行解析
    items = [{"content": l.strip()} for l in lines if l.strip()]
    return items, ["content"]


def _parse_yida_auto(content):
    """解析已有的忆哒格式字符串，转回 items 列表。"""
    fragments = content.split('▮')
    items = []
    field_names = None

    for frag in fragments:
        if not frag.strip():
            continue
        fields = re.findall(r'\{\{(.*?)\}\}', frag)
        if not fields:
            continue
        if field_names is None:
            field_names = [f'field_{i}' for i in range(len(fields))]
        item = {fn: fv for fn, fv in zip(field_names, fields)}
        items.append(item)

    return items, field_names or ['content']


def _try_csv(content):
    """尝试 CSV 解析，返回 None 如果不像 CSV。"""
    lines = [l for l in content.splitlines() if l.strip()]
    if len(lines) < 2:
        return None

    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[:5]), delimiters=',\t;|')
        reader = csv.reader(io.StringIO(content), dialect)
        rows = list(reader)
        if len(rows) < 2:
            return None
        # 检查列数一致性
        col_counts = [len(r) for r in rows[:5]]
        if max(col_counts) - min(col_counts) > 1:
            return None
        headers = [h.strip() for h in rows[0]]
        items = []
        for row in rows[1:]:
            if not any(cell.strip() for cell in row):
                continue
            item = {}
            for i, h in enumerate(headers):
                item[h] = row[i].strip() if i < len(row) else ""
            items.append(item)
        return items, headers
    except (csv.Error, Exception):
        return None


def _parse_csv_auto(content):
    """CSV 自动解析。"""
    result = _try_csv(content)
    if result:
        return result
    # 回退
    items = [{"content": l.strip()} for l in content.splitlines() if l.strip()]
    return items, ["content"]


def _parse_json_auto(content):
    """JSON/JSONL 自动解析。"""
    items = []
    if content.startswith('['):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                items = data
        except json.JSONDecodeError:
            pass

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

    field_names = list(items[0].keys())
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


def _parse_tab_auto(content):
    """制表符自动解析。"""
    lines = [l for l in content.splitlines() if l.strip()]
    if not lines:
        return [], []

    # 跳过表头
    start = 0
    if not any('\u4e00' <= c <= '\u9fff' for c in lines[0]):
        start = 1

    items = []
    for line in lines[start:]:
        cols = line.split('\t')
        if len(cols) >= 3:
            items.append({"word": cols[0].strip(), "phonetic": cols[1].strip(), "meaning": cols[2].strip()})
        elif len(cols) == 2:
            items.append({"word": cols[0].strip(), "meaning": cols[1].strip()})

    if not items:
        return [], []

    fields = list(items[0].keys())
    return items, fields


def _parse_dash_auto(content):
    """破折号自动解析。"""
    items = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^(\S+)\s*[-–—]\s*(.+)$', line)
        if m:
            items.append({"word": m.group(1), "meaning": m.group(2).strip()})
    return items, ["word", "meaning"]


# ============================================================
# 批量处理
# ============================================================

def batch_process(file_paths, output_dir=None, field_names=None, fmt=None):
    """批量处理多个文件。

    Args:
        file_paths: 输入文件路径列表
        output_dir: 输出目录（None 则打印到 stdout）
        field_names: 字段名列表（None 则自动检测）
        fmt: 强制指定格式（None 则自动检测）

    Returns:
        dict {filename: (yida_str, item_count)}
    """
    results = {}

    for fp in file_paths:
        fname = os.path.basename(fp)
        print(f"\n{'='*40}", file=sys.stderr)
        print(f"📄 处理: {fname}", file=sys.stderr)

        try:
            content = read_input(fp)
        except SystemExit:
            print(f"⏭️  跳过（无法读取）: {fname}", file=sys.stderr)
            continue

        if not content.strip():
            print(f"⏭️  跳过（空文件）: {fname}", file=sys.stderr)
            continue

        # 解析
        items, detected_fields = auto_parse(content, hint=fmt)
        if not items:
            print(f"⏭️  跳过（无法解析）: {fname}", file=sys.stderr)
            continue

        # 去重
        items = dedup(items)

        # 字段名
        fn = field_names or detected_fields
        print_stats(items, {"字段": ", ".join(fn)})

        # 转换
        yida = to_yida(items, fn)
        ok, errs = validate(yida, expected_fields=len(fn))
        if not ok:
            print(f"⚠️  {fname}: 格式验证警告:", file=sys.stderr)
            for e in errs[:5]:  # 最多显示 5 个错误
                print(f"   {e}", file=sys.stderr)

        # 输出
        if output_dir:
            out_name = os.path.splitext(fname)[0] + "_忆哒格式.txt"
            out_path = os.path.join(output_dir, out_name)
            write_output(yida, out_path, preview_lines=2)
        else:
            write_output(yida, preview_lines=2)

        results[fname] = (yida, len(items))

    # 汇总
    total_items = sum(c for _, c in results.values())
    print(f"\n{'='*40}", file=sys.stderr)
    print(f"✅ 批量处理完成: {len(results)} 个文件, 共 {total_items} 条", file=sys.stderr)

    return results
