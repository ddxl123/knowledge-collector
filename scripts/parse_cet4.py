#!/usr/bin/env python3
"""CET-4/6/IETLS 词汇 → 忆哒格式 (thin wrapper)

数据源: KyleBing/english-vocabulary (GitHub)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from yida_utils import (
    read_input, write_output, to_yida, validate, auto_parse,
    dedup, print_stats, retry_fetch,
)

CDN_URLS = {
    'cet4': "https://cdn.jsdelivr.net/gh/KyleBing/english-vocabulary@master/3%20%E5%9B%9B%E7%BA%A7-%E4%B9%B1%E5%BA%8F.txt",
    'cet6': "https://cdn.jsdelivr.net/gh/KyleBing/english-vocabulary@master/4%20%E5%85%AD%E7%BA%A7-%E4%B9%B1%E5%BA%8F.txt",
    'ielts': "https://cdn.jsdelivr.net/gh/KyleBing/english-vocabulary@master/5%20%E9%9B%85%E6%80%9D%E6%A0%B8%E5%BF%83%E8%AF%8D%E6%B1%87.txt",
}

DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "raw_data", "cet4_high_freq.txt")

def fetch_content(url=None):
    url = url or CDN_URLS['cet4']
    return retry_fetch(url)

def parse(content):
    items, _ = auto_parse(content, hint='tab')
    return items

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="本地文件（不提供则在线获取）")
    ap.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    ap.add_argument("--source", default="cet4", choices=list(CDN_URLS.keys()))
    args = ap.parse_args()

    if args.input:
        content = read_input(args.input)
    else:
        content = fetch_content(CDN_URLS[args.source])

    items = parse(content)
    items = dedup(items)
    print_stats(items)
    yida = to_yida(items, ["word", "meaning"])
    write_output(yida, args.output)
