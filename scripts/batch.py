#!/usr/bin/env python3
"""批量处理 CLI (thin wrapper over kc.py)

等价于: kc.py batch <inputs> -o <output> [--format FORMAT] [--fields FIELDS]
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    # 直接转发给 kc.py
    from kc import main
    sys.argv = [sys.argv[0], "batch"] + sys.argv[1:]
    sys.exit(main() or 0)
