#!/usr/bin/env python3
"""knowledge-collector 统一 CLI

用法:
    kc parse <file> [--format FORMAT] [--fields a,b,c] [-o out.txt]
    kc validate <file> [--fields N] [--strict]
    kc batch <dir|files...> [-o out_dir] [--format FORMAT] [--fields a,b,c]
    kc fetch <source> [-o out.txt]
    kc stats <file>
    kc clean <file> [-o out.txt]
    kc convert <file> --map old1:new1,old2:new2 [-o out.txt]
    kc merge <files...> [-o out.txt] [--fields a,b,c]
    kc preview <file> [--limit N]
"""

import sys
import os
import argparse
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yida_utils import (
    read_input, write_output, to_yida, validate, auto_parse,
    dedup, clean_field, print_stats, batch_process, retry_fetch,
    convert_fields, filter_items, merge,
)


# ============================================================
# 格式映射
# ============================================================

FORMAT_MAP = {
    'auto': None, 'csv': None, 'json': None, 'tab': None,
    'dash': None, 'markdown': None, 'numbered': None, 'indent': None,
}

# 可在线获取的数据源
FETCH_SOURCES = {
    'cet4': {
        'url': 'https://cdn.jsdelivr.net/gh/KyleBing/english-vocabulary@master/3%20%E5%9B%9B%E7%BA%A7-%E4%B9%B1%E5%BA%8F.txt',
        'desc': 'CET-4 高频词汇',
        'parser': 'tab',
    },
    'cet6': {
        'url': 'https://cdn.jsdelivr.net/gh/KyleBing/english-vocabulary@master/4%20%E5%85%AD%E7%BA%A7-%E4%B9%B1%E5%BA%8F.txt',
        'desc': 'CET-6 词汇',
        'parser': 'tab',
    },
    'ielts': {
        'url': 'https://cdn.jsdelivr.net/gh/KyleBing/english-vocabulary@master/5%20%E9%9B%85%E6%80%9D%E6%A0%B8%E5%BF%83%E8%AF%8D%E6%B1%87.txt',
        'desc': 'IELTS 核心词汇',
        'parser': 'tab',
    },
    'gaokao-history': {
        'url': 'https://cdn.jsdelivr.net/gh/ruixiangcui/AGIEval@main/data/v1/gaokao-history.jsonl',
        'desc': '高考历史真题',
        'parser': 'json',
    },
    'gaokao-geography': {
        'url': 'https://cdn.jsdelivr.net/gh/ruixiangcui/AGIEval@main/data/v1/gaokao-geography.jsonl',
        'desc': '高考地理真题',
        'parser': 'json',
    },
}


# ============================================================
# 子命令实现
# ============================================================

def cmd_parse(args):
    """解析文件并转换为忆哒格式。"""
    content = read_input(args.input)
    if not content.strip():
        print("❌ 文件为空", file=sys.stderr)
        return 1

    field_names = args.fields.split(",") if args.fields else None
    has_header = not args.no_header

    # 调用自动解析（hint 传入格式）
    items, detected_fields = auto_parse(content, hint=args.format)

    if not items:
        print("❌ 无法解析出数据", file=sys.stderr)
        return 1

    fn = field_names or detected_fields

    # 字段重映射
    if args.map:
        mapping = dict(p.split(':', 1) for p in args.map.split(','))
        items = convert_fields(items, mapping)
        fn = list(mapping.values())

    # 过滤
    if args.filter:
        items = filter_items(items, args.filter)

    # 去重
    if not args.no_dedup:
        items = dedup(items, key_fields=fn[:1] if len(fn) > 1 else None)

    print_stats(items, {"字段": ", ".join(fn)})

    yida = to_yida(items, fn)
    ok, errs = validate(yida, expected_fields=len(fn))

    if not ok:
        print(f"⚠️  {len(errs)} 个警告", file=sys.stderr)
        for e in errs[:5]:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
    return 0


def cmd_validate(args):
    """验证忆哒格式文件。"""
    content = read_input(args.input)
    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    ok, errs = validate(content, expected_fields=args.fields)
    fragments = content.split("▮")
    total = len(fragments)

    print(f"📄 {args.input}", file=sys.stderr)
    print(f"📊 {total} 条", file=sys.stderr)
    if args.fields:
        print(f"📋 期望字段: {args.fields}", file=sys.stderr)

    if ok:
        print("✅ 验证通过", file=sys.stderr)
        return 0
    else:
        print(f"❌ {len(errs)} 个问题", file=sys.stderr)
        for e in errs:
            print(f"   • {e}", file=sys.stderr)
        return 1 if args.strict else 0


def cmd_batch(args):
    """批量处理多个文件。"""
    import glob as globmod
    EXTS = {'.txt', '.csv', '.json', '.jsonl', '.md', '.tsv', '.dat'}

    files = []
    for p in args.inputs:
        if os.path.isdir(p):
            for ext in EXTS:
                files.extend(globmod.glob(os.path.join(p, f'*{ext}')))
        elif os.path.isfile(p):
            files.append(p)
        else:
            files.extend([f for f in globmod.glob(p) if os.path.isfile(f)])

    files = sorted(set(files))
    if not files:
        print("❌ 未找到文件", file=sys.stderr)
        return 1

    print(f"📁 {len(files)} 个文件", file=sys.stderr)
    if args.output:
        os.makedirs(args.output, exist_ok=True)

    field_names = args.fields.split(",") if args.fields else None
    results = batch_process(files, output_dir=args.output, field_names=field_names, fmt=args.format)

    total_items = sum(c for _, c in results.values())
    print(f"\n{'='*40}")
    print(f"✅ {len(results)}/{len(files)} 成功, 共 {total_items} 条")
    return 0


def cmd_fetch(args):
    """在线获取预置数据源。"""
    source = args.source.lower()
    if source not in FETCH_SOURCES:
        print(f"❌ 未知数据源: {source}", file=sys.stderr)
        print(f"可用: {', '.join(FETCH_SOURCES.keys())}", file=sys.stderr)
        return 1

    info = FETCH_SOURCES[source]
    print(f"🌐 获取: {info['desc']}", file=sys.stderr)

    try:
        content = retry_fetch(info['url'])
    except Exception as e:
        print(f"❌ 获取失败: {e}", file=sys.stderr)
        return 1

    items, field_names = auto_parse(content, hint=info['parser'])

    # 特殊处理 JSONL 格式的高考题
    if info['parser'] == 'json' and source.startswith('gaokao'):
        import json
        items = []
        for i, line in enumerate(content.strip().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            question = obj.get("question", "")
            options = obj.get("options", [])
            label = obj.get("label", "")
            src = obj.get("other", {}).get("source", info['desc'])
            options_text = "\n".join(options)
            year_match = re.search(r'(\d{4})', src)
            tags = ["高考", "历史" if "历史" in source else "地理", "选择题"]
            if year_match:
                tags.append(year_match.group(1))
            full_content = f"{question}\n\n{options_text}\n\n答案：({label})"
            items.append({"title": f"#{i}", "content": full_content, "tags": ",".join(tags), "source": src})
        field_names = ["title", "content", "tags", "source"]

    if not items:
        print("❌ 未解析到数据", file=sys.stderr)
        return 1

    items = dedup(items)
    fn = field_names or list(items[0].keys())
    print_stats(items, {"字段": ", ".join(fn)})

    yida = to_yida(items, fn)
    write_output(yida, args.output)
    return 0


def cmd_stats(args):
    """显示文件统计信息。"""
    content = read_input(args.input)
    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    fragments = content.split("▮")
    total = len(fragments)
    field_count = fragments[0].count("{{")
    ok, errs = validate(content)

    print(f"📄 {args.input}")
    print(f"📊 {total} 条")
    print(f"📋 {field_count} 字段/条")
    print(f"📏 {len(content):,} 字节")
    print(f"✅ {'有效' if ok else f'{len(errs)} 个问题'}")

    print(f"\n📝 前 3 条:")
    for i, frag in enumerate(fragments[:3]):
        fields = re.findall(r'\{\{(.*?)\}\}', frag)
        print(f"  #{i+1}: {' | '.join(fields)}")
    return 0


def cmd_clean(args):
    """清洗忆哒格式文件。"""
    content = read_input(args.input)
    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    fragments = content.split("▮")
    cleaned, fixes = [], 0

    for frag in fragments:
        if not frag.strip():
            fixes += 1
            continue
        fields = re.findall(r'\{\{(.*?)\}\}', frag)
        if not fields:
            fixes += 1
            continue
        new_fields = []
        for val in fields:
            new_val = clean_field(val)
            if new_val != val:
                fixes += 1
            new_fields.append(new_val)
        cleaned.append("".join(f"{{{{{f}}}}}" for f in new_fields))

    result = "▮".join(cleaned)
    print(f"🔧 修复 {fixes} 处", file=sys.stderr)

    ok, errs = validate(result)
    print(f"{'✅ 验证通过' if ok else f'⚠️  {len(errs)} 个问题'}", file=sys.stderr)

    write_output(result, args.output)
    return 0


def cmd_convert(args):
    """转换字段名/筛选字段。"""
    content = read_input(args.input)
    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    items, field_names = auto_parse(content)
    if not items:
        print("❌ 无法解析", file=sys.stderr)
        return 1

    # 字段映射
    mapping = dict(p.split(':', 1) for p in args.map.split(','))
    items = convert_fields(items, mapping)
    fn = list(mapping.values())

    # 过滤
    if args.filter:
        items = filter_items(items, args.filter)

    items = dedup(items)
    print_stats(items, {"字段": ", ".join(fn)})

    yida = to_yida(items, fn)
    write_output(yida, args.output)
    return 0


def cmd_merge(args):
    """合并多个文件。"""
    all_items = []
    all_fields = None

    for fp in args.inputs:
        content = read_input(fp)
        if not content.strip():
            continue
        items, fields = auto_parse(content)
        if items:
            if all_fields is None:
                all_fields = args.fields.split(",") if args.fields else fields
            all_items.extend(items)
            print(f"📄 {os.path.basename(fp)}: {len(items)} 条", file=sys.stderr)

    if not all_items:
        print("❌ 无数据", file=sys.stderr)
        return 1

    fn = all_fields or list(all_items[0].keys())
    all_items = dedup(all_items)
    print_stats(all_items, {"字段": ", ".join(fn)})

    yida = to_yida(all_items, fn)
    write_output(yida, args.output)
    return 0


def cmd_preview(args):
    """预览文件内容（不保存）。支持原始数据和忆哒格式。"""
    content = read_input(args.input)
    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    limit = args.limit or 10

    # 已是忆哒格式
    if '▮' in content and '{{' in content:
        fragments = content.split("▮")
        print(f"📊 共 {len(fragments)} 条，显示前 {min(limit, len(fragments))} 条:\n")
        for i, frag in enumerate(fragments[:limit]):
            fields = re.findall(r'\{\{(.*?)\}\}', frag)
            print(f"  #{i+1}: {' | '.join(fields)}")
        if len(fragments) > limit:
            print(f"\n  ... 还有 {len(fragments) - limit} 条")
        return 0

    # 原始数据 → 自动解析后预览
    items, field_names = auto_parse(content)
    if not items:
        print("❌ 无法解析", file=sys.stderr)
        return 1

    print(f"📊 共 {len(items)} 条（字段: {', '.join(field_names)}），显示前 {min(limit, len(items))} 条:\n")
    for i, item in enumerate(items[:limit]):
        vals = [str(item.get(fn, '')) for fn in field_names]
        print(f"  #{i+1}: {' | '.join(vals)}")
    if len(items) > limit:
        print(f"\n  ... 还有 {len(items) - limit} 条")
    return 0


# ============================================================
# 主入口
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        prog='kc',
        description='📚 knowledge-collector CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest='command')

    # parse
    p = sub.add_parser('parse', help='解析文件为忆哒格式')
    p.add_argument('input', help='输入文件')
    p.add_argument('--format', '-f', choices=list(FORMAT_MAP.keys()), default='auto')
    p.add_argument('--fields', help='字段名,逗号分隔')
    p.add_argument('--map', help='字段映射 old:new,old2:new2')
    p.add_argument('--filter', help='过滤条件 field=value / field~=regex / field!=value')
    p.add_argument('--no-header', action='store_true')
    p.add_argument('--no-dedup', action='store_true')
    p.add_argument('--output', '-o')

    # validate
    p = sub.add_parser('validate', help='验证忆哒格式')
    p.add_argument('input')
    p.add_argument('--fields', type=int)
    p.add_argument('--strict', action='store_true')

    # batch
    p = sub.add_parser('batch', help='批量处理')
    p.add_argument('inputs', nargs='+')
    p.add_argument('--output', '-o')
    p.add_argument('--format', '-f', choices=list(FORMAT_MAP.keys()), default='auto')
    p.add_argument('--fields')

    # fetch
    p = sub.add_parser('fetch', help='在线获取数据源')
    p.add_argument('source', help=f'数据源: {", ".join(FETCH_SOURCES.keys())}')
    p.add_argument('--output', '-o')

    # stats
    p = sub.add_parser('stats', help='统计信息')
    p.add_argument('input')

    # clean
    p = sub.add_parser('clean', help='清洗文件')
    p.add_argument('input')
    p.add_argument('--output', '-o')

    # convert (NEW)
    p = sub.add_parser('convert', help='转换/筛选字段')
    p.add_argument('input')
    p.add_argument('--map', required=True, help='字段映射 old:new,old2:new2')
    p.add_argument('--filter', help='过滤条件')
    p.add_argument('--output', '-o')

    # merge (NEW)
    p = sub.add_parser('merge', help='合并多个文件')
    p.add_argument('inputs', nargs='+')
    p.add_argument('--fields', help='字段名,逗号分隔')
    p.add_argument('--output', '-o')

    # preview (NEW)
    p = sub.add_parser('preview', help='预览文件')
    p.add_argument('input')
    p.add_argument('--limit', '-n', type=int, default=10)

    args = ap.parse_args()
    if not args.command:
        ap.print_help()
        return 0

    cmd_map = {
        'parse': cmd_parse, 'validate': cmd_validate, 'batch': cmd_batch,
        'fetch': cmd_fetch, 'stats': cmd_stats, 'clean': cmd_clean,
        'convert': cmd_convert, 'merge': cmd_merge, 'preview': cmd_preview,
    }
    return cmd_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
