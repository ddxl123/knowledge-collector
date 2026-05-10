#!/usr/bin/env python3
"""验证 CLI (thin wrapper over kc.py)

等价于: kc.py validate <input> [--fields N] [--strict]
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    from kc import main
    sys.argv = [sys.argv[0], "validate"] + sys.argv[1:]
    sys.exit(main() or 0)
