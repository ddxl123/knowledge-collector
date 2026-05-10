#!/usr/bin/env python3
"""独立验证 CLI — 验证忆哒格式文件的正确性

用法:
    python3 validate.py <input_file>                    # 自动检测字段数
    python3 validate.py <input_file> --fields 2         # 指定期望字段数
    python3 validate.py <input_file> --fields 3 --strict  # 严格模式（任何警告都报错）
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import read_input, validate

def main():
    import argparse
    ap = argparse.ArgumentParser(description="验证忆哒格式文件")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("--fields", type=int, help="每条知识点期望的字段数")
    ap.add_argument("--strict", action="store_true", help="严格模式（任何警告都视为错误）")
    ap.add_argument("--quiet", action="store_true", help="静默模式（只输出结果）")
    args = ap.parse_args()

    content = read_input(args.input)

    if not content.strip():
        if not args.quiet:
            print("⚠️  文件为空", file=sys.stderr)
        sys.exit(1)

    ok, errs = validate(content, expected_fields=args.fields)

    if not args.quiet:
        fragments = content.split("▮")
        total = len(fragments)
        print(f"📄 文件: {args.input}", file=sys.stderr)
        print(f"📊 总条数: {total}", file=sys.stderr)

        if args.fields:
            print(f"📋 期望字段数: {args.fields}", file=sys.stderr)

    if ok:
        if not args.quiet:
            print("✅ 验证通过！", file=sys.stderr)
        sys.exit(0)
    else:
        if not args.quiet:
            print(f"❌ 验证失败：{len(errs)} 个问题", file=sys.stderr)
            for e in errs:
                print(f"   • {e}", file=sys.stderr)
        sys.exit(1 if args.strict else 0)


if __name__ == "__main__":
    main()
