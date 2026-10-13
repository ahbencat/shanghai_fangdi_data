#!/usr/bin/env python3
"""构建 GitHub Pages 静态站点（纯标准库，可在 GitHub runner 上直接运行）。

流程：
1. 解析 ROOT/monthly/*.md 的「二手房/一手房每日明细」表格
2. 把数据 JSON 嵌入 pages/index.template.html 的 /*__DATA__*/ 占位符
3. 输出 ROOT/site/index.html（自包含单文件，不进 git 历史）

由 .github/workflows/pages.yml 在每次 push 后调用。
用法：python3 pages/build.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / 'pages'
MONTHLY_DIR = ROOT / 'monthly'
SITE_DIR = ROOT / 'site'

# 表格行：| 2026-10-01 | 153 | 12,319.44 |
ROW_RE = re.compile(r'^\| (\d{4}-\d{2}-\d{2}) \| ([\d,]+) \| ([\d,.]+) \|$')


def parse_num(s):
    s = s.replace(',', '')
    return float(s) if '.' in s else int(s)


def parse_monthly():
    """扫描全部月度 MD，按日期聚合两个市场的每日数据。"""
    days = {}
    for path in sorted(MONTHLY_DIR.glob('*.md')):
        market = None
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('## '):
                if '二手房每日明细' in line:
                    market = 'ershou'
                elif '一手房每日明细' in line:
                    market = 'yishou'
                else:
                    market = None
                continue
            m = ROW_RE.match(line)
            if m and market:
                date, count, area = m.group(1), m.group(2), m.group(3)
                entry = days.setdefault(date, {})
                if market == 'ershou':
                    entry['count'] = parse_num(count)
                    entry['area'] = parse_num(area)
                else:
                    entry['newCount'] = parse_num(count)
                    entry['newArea'] = parse_num(area)
    return days


def main():
    days = parse_monthly()
    template_path = PAGES_DIR / 'index.template.html'
    template = template_path.read_text(encoding='utf-8')
    n = template.count('/*__DATA__*/')
    if n != 1:
        raise SystemExit(f'{template_path} 中 /*__DATA__*/ 占位符应恰好 1 处，实际 {n} 处')

    payload = json.dumps({'days': days}, ensure_ascii=False, separators=(',', ':'))
    html = template.replace('/*__DATA__*/', payload, 1)

    SITE_DIR.mkdir(exist_ok=True)
    out = SITE_DIR / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'生成 {out.relative_to(ROOT)}（{len(days)} 天数据）')


if __name__ == '__main__':
    main()
