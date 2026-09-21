# -*- coding: utf-8 -*-
"""交付前校验 —— 每次生成后都跑一遍。

用法：
    python validate_site.py <展示页.html> [--shots]

做六件事：
  1. 抽出最后一个 <script> 交给 `node --check`（JS 语法错会让页面全白，肉眼看不出来）
  2. 标签配对统计（漏闭合会导致后续布局整体错位）
  3. 占位符残留检查（__CARDS__ 之类没被替换掉）
  4. 错误转义检查（&lt;ol&gt; 之类，说明 inline() 把已生成的 HTML 又 escape 了一遍）
  5. 关键元素计数（卡片 / 模板 / 五问 / 原文按键 / 图示 / 内嵌图）
  6. --shots：无头 Chrome 截图（必须带 --force-prefers-reduced-motion，见 pitfalls.md）

外部依赖（找不到就跳过该项并给出提示，不会中断）：
  - Node.js  用于 JS 语法检查。可用环境变量 `NODE` 指定可执行文件路径。
  - Chrome / Edge / Chromium  仅 --shots 需要。可用环境变量 `CHROME` 指定。
  - 截图与临时 js 输出到 `CHECK_DIR`（默认：HTML 同级的 `_check/`）。
"""
import os, re, sys, glob, shutil, subprocess, urllib.parse

TAGS = ['div', 'section', 'article', 'aside', 'figure', 'figcaption', 'nav', 'button',
        'template', 'main', 'header', 'footer', 'h1', 'h2', 'h3', 'h4', 'p', 'span',
        'ul', 'ol', 'li', 'strong', 'b', 'em', 'code', 'table', 'thead', 'tbody',
        'tr', 'th', 'td', 'blockquote', 'pre', 'details', 'summary', 'a', 'img', 'br', 'hr']

PLACEHOLDERS = ['__CARDS__', '__TEMPLATES__', '__CHIPS__', '__QUICK__',
                '__TREND__', '__LAND__', '__ANCHOR__', '__JSDATA__']

# 可执行文件探测顺序：环境变量 → PATH → 各平台常见安装位置
NODE_ENV, NODE_NAMES = 'NODE', ['node']
CHROME_ENV = 'CHROME'
CHROME_NAMES = ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser',
                'chrome', 'msedge']
NODE_PATHS = [
    r'C:\Program Files\nodejs\node.exe',
    r'C:\Program Files (x86)\nodejs\node.exe',
    '/usr/local/bin/node', '/usr/bin/node', '/opt/homebrew/bin/node',
]
CHROME_PATHS = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
]


def find(env_key, names, extra_paths):
    """找一个可执行文件：环境变量 → PATH → 常见安装路径。"""
    c = os.environ.get(env_key)
    if c and os.path.exists(c):
        return c
    for n in names:
        w = shutil.which(n)
        if w:
            return w
    for c in extra_paths:
        if os.path.exists(c):
            return c
    return None

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 1
    path = args[0]
    shots = '--shots' in sys.argv
    base = os.path.basename(path).rsplit('.', 1)[0]
    outdir = os.environ.get('CHECK_DIR') or os.path.join(
        os.path.dirname(os.path.abspath(path)), '_check')
    os.makedirs(outdir, exist_ok=True)

    s = open(path, encoding='utf-8').read()
    fails, warns = [], []

    print('== 文件 ==')
    print('  %s  %.2f MB' % (path, len(s) / 1048576))

    # 1. JS 语法
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
    if not scripts:
        warns.append('页面里没有 <script>，确认是否是纯静态页')
    else:
        js = os.path.join(outdir, base + '.js')
        open(js, 'w', encoding='utf-8').write(scripts[-1])
        node = find(NODE_ENV, NODE_NAMES, NODE_PATHS)
        if not node:
            warns.append('未找到 node，跳过 JS 语法检查（装了 Node.js 或设 NODE 环境变量后会启用）')
            print('  JS 语法 跳过（无 node）')
        else:
            r = subprocess.run([node, '--check', js], capture_output=True, text=True)
            if r.returncode == 0:
                print('  JS 语法 OK (%d chars)' % len(scripts[-1]))
            else:
                fails.append('JS 语法错误：' + (r.stderr or '').strip()[:400])
                print('  JS 语法 FAIL')
                print(r.stderr[:600])

    # 2. 标签配对
    print('== 标签配对 ==')
    mis = 0
    for t in TAGS:
        if t in ('img', 'br', 'hr'):
            continue
        o = len(re.findall(r'<%s(?=[\s>])' % t, s))
        c = len(re.findall(r'</%s>' % t, s))
        if o != c:
            mis += 1
            fails.append('标签不配对 <%s> open=%d close=%d' % (t, o, c))
            print('  MISMATCH %-11s open=%-4d close=%-4d' % (t, o, c))
    if not mis:
        print('  全部闭合')

    # 3. 占位符残留
    left = [p for p in PLACEHOLDERS if p in s]
    if left:
        fails.append('占位符未替换：' + ', '.join(left))
    print('== 占位符 == %s' % ('残留 ' + ', '.join(left) if left else '无残留'))

    # 4. 错误转义
    esc = re.findall(r'&lt;(?:ol|ul|li|p|strong|code|em|br)&gt;', s)
    if esc:
        fails.append('被二次转义的标签 %d 处（inline() 把已生成 HTML 又 escape 了）' % len(esc))
    print('== 错误转义 == %d 处' % len(esc))

    # 5. 关键元素计数
    n_card = len(re.findall(r'<article class="card', s))
    n_tpl = s.count('<template')
    n_qa = len(re.findall(r'class="qa-i', s))
    n_tab = len(re.findall(r'class="srcbtn', s))
    n_fig = s.count('<figure class="dfig"')
    n_img = s.count('data:image/')
    print('== 计数 == 卡片 %d | 模板 %d | 五问 %d | 原文按键 %d | 图示 %d | 内嵌图 %d'
          % (n_card, n_tpl, n_qa, n_tab, n_fig, n_img))
    if n_tpl != n_card:
        fails.append('模板数(%d) ≠ 卡片数(%d)' % (n_tpl, n_card))
    if n_card and n_qa != n_card * 5:
        fails.append('五问块 %d ≠ 卡片数×5 = %d' % (n_qa, n_card * 5))
    if n_card and n_tab != n_card * 3:
        fails.append('原文按键 %d ≠ 卡片数×3 = %d' % (n_tab, n_card * 3))
    if n_fig != n_card:
        warns.append('图示 %d 张 ≠ 论文 %d 篇（缺图的篇目会用替代图或留空，确认是有意为之）'
                     % (n_fig, n_card))
    if 'cardIn' in s or 'animation-delay:calc(var(--i)' in s:
        fails.append('卡片还带着逐张延迟入场动画 —— 会让卡片延迟出现，必须删掉')

    print()
    if fails:
        print('FAIL (%d)' % len(fails))
        for f in fails:
            print('  × ' + f)
    else:
        print('静态校验 PASS')
    for w in warns:
        print('  ! ' + w)

    # 6. 截图
    if shots:
        chrome = find(CHROME_ENV, CHROME_NAMES, CHROME_PATHS)
        if not chrome:
            warns.append('未找到 Chrome/Edge，跳过截图（装了浏览器或设 CHROME 环境变量后会启用）')
            print('\n未找到 Chrome/Edge，跳过截图')
            for w in warns:
                print('  ! ' + w)
            return 1 if fails else 0
        url = 'file:///' + urllib.parse.quote(os.path.abspath(path).replace('\\', '/'))
        jobs = [('home', '', 1600, 1100), ('home_tall', '', 1600, 2400),
                ('p01', '#p01', 1600, 1200)]
        print('\n== 截图（%s）==' % os.path.basename(chrome))
        for name, frag, w, h in jobs:
            out = os.path.join(outdir, '%s_%s.png' % (base, name))
            subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                            '--force-prefers-reduced-motion',
                            '--window-size=%d,%d' % (w, h),
                            '--screenshot=' + os.path.abspath(out), url + frag],
                           capture_output=True)
            print('  ' + out + ('  (缺失)' if not os.path.exists(out) else ''))
        print('  逐张看图确认：封面是否出来 / 玻璃下面有没有真实纹理 / 图题有没有重复')

    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
