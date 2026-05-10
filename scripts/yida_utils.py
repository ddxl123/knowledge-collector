#!/usr/bin/env python3
"""忆哒格式核心工具模块

职责：格式转换、验证、I/O、清洗、去重、合并、自动解析。
所有解析逻辑集中在此模块（单一事实来源），standalone parse 脚本和 kc.py 均依赖本模块。

用法:
    from yida_utils import to_yida, validate, write_output, read_input
    from yida_utils import dedup, clean_field, merge, auto_parse, batch_process
    from yida_utils import retry_fetch, progress_bar
"""

import sys
import re
import os
import json
import csv
import io
import codecs
import time
import urllib.request
import urllib.error


# ============================================================
# 忆哒格式 — 转换 / 验证
# ============================================================

def to_yida(items, field_names=None):
    """items → 忆哒格式字符串。

    Args:
        items: list of dict
        field_names: 字段名列表。None 则用第一个 dict 的 key 顺序。

    Returns:
        "{{v1}}{{v2}}▮{{v1}}{{v2}}" 格式字符串
    """
    if not items:
        return ""
    if field_names is None:
        field_names = list(items[0].keys())
    fragments = []
    for item in items:
        fields = []
        for fn in field_names:
            val = clean_field(str(item.get(fn, "")).strip())
            fields.append(f"{{{{{val}}}}}")
        fragments.append("".join(fields))
    return "▮".join(fragments)


def validate(yida_str, expected_fields=None):
    """验证忆哒格式字符串。

    Returns:
        (is_valid, errors) 元组
    """
    errors = []
    if not yida_str:
        return True, []

    fragments = yida_str.split("▮")
    if expected_fields is None:
        expected_fields = fragments[0].count("{{")

    for i, frag in enumerate(fragments):
        open_count = frag.count("{{")
        close_count = frag.count("}}")
        if open_count != close_count:
            errors.append(f"#{i+1}: 括号不匹配 ({{ {open_count}, }} {close_count})")
            continue
        if open_count != expected_fields:
            errors.append(f"#{i+1}: 期望 {expected_fields} 字段, 实际 {open_count}")
        field_values = re.findall(r'\{\{(.*?)\}\}', frag)
        for j, val in enumerate(field_values):
            if not val.strip():
                errors.append(f"#{i+1} 字段{j+1}: 空值")
            for ch in ('{{', '}}', '▮'):
                if ch in val:
                    errors.append(f"#{i+1} 字段{j+1}: 非法字符 '{ch}'")
    return len(errors) == 0, errors


# ============================================================
# I/O — 读写 / 编码检测
# ============================================================

def _detect_encoding(path, sample_size=8192):
    """检测文件编码: BOM → UTF-8 → GBK → GB18030 → fallback UTF-8。"""
    with open(path, 'rb') as f:
        raw = f.read(sample_size)
    if raw.startswith(codecs.BOM_UTF8):
        return 'utf-8-sig'
    if raw.startswith(codecs.BOM_UTF16_LE):
        return 'utf-16-le'
    if raw.startswith(codecs.BOM_UTF16_BE):
        return 'utf-16-be'
    for enc in ('utf-8', 'gbk', 'gb18030'):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    return 'utf-8'


def read_input(path=None):
    """读取文件（自动编码检测）或 stdin。"""
    if path and os.path.isfile(path):
        enc = _detect_encoding(path)
        with open(path, encoding=enc) as f:
            content = f.read()
        if enc != 'utf-8':
            print(f"📝 编码: {enc}", file=sys.stderr)
        return content
    elif path:
        print(f"❌ 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    return sys.stdin.read()


def write_output(content, path=None, preview_lines=5):
    """写入文件 + 打印预览。返回写入路径或 None。"""
    if path:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"💾 已保存: {path}", file=sys.stderr)
    fragments = content.split("▮")
    total = len(fragments)
    preview = "▮".join(fragments[:preview_lines])
    if total > preview_lines:
        print(f"📊 共 {total} 条，预览前 {preview_lines}:", file=sys.stderr)
    print(preview)
    return path


def print_stats(items, extra=None):
    """打印解析统计。"""
    print(f"📊 解析 {len(items)} 条", file=sys.stderr)
    if extra:
        for k, v in extra.items():
            print(f"   {k}: {v}", file=sys.stderr)


# ============================================================
# 网络 — 带重试的 URL 获取
# ============================================================

def retry_fetch(url, retries=3, timeout=30, delay=2):
    """带重试和 UA 的 URL 获取。

    Returns:
        str: 响应文本内容
    Raises:
        urllib.error.URLError: 重试耗尽后抛出
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; KnowledgeCollector/1.0)"}
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            if attempt < retries - 1:
                wait = delay * (attempt + 1)
                print(f"⚠️  获取失败 (第{attempt+1}次), {wait}s 后重试: {e}", file=sys.stderr)
                time.sleep(wait)
    raise last_err


def progress_bar(current, total, width=30, prefix=""):
    """打印进度条到 stderr。"""
    if total == 0:
        return
    pct = current / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\r{prefix}[{bar}] {current}/{total} ({pct:.0%})", end="", file=sys.stderr)
    if current == total:
        print(file=sys.stderr)


# ============================================================
# 数据清洗 / 去重 / 合并
# ============================================================

def clean_field(value):
    """清洗字段值：移除保留字符，合并空白。"""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace('{{', '').replace('}}', '').replace('▮', '')
    return re.sub(r'\s+', ' ', value).strip()


def dedup(items, key_fields=None, case_insensitive=True):
    """按指定字段去重。返回去重后的 list。"""
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
    if removed:
        print(f"🔄 去重: {len(items)} → {len(result)} (-{removed})", file=sys.stderr)
    return result


def merge(*item_lists):
    """合并多个 items 列表并去重。"""
    all_items = []
    for items in item_lists:
        if items:
            all_items.extend(items)
    return dedup(all_items) if all_items else []


# ============================================================
# 自动格式检测 — 单一事实来源
# ============================================================

def auto_parse(content, hint=None):
    """自动检测格式并解析为 items 列表。

    Args:
        content: 原始文本
        hint: 格式提示 (csv/json/tab/dash/markdown/numbered/indent/auto)

    Returns:
        (items, field_names) 元组
    """
    content = content.strip()
    if not content:
        return [], []

    # 标准化 hint
    if hint and hint.startswith('parse_'):
        hint = hint[6:]

    # hint 快速路由
    _hint_map = {
        'csv': _parse_csv, 'json': _parse_json, 'tab': _parse_tab,
        'dash': _parse_dash, 'markdown': _parse_markdown_table,
        'numbered': _parse_numbered, 'indent': _parse_indent,
    }
    if hint and hint in _hint_map:
        return _hint_map[hint](content)

    # 自动检测（按可信度排序）
    # 1. 忆哒格式（已有数据）
    if '▮' in content and '{{' in content:
        return _parse_yida(content)

    # 2. JSON
    if content[0] in ('[', '{'):
        return _parse_json(content)

    # 3. Markdown 表格
    if re.search(r'\|.*\|', content) and re.search(r'\|[\s\-:]+\|', content):
        return _parse_markdown_table(content)

    lines = [l for l in content.splitlines() if l.strip()]

    # 4. 制表符（优先于 CSV，避免 tab 被误判为 CSV 分隔符）
    if lines and '\t' in lines[0]:
        return _parse_tab(content)

    # 5. CSV
    csv_result = _try_csv(content)
    if csv_result:
        return csv_result

    # 6. 破折号
    if re.search(r'\S+\s*[-–—]\s+\S+', content):
        return _parse_dash(content)

    # 7. 缩进层级
    if lines and any(l[0] in (' ', '\t') for l in lines if l):
        return _parse_indent(content)

    # 8. 编号列表
    if re.search(r'^\d+[.)\s]', content, re.MULTILINE):
        return _parse_numbered(content)

    # 9. 兜底：按行
    items = [{"content": l.strip()} for l in lines if l.strip()]
    return items, ["content"]


# ============================================================
# 内部解析器（自动检测用，不对外暴露）
# ============================================================

def _parse_yida(content):
    """解析已有忆哒格式 → items。"""
    items, field_names = [], None
    for frag in content.split('▮'):
        if not frag.strip():
            continue
        fields = re.findall(r'\{\{(.*?)\}\}', frag)
        if not fields:
            continue
        if field_names is None:
            # 尝试从内容推断字段名
            n = len(fields)
            if n == 2:
                # 2字段: 可能是 word+meaning 或 question+answer
                if any('\u4e00' <= c <= '\u9fff' for c in fields[1]):
                    field_names = ['word', 'meaning']
                else:
                    field_names = ['field_0', 'field_1']
            elif n == 3:
                field_names = ['word', 'phonetic', 'meaning']
            else:
                field_names = [f'field_{i}' for i in range(n)]
        items.append(dict(zip(field_names, fields)))
    return items, field_names or ['content']


def _try_csv(content):
    """尝试 CSV 解析，不像则返回 None。"""
    lines = [l for l in content.splitlines() if l.strip()]
    if len(lines) < 2:
        return None
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[:5]), delimiters=',\t;|')
        reader = csv.reader(io.StringIO(content), dialect)
    except csv.Error:
        # sniffer 失败时，尝试逗号作为兜底分隔符
        comma_counts = [l.count(',') for l in lines[:5]]
        if len(set(comma_counts)) == 1 and comma_counts[0] >= 1:
            reader = csv.reader(io.StringIO(content), delimiter=',')
        else:
            return None
    try:
        rows = list(reader)
        if len(rows) < 2:
            return None
        col_counts = [len(r) for r in rows[:5]]
        if max(col_counts) - min(col_counts) > 1:
            return None
        headers = [h.strip() for h in rows[0]]
        items = []
        for row in rows[1:]:
            if not any(cell.strip() for cell in row):
                continue
            items.append({h: (row[i].strip() if i < len(row) else "") for i, h in enumerate(headers)})
        return items, headers
    except Exception:
        return None


def _parse_csv(content):
    """CSV 解析。"""
    result = _try_csv(content)
    if result:
        return result
    items = [{"content": l.strip()} for l in content.splitlines() if l.strip()]
    return items, ["content"]


def _parse_json(content):
    """JSON/JSONL 解析。"""
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


def _parse_tab(content):
    """制表符解析：2列=word+meaning，3列=word+phonetic+meaning。"""
    lines = [l for l in content.splitlines() if l.strip()]
    if not lines:
        return [], []
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
    return items, (["word", "phonetic", "meaning"] if items and "phonetic" in items[0] else ["word", "meaning"])


def _parse_dash(content):
    """破折号解析：word - meaning。"""
    items = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^(\S+)\s*[-–—]\s*(.+)$', line)
        if m:
            items.append({"word": m.group(1), "meaning": m.group(2).strip()})
    return items, ["word", "meaning"]


def _parse_markdown_table(content):
    """Markdown 表格解析。"""
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    if len(lines) < 3:
        return [], []
    headers = [h.strip() for h in lines[0].strip('|').split('|')]
    items = []
    for line in lines[2:]:
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.strip('|').split('|')]
        items.append({h: (cols[i] if i < len(cols) else "") for i, h in enumerate(headers)})
    return items, headers


def _parse_numbered(content):
    """编号列表解析。智能拆分 word/meaning。"""
    separators = [r'\s+[-–—:]\s+', r'\s{2,}', r'\t',
                  r'(?<=\w)\s+(?=[a-zA-Z\u4e00-\u9fff])']
    items = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\d+[.)\s]+(.+)$', line)
        if not m:
            continue
        rest = m.group(1).strip()
        word, meaning = rest, ""
        for sep in separators:
            parts = re.split(sep, rest, maxsplit=1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                word, meaning = parts[0].strip(), parts[1].strip()
                break
        items.append({"word": word, "meaning": meaning})
    return items, ["word", "meaning"]


def _parse_indent(content):
    """缩进层级解析。"""
    items, current = [], None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line[0] in (' ', '\t'):
            if current:
                current["details"] += (" " + stripped if current["details"] else stripped)
            continue
        if current:
            items.append(current)
        current = {"key": stripped, "details": ""}
    if current:
        items.append(current)
    return items, ["key", "details"]


# ============================================================
# 批量处理
# ============================================================

def batch_process(file_paths, output_dir=None, field_names=None, fmt=None):
    """批量处理多个文件。

    Returns:
        dict {filename: (yida_str, item_count)}
    """
    results = {}
    total = len(file_paths)
    for idx, fp in enumerate(file_paths, 1):
        fname = os.path.basename(fp)
        progress_bar(idx, total, prefix=f"📄 {fname[:20]:20s} ")
        try:
            content = read_input(fp)
        except SystemExit:
            print(f"⏭️  跳过(无法读取): {fname}", file=sys.stderr)
            continue
        if not content.strip():
            print(f"⏭️  跳过(空): {fname}", file=sys.stderr)
            continue
        items, detected_fields = auto_parse(content, hint=fmt)
        if not items:
            print(f"⏭️  跳过(无数据): {fname}", file=sys.stderr)
            continue
        items = dedup(items)
        fn = field_names or detected_fields
        print_stats(items, {"字段": ", ".join(fn)})
        yida = to_yida(items, fn)
        ok, errs = validate(yida, expected_fields=len(fn))
        if not ok:
            print(f"⚠️  {fname}: {len(errs)} 个警告", file=sys.stderr)
            for e in errs[:3]:
                print(f"   {e}", file=sys.stderr)
        if output_dir:
            out_name = os.path.splitext(fname)[0] + "_忆哒格式.txt"
            out_path = os.path.join(output_dir, out_name)
            write_output(yida, out_path, preview_lines=2)
        else:
            write_output(yida, preview_lines=2)
        results[fname] = (yida, len(items))
    total_items = sum(c for _, c in results.values())
    print(f"\n{'='*40}", file=sys.stderr)
    print(f"✅ 完成: {len(results)}/{total} 文件, 共 {total_items} 条", file=sys.stderr)
    return results


# ============================================================
# 字段转换（kc.py convert 用）
# ============================================================

def convert_fields(items, field_map):
    """重命名/筛选字段。

    Args:
        items: list of dict
        field_map: dict {old_name: new_name} 或 list of names (保留并保持原名)

    Returns:
        list of dict（已重命名）
    """
    if isinstance(field_map, list):
        field_map = {n: n for n in field_map}
    result = []
    for item in items:
        new_item = {}
        for old, new in field_map.items():
            new_item[new] = item.get(old, "")
        result.append(new_item)
    return result


def filter_items(items, filter_expr):
    """按条件过滤 items。

    Args:
        items: list of dict
        filter_expr: "field=value" 或 "field~=regex" 或 "field!=value"

    Returns:
        filtered list of dict
    """
    if not filter_expr:
        return items

    # 解析表达式
    m = re.match(r'^(\w+)(~=|!=|=)(.+)$', filter_expr)
    if not m:
        print(f"⚠️  无效过滤表达式: {filter_expr}", file=sys.stderr)
        return items

    field, op, value = m.group(1), m.group(2), m.group(3)
    result = []
    for item in items:
        val = str(item.get(field, ""))
        if op == '=' and val == value:
            result.append(item)
        elif op == '!=' and val != value:
            result.append(item)
        elif op == '~=' and re.search(value, val):
            result.append(item)
    print(f"🔍 过滤: {len(items)} → {len(result)} ({filter_expr})", file=sys.stderr)
    return result
