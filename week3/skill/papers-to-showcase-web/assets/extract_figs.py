# -*- coding: utf-8 -*-
"""从论文 PDF 中裁出 pipeline / framework 图并压缩，供 HTML 内嵌。**本文件不需要修改。**

用法：
    python extract_figs.py [project.py]      # 省略参数则读取同目录的 project.py

读 project.py 里的 FIG_TARGETS / PAPERS_DIR / FIGS_DIR。每篇产出三档图：

- `figNN_名称.png` 单篇页用的大图（3 倍 zoom 渲染后压成 256 色）
- `NN_名称_mid.jpg` 卡片封面（宽 ≤560px，q82）
- `NN_名称_bg.jpg` 卡片模糊底衬（宽 ≤56px，q45）

外加一张 `figcheck.png` 对照图 —— **必须人工看一眼**：自动裁切总有一两张要兜底
（判定标准：只含图、不含正文、不含图题）。字段含义与兜底方法见
`../references/pitfalls.md` 的「图示裁取」一节。"""
import os, sys, json, re, importlib.util
import pymupdf
from PIL import Image


def load_project(path=None):
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'project.py')
    if not os.path.isfile(path):
        sys.exit('找不到项目配置 %s\n请把 project.sample.py 复制为 project.py 并填写。' % path)
    spec = importlib.util.spec_from_file_location('showcase_project', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = load_project(sys.argv[1] if len(sys.argv) > 1 else None)
PDF_DIR = P.PAPERS_DIR
FIGS_DIR = P.FIGS_DIR
os.makedirs(FIGS_DIR, exist_ok=True)
TOL, MIN_H = 30, 80

TARGETS = P.FIG_TARGETS

# 先核对文件名（PDF 改名后 FIG_TARGETS 的 pdf 字段会静默失效，见 pitfalls.md #9）
_missing = [t['pdf'] for t in TARGETS
            if not os.path.isfile(os.path.join(PDF_DIR, t['pdf'] + '.pdf'))]
if _missing:
    sys.exit('这些 PDF 在 %s 下找不到，请核对 FIG_TARGETS 的 pdf 字段与磁盘文件名：\n  %s'
             % (PDF_DIR, '\n  '.join(_missing)))


def text_column(page):
    bl = [b for b in page.get_text('blocks') if b[4].strip()]
    if not bl:
        return 40, page.rect.width - 40
    xs0 = sorted(b[0] for b in bl)
    xs1 = sorted(b[2] for b in bl)
    return min(xs0), max(xs1)


def caption_text(page, label):
    """返回 (图题全文, 图题文本块 bbox)。"""
    for b in page.get_text('blocks'):
        t = re.sub(r'\s+', ' ', b[4]).strip()
        if t.startswith(label):
            t = re.sub(r'^(Figure\s*\d+)\s*[j|:.]\s*', r'\1: ', t)
            return t, b[:4]
    return '', None


def cluster_bbox(page, cap_y0):
    H = page.rect.height
    pool = []
    try:
        for info in page.get_image_info():
            r = pymupdf.Rect(info['bbox'])
            if r.height < 0.85 * H:
                pool.append(r)
    except Exception:
        pass
    try:
        for dr in page.get_drawings():
            r = dr.get('rect')
            if r and 1 < r.height < 0.85 * H and r.width > 1:
                pool.append(pymupdf.Rect(r))
    except Exception:
        pass
    pool = [r for r in pool if r.y1 <= cap_y0 + 2]
    if not pool:
        return None
    pool.sort(key=lambda r: -r.y1)
    y0, y1 = pool[0].y0, pool[0].y1
    rest, changed = pool[1:], True
    while changed:
        changed, keep = False, []
        for r in rest:
            if r.y1 >= y0 - TOL and r.y0 <= y1 + TOL:
                y0, y1, changed = min(y0, r.y0), max(y1, r.y1), True
            else:
                keep.append(r)
        rest = keep
    return y0, y1


results = []
for t in TARGETS:
    doc = pymupdf.open(os.path.join(PDF_DIR, t['pdf'] + '.pdf'))
    fpage = doc[t['fig_page'] - 1]
    cpage = doc[t['cap_page'] - 1]
    xs0, xs1 = text_column(fpage)

    cap, cap_bbox = caption_text(cpage, t['label'])
    if t.get('override'):
        y0, y1 = t['override']
        src = 'override'
    else:
        hits = []
        for cand in (t['prefix'], t['prefix'][:44], t['prefix'][:32], t['prefix'][:22], t['label']):
            if cand and (hits := cpage.search_for(cand)):
                break
        cap_y0 = min(r.y0 for r in hits) if hits else 200
        bb = cluster_bbox(fpage, cap_y0 + 40 if t['cap_page'] != t['fig_page'] else cap_y0)
        if bb and bb[1] - bb[0] >= MIN_H:
            y0, y1 = bb
            src = 'cluster'
        else:
            y0, y1 = (cap_y0 - 200, cap_y0 + 40)
            src = 'fallback'
    y0 = max(0, y0 - 8); y1 = min(fpage.rect.height, y1 + 8)
    # 图题已在 HTML 中单独渲染，故裁掉图片内的图题，避免重复
    if t['cap_page'] == t['fig_page'] and cap_bbox and cap_bbox[1] - 3 > y0 + MIN_H:
        y1 = min(y1, cap_bbox[1] - 3)
    clip = pymupdf.Rect(xs0 - 6, y0, xs1 + 6, y1)
    pix = fpage.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=clip, alpha=False)
    raw = os.path.join(FIGS_DIR, 'fig%02d_%s.png' % (t['n'], t['name']))
    pix.save(raw)

    im = Image.open(raw).convert('RGB')
    if im.width > 1900:
        im = im.resize((1900, round(im.height * 1900 / im.width)), Image.LANCZOS)
    q = im.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.NONE)
    q.save(raw, optimize=True, format='PNG')
    kb = os.path.getsize(raw) / 1024

    # 卡片封面用中图（清晰）+ 卡底衬用模糊小图
    base = os.path.join(FIGS_DIR, '%02d_%s' % (t['n'], t['name']))
    mid = im.copy()
    if mid.width > 560:
        mid = mid.resize((560, max(1, round(mid.height * 560 / mid.width))), Image.LANCZOS)
    mid_file = base + '_mid.jpg'
    mid.save(mid_file, quality=82, optimize=True, format='JPEG')
    th = im.copy()
    th.thumbnail((56, 400), Image.LANCZOS)
    th_file = base + '_bg.jpg'
    th.save(th_file, quality=45, optimize=True, format='JPEG')

    # manifest 里只存文件名，路径由 build_site.py 依 FIGS_DIR 解析 —— 便于整个目录搬移
    results.append(dict(n=t['n'], name=t['name'], file=os.path.basename(raw),
                        w=im.width, h=im.height, kb=round(kb), src=src,
                        mid=os.path.basename(mid_file), midkb=round(os.path.getsize(mid_file) / 1024),
                        bg=os.path.basename(th_file), bgkb=round(os.path.getsize(th_file) / 1024),
                        label=t['label'], page=t['fig_page'], caption=cap,
                        substitute=bool(t.get('substitute')),
                        note=t.get('note', '')))
    print('%02d %-17s %-8s %4dx%-5d %6.1f KB | 封面 %4.1f KB 底衬 %.1f KB | cap=%d字 %s' % (
        t['n'], t['name'], src, im.width, im.height, kb,
        os.path.getsize(mid_file) / 1024, os.path.getsize(th_file) / 1024, len(cap),
        t.get('note', '')))
    doc.close()

json.dump(results, open(os.path.join(FIGS_DIR, 'manifest.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\ntotal %.1f KB' % sum(r['kb'] for r in results))

# 对照图
sheet = pymupdf.open()
COLS, ROWS, CW, CH = 2, 5, 660, 430
pg = sheet.new_page(width=COLS * CW + 30, height=ROWS * CH + 30)
for i, r in enumerate(results):
    rr, cc = divmod(i, COLS)
    x, y = 10 + cc * CW, 10 + rr * CH
    pg.insert_text((x + 4, y + 16), '%02d  %s' % (r['n'], r['name']), fontsize=13)
    s = min((CW - 24) / r['w'], (CH - 40) / r['h'])
    pg.insert_image(pymupdf.Rect(x + 4, y + 24, x + 4 + r['w'] * s, y + 24 + r['h'] * s),
                    filename=os.path.join(FIGS_DIR, r['file']))
sheet[0].get_pixmap(matrix=pymupdf.Matrix(1.35, 1.35)).save(
    os.path.join(FIGS_DIR, 'figcheck.png'))
print('check sheet -> %s' % os.path.join(FIGS_DIR, 'figcheck.png'))
