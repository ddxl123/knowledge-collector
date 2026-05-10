#!/usr/bin/env python3
"""批量处理 CLI — 自动检测格式并批量转换为忆哒格式

用法:
    python3 batch.py ./raw_data/ -o ./output/           # 处理目录下所有文件
    python3 batch.py file1.txt file2.csv -o ./output/   # 处理指定文件
    python3 batch.py ./data/ --format tab -o ./out/     # 强制指定格式
    python3 batch.py ./data/ --fields word,meaning      # 指定字段名
"""

import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import batch_process

SUPPORTED_EXTS = {'.txt', '.csv', '.json', '.jsonl', '.md', '.tsv', '.dat'}

def collect_files(paths):
    """从路径列表中收集所有待处理的文件。"""
    files = []
    for p in paths:
        if os.path.isdir(p):
            for ext in SUPPORTED_EXTS:
                files.extend(glob.glob(os.path.join(p, f'*{ext}')))
        elif os.path.isfile(p):
            files.append(p)
        else:
            # 尝试 glob 模式
            matched = glob.glob(p)
            files.extend([f for f in matched if os.path.isfile(f)])
    return sorted(set(files))

def main():
    import argparse
    ap = argparse.ArgumentParser(description="批量处理为忆哒格式")
    ap.add_argument("inputs", nargs="+", help="输入文件或目录路径")
    ap.add_argument("-o", "--output", help="输出目录")
    ap.add_argument("--format", choices=['csv', 'json', 'tab', 'dash', 'markdown', 'numbered', 'indent'],
                    help="强制指定输入格式（默认自动检测）")
    ap.add_argument("--fields", help="字段名，逗号分隔（如 word,meaning）")
    args = ap.parse_args()

    files = collect_files(args.inputs)
    if not files:
        print("❌ 未找到可处理的文件", file=sys.stderr)
        sys.exit(1)

    print(f"📁 找到 {len(files)} 个文件待处理", file=sys.stderr)

    if args.output:
        os.makedirs(args.output, exist_ok=True)

    field_names = args.fields.split(",") if args.fields else None

    results = batch_process(files, output_dir=args.output, field_names=field_names, fmt=args.format)

    # 汇总
    success = len(results)
    total_items = sum(c for _, c in results.values())
    print(f"\n{'='*40}")
    print(f"✅ 完成: {success}/{len(files)} 个文件成功, 共 {total_items} 条知识点")


if __name__ == "__main__":
    main()
