#!/usr/bin/env python3
"""knowledge-collector 统一 CLI 入口

用法:
    kc parse <file> [--format FORMAT] [--fields a,b,c] [-o out.txt]
    kc validate <file> [--fields N] [--strict]
    kc batch <dir|files...> [-o out_dir] [--format FORMAT] [--fields a,b,c]
    kc fetch <source> [-o out.txt]
    kc stats <file>
    kc clean <file> [-o out.txt]

支持的格式: auto, csv, json, tab, dash, markdown, numbered, indent
支持的数据源: cet4, gaokao-history, gaokao-geography, cet6, ielts
"""

import sys
import os
import argparse

# 确保能 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yida_utils import (
    read_input, write_output, to_yida, validate, auto_parse,
    dedup, clean_field, print_stats, batch_process
)


# ============================================================
# 格式 → 解析函数映射
# ============================================================

FORMAT_MAP = {
    'auto': None,
    'csv': 'parse_csv',
    'json': 'parse_json',
    'tab': 'parse_tab',
    'dash': 'parse_dash',
    'markdown': 'parse_markdown',
    'numbered': 'parse_numbered',
    'indent': 'parse_indent',
}

# 可在线获取的数据源
FETCH_SOURCES = {
    'cet4': ('parse_cet4', 'CET-4 高频词汇'),
    'cet6': ('parse_cet4', 'CET-6 词汇'),  # 共用解析器
    'gaokao-history': ('parse_gaokao_history', '高考历史真题'),
    'gaokao-geography': ('parse_gaokao_history', '高考地理真题'),  # 共用解析器
    'ielts': ('parse_cet4', 'IELTS 词汇'),  # 共用解析器
}


def parse_with_format(content, fmt=None, field_names=None, has_header=True):
    """根据指定格式解析内容。

    Returns:
        (items, field_names) 元组
    """
    if fmt and fmt != 'auto':
        # 动态导入对应解析模块
        module_name = FORMAT_MAP.get(fmt)
        if module_name:
            module = __import__(module_name)
            if hasattr(module, 'parse'):
                import inspect
                sig = inspect.signature(module.parse)
                params = list(sig.parameters.keys())

                kwargs = {}
                if 'field_names' in params:
                    kwargs['field_names'] = field_names
                if 'has_header' in params:
                    kwargs['has_header'] = has_header

                result = module.parse(content, **kwargs)

                # 解析模块返回值可能是 (items, fields) 或 items
                if isinstance(result, tuple):
                    return result
                return result, field_names or ["content"]

    # 自动检测
    return auto_parse(content, hint=fmt if fmt != 'auto' else None)


# ============================================================
# 子命令: parse
# ============================================================

def cmd_parse(args):
    """解析文件并转换为忆哒格式。"""
    content = read_input(args.input)

    if not content.strip():
        print("❌ 文件为空", file=sys.stderr)
        return 1

    field_names = args.fields.split(",") if args.fields else None
    has_header = not args.no_header

    items, detected_fields = parse_with_format(
        content, fmt=args.format, field_names=field_names, has_header=has_header
    )

    if not items:
        print("❌ 无法解析出数据", file=sys.stderr)
        return 1

    fn = field_names or detected_fields

    # 去重
    if not args.no_dedup:
        items = dedup(items, key_fields=fn[:1] if len(fn) > 1 else None)

    print_stats(items, {"字段": ", ".join(fn)})

    yida = to_yida(items, fn)
    ok, errs = validate(yida, expected_fields=len(fn))

    if not ok:
        print(f"⚠️  格式验证: {len(errs)} 个警告", file=sys.stderr)
        for e in errs[:5]:
            print(f"   {e}", file=sys.stderr)

    write_output(yida, args.output)
    return 0


# ============================================================
# 子命令: validate
# ============================================================

def cmd_validate(args):
    """验证忆哒格式文件。"""
    content = read_input(args.input)

    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    ok, errs = validate(content, expected_fields=args.fields)

    fragments = content.split("▮")
    total = len(fragments)
    print(f"📄 文件: {args.input}", file=sys.stderr)
    print(f"📊 总条数: {total}", file=sys.stderr)

    if args.fields:
        print(f"📋 期望字段数: {args.fields}", file=sys.stderr)

    if ok:
        print("✅ 验证通过！", file=sys.stderr)
        return 0
    else:
        print(f"❌ 验证失败：{len(errs)} 个问题", file=sys.stderr)
        for e in errs:
            print(f"   • {e}", file=sys.stderr)
        return 1 if args.strict else 0


# ============================================================
# 子命令: batch
# ============================================================

def cmd_batch(args):
    """批量处理多个文件。"""
    import glob as globmod

    SUPPORTED_EXTS = {'.txt', '.csv', '.json', '.jsonl', '.md', '.tsv', '.dat'}

    files = []
    for p in args.inputs:
        if os.path.isdir(p):
            for ext in SUPPORTED_EXTS:
                files.extend(globmod.glob(os.path.join(p, f'*{ext}')))
        elif os.path.isfile(p):
            files.append(p)
        else:
            matched = globmod.glob(p)
            files.extend([f for f in matched if os.path.isfile(f)])

    files = sorted(set(files))
    if not files:
        print("❌ 未找到可处理的文件", file=sys.stderr)
        return 1

    print(f"📁 找到 {len(files)} 个文件待处理", file=sys.stderr)

    if args.output:
        os.makedirs(args.output, exist_ok=True)

    field_names = args.fields.split(",") if args.fields else None

    results = batch_process(
        files, output_dir=args.output, field_names=field_names, fmt=args.format
    )

    success = len(results)
    total_items = sum(c for _, c in results.values())
    print(f"\n{'='*40}")
    print(f"✅ 完成: {success}/{len(files)} 个文件成功, 共 {total_items} 条知识点")
    return 0


# ============================================================
# 子命令: fetch
# ============================================================

def cmd_fetch(args):
    """在线获取预置数据源。"""
    source = args.source.lower()

    if source not in FETCH_SOURCES:
        print(f"❌ 未知数据源: {source}", file=sys.stderr)
        print(f"可用数据源: {', '.join(FETCH_SOURCES.keys())}", file=sys.stderr)
        return 1

    module_name, desc = FETCH_SOURCES[source]
    print(f"🌐 正在获取: {desc}", file=sys.stderr)

    module = __import__(module_name)

    if hasattr(module, 'fetch_content'):
        content = module.fetch_content()
        items = module.parse(content)
        items = dedup(items)

        # 确定字段名
        if items:
            fn = list(items[0].keys())
        else:
            fn = ["content"]

        print_stats(items)
        yida = to_yida(items, fn)
        write_output(yida, args.output)
        return 0
    else:
        print(f"❌ 模块 {module_name} 不支持在线获取", file=sys.stderr)
        return 1


# ============================================================
# 子命令: stats
# ============================================================

def cmd_stats(args):
    """显示文件统计信息。"""
    content = read_input(args.input)

    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    fragments = content.split("▮")
    total = len(fragments)

    # 检测字段数
    first = fragments[0]
    field_count = first.count("{{")

    # 验证
    ok, errs = validate(content)

    print(f"📄 文件: {args.input}")
    print(f"📊 总条数: {total}")
    print(f"📋 字段数: {field_count}")
    print(f"📏 文件大小: {len(content):,} 字节")
    print(f"✅ 格式: {'有效' if ok else f'有 {len(errs)} 个问题'}")

    # 抽样预览
    print(f"\n📝 前 3 条预览:")
    for i, frag in enumerate(fragments[:3]):
        import re
        fields = re.findall(r'\{\{(.*?)\}\}', frag)
        print(f"  #{i+1}: {' | '.join(fields)}")

    return 0


# ============================================================
# 子命令: clean
# ============================================================

def cmd_clean(args):
    """清洗忆哒格式文件（修复常见问题）。"""
    import re

    content = read_input(args.input)

    if not content.strip():
        print("⚠️  文件为空", file=sys.stderr)
        return 1

    fragments = content.split("▮")
    cleaned = []
    fixes = 0

    for frag in fragments:
        if not frag.strip():
            fixes += 1
            continue

        # 清洗每个字段值
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

        cleaned_frag = "".join(f"{{{{{f}}}}}" for f in new_fields)
        cleaned.append(cleaned_frag)

    result = "▮".join(cleaned)
    print(f"🔧 修复了 {fixes} 个问题", file=sys.stderr)

    # 验证结果
    ok, errs = validate(result)
    if ok:
        print("✅ 清洗后格式验证通过", file=sys.stderr)
    else:
        print(f"⚠️  仍有 {len(errs)} 个问题", file=sys.stderr)

    write_output(result, args.output)
    return 0


# ============================================================
# 主入口
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        prog='kc',
        description='📚 knowledge-collector 统一 CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  kc parse data.txt --format tab -o out.txt
  kc validate out.txt --fields 2
  kc batch ./raw_data/ -o ./output/
  kc fetch cet4 -o cet4.txt
  kc stats out.txt
  kc clean broken.txt -o fixed.txt
        """
    )
    sub = ap.add_subparsers(dest='command', help='子命令')

    # parse
    p_parse = sub.add_parser('parse', help='解析文件为忆哒格式')
    p_parse.add_argument('input', help='输入文件路径')
    p_parse.add_argument('--format', '-f', choices=list(FORMAT_MAP.keys()),
                         default='auto', help='输入格式（默认自动检测）')
    p_parse.add_argument('--fields', help='字段名，逗号分隔')
    p_parse.add_argument('--no-header', action='store_true', help='无表头行')
    p_parse.add_argument('--no-dedup', action='store_true', help='不去重')
    p_parse.add_argument('--output', '-o', help='输出文件路径')

    # validate
    p_val = sub.add_parser('validate', help='验证忆哒格式文件')
    p_val.add_argument('input', help='输入文件路径')
    p_val.add_argument('--fields', type=int, help='期望字段数')
    p_val.add_argument('--strict', action='store_true', help='严格模式')

    # batch
    p_batch = sub.add_parser('batch', help='批量处理文件')
    p_batch.add_argument('inputs', nargs='+', help='输入文件或目录')
    p_batch.add_argument('--output', '-o', help='输出目录')
    p_batch.add_argument('--format', '-f', choices=list(FORMAT_MAP.keys()),
                         default='auto', help='输入格式')
    p_batch.add_argument('--fields', help='字段名，逗号分隔')

    # fetch
    p_fetch = sub.add_parser('fetch', help='在线获取预置数据源')
    p_fetch.add_argument('source', help=f'数据源名称: {", ".join(FETCH_SOURCES.keys())}')
    p_fetch.add_argument('--output', '-o', help='输出文件路径')

    # stats
    p_stats = sub.add_parser('stats', help='显示文件统计信息')
    p_stats.add_argument('input', help='输入文件路径')

    # clean
    p_clean = sub.add_parser('clean', help='清洗忆哒格式文件')
    p_clean.add_argument('input', help='输入文件路径')
    p_clean.add_argument('--output', '-o', help='输出文件路径')

    args = ap.parse_args()

    if not args.command:
        ap.print_help()
        return 0

    cmd_map = {
        'parse': cmd_parse,
        'validate': cmd_validate,
        'batch': cmd_batch,
        'fetch': cmd_fetch,
        'stats': cmd_stats,
        'clean': cmd_clean,
    }

    return cmd_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
