# -*- coding: utf-8 -*-
"""论文展示站生成器 —— 通用版，**本文件不需要修改**。

用法：
    python build_site.py [project.py]      # 省略参数则读取同目录的 project.py

项目相关的一切（路径、标题文案、路线配色、论文清单、五问答案）都写在 project.py 里，
本文件只负责渲染。CSS / JS / 组件结构是本 skill 的交付外观，**请勿改动**。

- 项目配置模板：`project.sample.py`（复制为 project.py 后按注释填写）
- 设计规范：`../references/design-system.md`
- 踩坑记录：`../references/pitfalls.md`

产出两份文件：合并版 Markdown（OUT_MD）+ 单文件展示网页（OUT_HTML，
图示以 base64 内嵌，不依赖外部资源）。
"""
import re, html, json, base64, os, sys, importlib.util


def load_project(path=None):
    """从指定路径加载 project.py（用文件路径加载，不污染 sys.path）。"""
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'project.py')
    if not os.path.isfile(path):
        sys.exit('找不到项目配置 %s\n请把 project.sample.py 复制为 project.py 并填写。' % path)
    spec = importlib.util.spec_from_file_location('showcase_project', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = load_project(sys.argv[1] if len(sys.argv) > 1 else None)

A_PATH, B_PATH = P.SUMMARY_MD, P.TRANSLATION_MD
OUT_MD, OUT_HTML = P.OUT_MD, P.OUT_HTML
QA, Q_TITLES = P.QA, P.Q_TITLES
S = P.MD_SECTIONS

for _f, _label in ((A_PATH, 'SUMMARY_MD（源笔记 A：要点解读 + 速查表）'),
                   (B_PATH, 'TRANSLATION_MD（源笔记 B：三段译文）')):
    if not os.path.isfile(_f):
        sys.exit('找不到 %s：%s\n请检查 project.py 里的路径配置。' % (_label, _f))

A = open(A_PATH, encoding='utf-8').read()
B = open(B_PATH, encoding='utf-8').read()


def headings(text):
    return [(len(m.group(1)), m.group(2).strip(), m.start(), m.end())
            for m in re.finditer(r'^(#{1,6}) (.+)$', text, re.M)]


def block(text, starts, level):
    hs = headings(text)
    for i, (lv, t, s, e) in enumerate(hs):
        if lv == level and t.startswith(starts):
            end = len(text)
            for lv2, t2, s2, e2 in hs[i + 1:]:
                if lv2 <= level:
                    end = s2
                    break
            return text[e:end].strip()
    return ''


SRC = P.SOURCE_SECTIONS          # 源笔记的二级标题前缀，结构约定见 references/content-contract.md
a_intro = block(A, SRC['intro'], 2)
a_table = block(A, SRC['table'], 2)
a_detail = block(A, SRC['detail'], 2)
a_trend = block(A, SRC['trend'], 2)
a_land = block(A, SRC['land'], 2)
a_anchor = block(A, SRC['anchor'], 2)

a_papers = {}
for it in re.split(r'^### ', a_detail, flags=re.M)[1:]:
    lines = it.split('\n')
    num = int(re.match(r'(\d+)', lines[0].strip()).group(1))
    a_papers[num] = '\n'.join(lines[1:]).strip()


def parse_table(md):
    rows = []
    for line in md.split('\n'):
        line = line.strip()
        if line.startswith('|') and not re.match(r'^\|[\s\-:|]+\|$', line):
            rows.append([c.strip() for c in line.strip('|').split('|')])
    return rows


quick = {}
for r in parse_table(a_table)[1:]:
    if r and r[0].isdigit():
        quick[int(r[0])] = r

b_papers, b_index_md = {}, ''
for p in re.split(r'^## ', B, flags=re.M)[1:]:
    if p.startswith(SRC['b_index']):
        b_index_md = p.strip()
        continue
    lines = p.split('\n')
    m = re.match(r'(\d+)\.', lines[0].strip())
    if not m:
        continue
    num = int(m.group(1))
    body = '\n'.join(lines[1:])

    def sub(name):
        mm = re.search(r'^### %s\s*\n(.*?)(?=\n### |\Z)' % name, body, re.M | re.S)
        return mm.group(1).strip() if mm else ''

    arxiv = re.search(r'`(arXiv:[^`]+)`（([^）]+)）', body)
    cn = re.search(r'\*\*中文标题\*\*：(.+)', body)
    b_papers[num] = dict(
        head=lines[0].strip(), arxiv=arxiv.group(1) if arxiv else '',
        date=arxiv.group(2) if arxiv else '', cn=cn.group(1).strip() if cn else '',
        abstract=sub('摘要'), intro=sub('引言'), conclusion=sub('结论'))

META = P.PAPERS_META            # {编号: (路线名, 落位序位, 是否★优先)}
SHORT = P.SHORT                 # {编号: 卡片短名}
ROUTES = P.ROUTES               # [(路线名, CSS 类后缀, 颜色)]
ROUTE_KEY = {name: key for name, key, _c in ROUTES}
order = sorted(quick.keys())

def _resolve_fig(p):
    """manifest 里的图片路径可能是绝对路径、项目相对路径或纯文件名，统一解析。"""
    if not p:
        return p
    if os.path.isabs(p) and os.path.exists(p):
        return p
    for cand in (os.path.join(P.FIGS_DIR, p),
                 os.path.join(P.FIGS_DIR, os.path.basename(p)), p):
        if os.path.exists(cand):
            return cand
    return os.path.join(P.FIGS_DIR, os.path.basename(p))


FIG = {}
_manifest = os.path.join(P.FIGS_DIR, 'manifest.json')
if os.path.exists(_manifest):
    for _r in json.load(open(_manifest, encoding='utf-8')):
        for _k in ('file', 'mid', 'bg'):
            if _r.get(_k):
                _r[_k] = _resolve_fig(_r[_k])
        FIG[_r['n']] = _r

_URICACHE = {}


def fig_uris(n):
    """返回 (全尺寸 PNG, 封面中图 JPEG, 底衬小图 JPEG) 三个 data URI。"""
    if n not in _URICACHE:
        r = FIG.get(n)

        def u(key, mime):
            p = r.get(key) if r else None
            if p and os.path.exists(p):
                return 'data:%s;base64,%s' % (
                    mime, base64.b64encode(open(p, 'rb').read()).decode('ascii'))
            return ''
        _URICACHE[n] = (u('file', 'image/png'), u('mid', 'image/jpeg'), u('bg', 'image/jpeg'))
    return _URICACHE[n]


def clean_cn(cn):
    s = cn.split('：', 1)[1] if '：' in cn else cn
    return re.sub(r'（[A-Za-z][^（）]*）\s*$', '', s).strip() or cn


def en_of(bp):
    t = bp.get('head', '').split('. ', 1)[-1]
    return t.split('——')[0].strip() or t.strip()


def paper_link(bp):
    """根据源笔记里的 arXiv 编号生成可点击的论文链接（指向 arXiv 摘要页）。"""
    a = bp.get('arxiv', '')
    m = re.match(r'arXiv:([^\s`]+)', a)
    if not m:
        return ''
    url = 'https://arxiv.org/abs/' + m.group(1)
    return ('<a class="plink" href="%s" target="_blank" rel="noopener">'
            '论文链接 ↗</a>' % html.escape(url, quote=True))


# ================= 合并 markdown =================
L = P.MD_LABELS
md = (['# ' + P.MD_TITLE, ''] + list(P.MD_HEADER_LINES)
      + ['', '---', '', '## ' + S['intro'], '', a_intro, '', '---', '',
         '## ' + S['table'], '', a_table, '', '---', '', '## ' + S['papers'], ''])

for n in order:
    bp = b_papers.get(n, {})
    route, prio, star = META.get(n, ('', 0, False))
    q = quick.get(n, ['', '', '', '', ''])
    md += ['### %d. %s —— %s' % (n, SHORT.get(n, en_of(bp)), clean_cn(bp.get('cn', ''))), '',
           '- **%s**：%s' % (L['en_title'], bp.get('head', '').split('. ', 1)[-1]),
           '- **%s**：%s' % (L['cn_title'], bp.get('cn', '')),
           '- **%s**：`%s`（%s）' % (L['source'], bp.get('arxiv', ''), bp.get('date', '')),
           '- **%s**：%s' % (L['route'], route),
           '- **%s**：%s' % (L['method'], q[3]), '- **%s**：%s' % (L['numbers'], q[4])]
    if star:
        md.append('- **%s**：%s' % (L['star'], P.STAR_NOTE))
    elif prio:
        md.append('- **%s**：%s' % (L['priority'], P.PRIORITY_FMT % prio))
    md += ['', '#### 五问解读', '']
    for i, (t, a) in enumerate(zip(Q_TITLES, QA.get(n, [''] * 5)), 1):
        md += ['**%d. %s**' % (i, t), '', a, '']
    for label, key in (('摘要', 'abstract'), ('引言', 'intro'), ('结论', 'conclusion')):
        md += ['#### %s（译文）' % label, '', bp.get(key, '（缺）'), '']

md += ['---', '', '## ' + S['trend'], '', a_trend, '', '---', '',
       '## ' + S['land'], '', a_land, '', '---', '',
       '## ' + S['anchor'], '', a_anchor, '', '---', '',
       '## ' + S['index'], '', b_index_md, '']
open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(md))
print('merged md:', OUT_MD)


# ================= Markdown → HTML =================
def inline(s):
    s = html.escape(s.replace('<br>', '\n'), quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


LIST_RE = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.*)$')


def parse_list(lines, i, base_indent):
    m = LIST_RE.match(lines[i])
    ordered = bool(re.match(r'\d+\.', m.group(2)))
    items = []
    while i < len(lines):
        m = LIST_RE.match(lines[i])
        if not m or len(m.group(1)) != base_indent:
            break
        content = m.group(3); i += 1
        while i < len(lines) and lines[i].strip() and not LIST_RE.match(lines[i]) \
                and len(lines[i]) - len(lines[i].lstrip()) > base_indent:
            content += ' ' + lines[i].strip(); i += 1
        sub = ''
        if i < len(lines):
            m2 = LIST_RE.match(lines[i])
            if m2 and len(m2.group(1)) > base_indent:
                sub, i = parse_list(lines, i, len(m2.group(1)))
        items.append(inline(content) + sub)
    tag = 'ol' if ordered else 'ul'
    return '<%s>%s</%s>' % (tag, ''.join('<li>%s</li>' % x for x in items), tag), i


def render_table(rows):
    cells = [[c.strip() for c in r.strip('|').split('|')]
             for r in rows if not re.match(r'^\|[\s\-:|]+\|$', r)]
    if not cells:
        return ''
    h = '<div class="tw"><table><thead><tr>' + ''.join(
        '<th>' + inline(c) + '</th>' for c in cells[0]) + '</tr></thead><tbody>'
    for r in cells[1:]:
        h += '<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in r) + '</tr>'
    return h + '</tbody></table></div>'


def render_blocks(mdtext):
    lines = mdtext.split('\n')
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
            para.clear()

    while i < len(lines):
        st = lines[i].strip()
        if not st:
            flush(); i += 1; continue
        if st in ('---', '***', '___'):
            flush(); out.append('<hr>'); i += 1; continue
        if st.startswith('```'):
            flush(); code = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i]); i += 1
            i += 1
            out.append('<pre>' + html.escape('\n'.join(code)) + '</pre>')
            continue
        if st.startswith('> '):
            flush(); q = []
            while i < len(lines) and lines[i].strip().startswith('> '):
                q.append(lines[i].strip()[2:]); i += 1
            out.append('<blockquote>' + inline(' '.join(q)) + '</blockquote>')
            continue
        m = LIST_RE.match(lines[i])
        if m:
            flush(); blk, i = parse_list(lines, i, len(m.group(1))); out.append(blk)
            continue
        if st.startswith('|'):
            flush(); rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip()); i += 1
            out.append(render_table(rows))
            continue
        para.append(st); i += 1
    flush()
    return '\n'.join(out)


def fig_html(n):
    r = FIG.get(n)
    if not r or not os.path.exists(r['file']):
        return ''
    b64 = base64.b64encode(open(r['file'], 'rb').read()).decode('ascii')
    label = r.get('label', '')
    cap = r.get('caption', '')
    body = cap[len(label):].lstrip(':：') if cap.startswith(label) else cap
    note = ('<p class="fignote">说明：%s</p>' % html.escape(r['note'], quote=False)
            ) if r.get('note') else ''
    return ('<figure class="dfig">'
            '<img src="data:image/png;base64,%s" alt="%s %s 图示" loading="lazy">'
            '<figcaption><b>%s</b>%s</figcaption>%s</figure>' % (
                b64, html.escape(label), html.escape(SHORT.get(n, ''), quote=True),
                html.escape(label), html.escape(body, quote=False), note))


def qa_html(n):
    ans = QA.get(n, [''] * 5)
    items = []
    for i, (t, a) in enumerate(zip(Q_TITLES, ans), 1):
        cls = 'qa-i opp' if i == 5 else 'qa-i'
        items.append('<div class="%s"><h4><b>%d</b>%s</h4><p>%s</p></div>'
                     % (cls, i, html.escape(t, quote=False), inline(a)))
    return '<div class="qa">%s</div>' % ''.join(items)


# ================= 生成 HTML =================
cards, templates = [], []
for n in order:
    bp = b_papers.get(n, {})
    route, prio, star = META.get(n, ('', 0, False))
    rk = ROUTE_KEY.get(route) or ROUTES[0][1]
    q = quick.get(n, ['', '', '', '', ''])
    short = SHORT.get(n, en_of(bp))
    cn = clean_cn(bp.get('cn', ''))
    qn = '%02d' % n

    _full, _mid, _bg = fig_uris(n)
    cover = ''
    if _mid:
        cover = ('<div class="bg" style="background-image:url(%s)"></div>'
                 '<div class="plate"><span class="shot" style="background-image:url(%s)"></span></div>'
                 % (_bg or _mid, _mid))

    cards.append(
        '<article class="card r-%s" data-n="%d" tabindex="0" role="button"'
        ' aria-label="打开第 %d 篇 %s">'
        '%s'
        '<div class="glass">'
        '<div class="c-top"><span class="c-num">%s</span>'
        '<span class="c-route">%s</span>%s</div>'
        '<h3 class="c-en">%s</h3>'
        '<p class="c-cn">%s</p>'
        '<p class="c-key"><span class="c-kl">方法</span>%s</p>'
        '<div class="c-foot"><span class="c-num2">%s</span>'
        '<span class="c-go">阅读 →</span></div>'
        '</div></article>' % (
            rk, n, n, html.escape(short, quote=True), cover, qn, route,
            '<span class="c-star">★</span>' if star else '',
            inline(short), inline(cn), inline(q[3]), inline(bp.get('arxiv', ''))))

    templates.append(
        '<template id="t-%d">'
        '<header class="dh">'
        '<div class="dh-num" aria-hidden="true">%s</div>'
        '<div class="dh-t">'
        '<span class="dh-route r-%s">%s</span>%s'
        '<h2>%s</h2><p class="dh-cn">%s</p>'
        '<div class="dh-meta"><span class="mono">%s</span>%s<span>%s</span>%s</div>'
        '</div></header>'
        '%s'
        '<section class="qasec"><h3 class="sech"><span>五问解读</span><em>Five Questions</em></h3>%s</section>'
        '<section class="srcsec">'
        '<h3 class="sech"><span>原文</span><em>Source Text</em></h3>'
        '<div class="srcwrap">'
        '<nav class="srcnav" aria-label="原文段落切换">'
        '<button class="srcbtn on" type="button" data-tab="abstract">摘要</button>'
        '<button class="srcbtn" type="button" data-tab="intro">引言</button>'
        '<button class="srcbtn" type="button" data-tab="conclusion">结论</button>'
        '</nav>'
        '<div class="srcbody">'
        '<article class="srcpane on" data-pane="abstract">%s</article>'
        '<article class="srcpane" data-pane="intro">%s</article>'
        '<article class="srcpane" data-pane="conclusion">%s</article>'
        '</div></div></section>'
        '</template>' % (
            n, qn, rk, route,
            '<span class="dh-star">★ %s</span>' % P.STAR_BADGE if star else '',
            inline(short), inline(cn),
            inline(bp.get('arxiv', '')), paper_link(bp), inline(bp.get('date', '')),
            ('<span class="dh-prio">%s</span>' % (P.PRIORITY_BADGE % prio))
            if prio and not star else '',
            fig_html(n),
            qa_html(n),
            render_blocks(bp.get('abstract', '')),
            render_blocks(bp.get('intro', '')),
            render_blocks(bp.get('conclusion', ''))))

page = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__HTML_TITLE__</title>
<style>
  :root{
    --ink:#14181F; --ink2:#3B4453; --ink3:#6B7484; --ink4:#9AA1AC;
    --paper:#F7F8FA; --line:rgba(20,24,31,.10); --line2:rgba(20,24,31,.16);
__ROOT_VARS__
    --serif:"Songti SC","Source Han Serif SC","Noto Serif SC",Georgia,"Times New Roman",serif;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    --mono:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
    font-size:15px;line-height:1.75;-webkit-font-smoothing:antialiased}
  body::before{content:"";position:fixed;inset:0;z-index:-1;
    background:
      radial-gradient(820px 560px at 10% -8%,rgba(42,90,140,.13),transparent 62%),
      radial-gradient(680px 500px at 94% 4%,rgba(138,90,31,.10),transparent 60%),
      radial-gradient(760px 600px at 62% 106%,rgba(31,122,107,.10),transparent 62%),
      linear-gradient(180deg,#FAFBFC 0%,#F3F5F8 100%)}
  .wrap{max-width:1180px;margin:0 auto;padding:0 28px}
__ROUTE_RULES__

  /* ---------- 主页 ---------- */
  .hero{padding:40px 0 20px;text-align:center}
  .hero h1{font-family:var(--serif);font-size:28px;font-weight:400;letter-spacing:.01em;
    line-height:1.3;margin:0 0 10px}
  .hero .lede{font-size:13.5px;color:var(--ink3);margin:0 auto;max-width:62ch}
  h2.sec{font-family:var(--serif);font-size:19px;font-weight:400;margin:28px 0 14px;
    display:flex;align-items:baseline;gap:12px}
  h2.sec em{font-family:var(--mono);font-style:normal;font-size:11px;letter-spacing:.14em;
    text-transform:uppercase;color:var(--ink4)}
  h2.sec::after{content:"";flex:1;height:1px;background:var(--line)}

  .flow{display:flex;flex-direction:column;gap:7px;padding:17px 20px;border-radius:14px;
    border:1px solid rgba(255,255,255,.86);
    background:linear-gradient(180deg,rgba(255,255,255,.80),rgba(255,255,255,.58));
    -webkit-backdrop-filter:blur(16px) saturate(170%);backdrop-filter:blur(16px) saturate(170%);
    box-shadow:0 1px 2px rgba(20,24,31,.05),0 14px 30px -24px rgba(20,24,31,.3),
      inset 0 1px 0 rgba(255,255,255,.9)}
  .frow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  .ftag{flex:none;width:182px;text-align:right;font-size:11.5px;color:var(--ink3)}
  .fnode{font-size:12.5px;font-weight:500;border-radius:8px;padding:5px 12px;
    border:1px solid var(--line2);background:rgba(255,255,255,.7)}
  .fnode.done{color:var(--ink3);background:rgba(20,24,31,.04)}
  .fnote{font-size:12px;color:var(--ink2)}
  .flowcite{margin:12px 0 0;padding:10px 14px;border-radius:0 8px 8px 0;
    border-left:3px solid #A9741F;background:rgba(169,116,31,.07);
    font-size:12px;color:var(--ink2)}

  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));
    gap:22px;padding-bottom:70px}
  /* 卡片：pipeline 图作封面 + 毛玻璃内容层；无入场动画，打开页面即见 */
  .card{position:relative;aspect-ratio:3/4;border-radius:16px;cursor:pointer;overflow:hidden;
    border:1px solid rgba(255,255,255,.72);background:rgba(255,255,255,.42);
    -webkit-backdrop-filter:blur(18px) saturate(170%);backdrop-filter:blur(18px) saturate(170%);
    box-shadow:0 1px 2px rgba(20,24,31,.05),0 16px 34px -26px rgba(20,24,31,.42),
      inset 0 1px 0 rgba(255,255,255,.85);
    transition:transform .3s cubic-bezier(.2,.7,.3,1),box-shadow .3s ease}
  .card:hover,.card:focus-visible{transform:translateY(-5px);
    box-shadow:0 3px 6px rgba(20,24,31,.06),0 30px 54px -26px rgba(20,24,31,.48),
      inset 0 1px 0 rgba(255,255,255,.9)}
  .card::after{content:"";position:absolute;inset:0;border-radius:16px;
    pointer-events:none;box-shadow:inset 0 0 0 1px rgba(255,255,255,.5)}
  .bg{position:absolute;inset:-14%;background-size:cover;background-position:center;
    filter:blur(22px) saturate(150%);opacity:.44;transform:scale(1.08)}
  .plate{position:absolute;left:0;right:0;top:0;height:46%;padding:15px 15px 0;
    display:flex;align-items:center;justify-content:center}
  .plate .shot{width:100%;height:100%;background-size:contain;background-position:center;
    background-repeat:no-repeat;background-color:#fff;border-radius:10px;
    box-shadow:0 10px 22px -14px rgba(20,24,31,.42);border:1px solid rgba(20,24,31,.07)}
  .glass{position:absolute;left:0;right:0;top:42%;bottom:0;overflow:hidden;
    display:flex;flex-direction:column;padding:14px 17px 15px;
    border-top:1px solid rgba(255,255,255,.92);
    background:linear-gradient(180deg,rgba(255,255,255,.58),rgba(255,255,255,.88));
    -webkit-backdrop-filter:blur(20px) saturate(180%);backdrop-filter:blur(20px) saturate(180%)}
  .glass::before{content:"";position:absolute;left:0;top:0;bottom:0;width:2px;background:var(--rc)}
  .c-top{display:flex;align-items:center;gap:9px;margin-bottom:9px}
  .c-num{font-family:var(--serif);font-size:18px;color:var(--ink4);line-height:1}
  .c-route{font-size:10.5px;color:var(--rc);border:1px solid currentColor;
    border-radius:999px;padding:2px 8px;background:rgba(255,255,255,.62)}
  .c-star{font-size:12px;color:#A9741F;margin-left:auto}
  .c-en{font-family:var(--serif);font-size:19px;font-weight:400;line-height:1.3;
    margin:0 0 6px;color:var(--ink);
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .c-cn{font-size:11.5px;color:var(--ink3);margin:0 0 10px;line-height:1.6;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .c-key{font-size:12px;color:var(--ink2);margin:0;line-height:1.65;flex:1;
    display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
  .c-kl{display:inline-block;font-size:10px;color:var(--rc);border:1px solid currentColor;
    border-radius:4px;padding:0 5px;margin-right:6px;vertical-align:1.5px;
    background:rgba(255,255,255,.62)}
  .c-foot{display:flex;align-items:center;justify-content:space-between;gap:10px;
    margin-top:10px;padding-top:10px;border-top:1px solid rgba(20,24,31,.08)}
  .c-num2{font-family:var(--mono);font-size:10.5px;color:var(--ink3)}
  .c-go{font-size:11.5px;color:var(--rc);opacity:0;transform:translateX(-6px);
    transition:opacity .25s ease,transform .25s ease}
  .card:hover .c-go,.card:focus-visible .c-go{opacity:1;transform:none}

  footer{margin-top:50px;padding:26px 0 40px;border-top:1px solid var(--line);
    font-size:12.5px;color:var(--ink3);line-height:1.9}
  footer code{font-family:var(--mono);font-size:11.5px;color:var(--ink2)}

  /* ---------- 单篇阅读 ---------- */
  #detail{position:fixed;inset:0;z-index:60;overflow-y:auto;overflow-x:hidden;
    background:linear-gradient(180deg,#FAFBFC 0%,#F2F4F8 100%);
    opacity:0;transform:translateY(30px) scale(.988);pointer-events:none;
    transition:opacity .4s cubic-bezier(.2,.7,.3,1),transform .4s cubic-bezier(.2,.7,.3,1)}
  body.detail #detail{opacity:1;transform:none;pointer-events:auto}
  body.detail{overflow:hidden}

  .topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:12px;
    padding:12px clamp(20px,3.2vw,60px);background:rgba(255,255,255,.55);
    -webkit-backdrop-filter:blur(20px) saturate(190%);backdrop-filter:blur(20px) saturate(190%);
    border-bottom:1px solid rgba(255,255,255,.7)}
  .tbtn{font:inherit;font-size:12.5px;color:var(--ink);cursor:pointer;
    display:inline-flex;align-items:center;gap:7px;padding:8px 15px;border-radius:999px;
    background:rgba(255,255,255,.62);border:1px solid rgba(255,255,255,.8);
    -webkit-backdrop-filter:blur(14px) saturate(180%);backdrop-filter:blur(14px) saturate(180%);
    box-shadow:0 1px 2px rgba(20,24,31,.06);transition:transform .2s ease,box-shadow .2s ease}
  .tbtn:hover{transform:translateY(-1px);box-shadow:0 4px 14px -6px rgba(20,24,31,.3)}
  .tbtn:disabled{opacity:.35;cursor:default;transform:none;box-shadow:none}
  .tmid{flex:1;display:flex;align-items:center;gap:12px;min-width:0;justify-content:center}
  .tidx{font-family:var(--mono);font-size:12px;color:var(--ink3);flex:none}
  .tname{font-family:var(--serif);font-size:14px;white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis;max-width:44vw}
  .troute{font-size:11.5px;border:1px solid currentColor;border-radius:999px;
    padding:2px 10px;flex:none;color:var(--rc)}
  .tprog{position:absolute;left:0;bottom:-1px;height:2px;background:var(--accent);
    width:0;transition:width .1s linear}

  .dwrap{max-width:1520px;margin:0 auto;padding:0 clamp(20px,3.2vw,60px) 90px}
  .dh{padding:52px 0 28px;display:flex;gap:26px;
    animation:riseIn .5s cubic-bezier(.2,.7,.3,1) both}
  @keyframes riseIn{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
  .dh-num{font-family:var(--serif);font-size:64px;line-height:.9;color:var(--ink4);
    flex:none;letter-spacing:-.02em}
  .dh-t{min-width:0}
  .dh-route{font-size:11.5px;border:1px solid currentColor;border-radius:999px;
    padding:3px 11px;color:var(--rc)}
  .dh-star{margin-left:9px;font-size:12px;color:#A9741F}
  .dh h2{font-family:var(--serif);font-size:31px;font-weight:400;line-height:1.32;
    margin:14px 0 8px}
  .dh-cn{font-size:15px;color:var(--ink2);margin:0 0 14px}
  .dh-meta{display:flex;flex-wrap:wrap;align-items:center;gap:16px;font-size:12.5px;color:var(--ink3)}
  .dh-meta .mono{font-family:var(--mono);font-size:12px}
  .dh-meta .plink{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(42,90,140,.32);
    transition:border-color .2s ease,opacity .2s ease}
  .dh-meta .plink:hover{border-bottom-color:var(--accent);opacity:.72}
  .dh-prio{color:var(--am-m)}

  .dfig{margin:6px 0 40px;border-radius:14px;overflow:hidden;
    border:1px solid rgba(255,255,255,.88);
    background:linear-gradient(180deg,rgba(255,255,255,.86),rgba(255,255,255,.66));
    -webkit-backdrop-filter:blur(16px) saturate(170%);backdrop-filter:blur(16px) saturate(170%);
    box-shadow:0 1px 2px rgba(20,24,31,.05),0 18px 42px -30px rgba(20,24,31,.4),
      inset 0 1px 0 rgba(255,255,255,.9);
    animation:riseIn .5s cubic-bezier(.2,.7,.3,1) .04s both}
  .dfig img{display:block;width:100%;height:auto;background:#fff;cursor:zoom-in;
    border-bottom:1px solid var(--line)}
  .dfig figcaption{padding:14px 20px 16px;font-size:12.5px;color:var(--ink2);line-height:1.75}
  .dfig figcaption b{color:var(--ink);font-weight:500;margin-right:7px}
  .fignote{margin:0;padding:0 20px 15px;font-size:12px;color:var(--am-m)}

  .sech{font-family:var(--serif);font-size:19px;font-weight:400;margin:0 0 18px;
    padding-bottom:11px;border-bottom:1px solid var(--line);
    display:flex;align-items:baseline;gap:12px}
  .sech em{font-family:var(--mono);font-style:normal;font-size:10.5px;
    letter-spacing:.14em;text-transform:uppercase;color:var(--ink4)}

  .qasec{margin-bottom:44px;animation:riseIn .5s cubic-bezier(.2,.7,.3,1) .08s both}
  .qa{display:grid;grid-template-columns:1fr 1fr;gap:18px}
  .qa-i{border-radius:12px;padding:17px 19px;
    border:1px solid rgba(255,255,255,.88);
    background:linear-gradient(180deg,rgba(255,255,255,.82),rgba(255,255,255,.60));
    -webkit-backdrop-filter:blur(16px) saturate(170%);backdrop-filter:blur(16px) saturate(170%);
    box-shadow:0 1px 2px rgba(20,24,31,.05),0 14px 30px -26px rgba(20,24,31,.32),
      inset 0 1px 0 rgba(255,255,255,.92)}
  .qa-i h4{margin:0 0 9px;font-size:12.5px;font-weight:500;color:var(--ink)}
  .qa-i h4 b{font-family:var(--mono);font-size:10.5px;font-weight:500;color:#fff;
    background:var(--accent);border-radius:4px;padding:1px 5px;margin-right:8px;
    vertical-align:1.5px}
  .qa-i p{margin:0;font-size:13.5px;color:var(--ink2);line-height:1.85}
  .qa-i strong{color:var(--ink);font-weight:500}
  .qa-i code{font-family:var(--mono);font-size:12px;background:rgba(20,24,31,.05);
    padding:1px 5px;border-radius:4px;color:var(--accent)}
  .qa-i.opp{grid-column:1/-1;
    background:linear-gradient(180deg,rgba(250,238,218,.92),rgba(250,238,218,.62));
    border-color:rgba(186,117,23,.34)}
  .qa-i.opp h4 b{background:var(--am-m)}

  .srcsec{margin-bottom:26px;animation:riseIn .5s cubic-bezier(.2,.7,.3,1) .12s both}
  .srcwrap{display:grid;grid-template-columns:118px 1fr;gap:52px;align-items:start}
  .srcnav{position:sticky;top:88px;display:flex;flex-direction:column;gap:2px}
  .srcbtn{display:block;width:100%;text-align:left;font:inherit;font-size:14.5px;
    color:var(--ink4);background:none;border:none;cursor:pointer;
    border-left:2px solid transparent;padding:9px 0 9px 15px;
    transition:color .2s ease,border-color .2s ease}
  .srcbtn:hover{color:var(--ink2)}
  .srcbtn.on{color:var(--ink);border-left-color:var(--accent);font-weight:500}
  .srcbody{min-width:0}
  .srcpane{display:none;animation:fadeUp .3s ease both}
  .srcpane.on{display:block}
  @keyframes fadeUp{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
  .srcpane p,.srcpane li{font-size:15px;color:var(--ink2);line-height:1.95}
  .srcpane p{margin:0 0 16px}
  .srcpane p:last-child{margin-bottom:0}
  .srcpane ul,.srcpane ol{padding-left:22px;margin:0 0 16px}
  .srcpane li{margin-bottom:10px}
  .srcpane li>ul,.srcpane li>ol{margin-top:11px;margin-bottom:2px;padding-left:20px}
  .srcpane strong{color:var(--ink);font-weight:500}
  .srcpane code{font-family:var(--mono);font-size:12.5px;background:rgba(20,24,31,.05);
    padding:1px 6px;border-radius:5px;color:var(--accent)}

  .dnav{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:10px;
    padding-top:34px;border-top:1px solid var(--line)}
  .nbtn{display:block;text-align:left;padding:18px 20px;border-radius:12px;cursor:pointer;
    font:inherit;color:inherit;border:1px solid rgba(255,255,255,.86);
    background:linear-gradient(180deg,rgba(255,255,255,.80),rgba(255,255,255,.58));
    -webkit-backdrop-filter:blur(16px) saturate(170%);backdrop-filter:blur(16px) saturate(170%);
    box-shadow:0 1px 2px rgba(20,24,31,.05),inset 0 1px 0 rgba(255,255,255,.9);
    transition:transform .22s ease,box-shadow .22s ease}
  .nbtn:hover{transform:translateY(-3px);
    box-shadow:0 20px 40px -22px rgba(20,24,31,.42),inset 0 1px 0 rgba(255,255,255,.95)}
  .nbtn span{display:block;font-size:11.5px;color:var(--ink3);margin-bottom:5px;
    font-family:var(--mono)}
  .nbtn b{font-family:var(--serif);font-weight:400;font-size:15px}
  .nbtn.next{text-align:right}
  .nbtn:disabled{opacity:.32;cursor:default;transform:none;box-shadow:none}

  .lb{position:fixed;inset:0;z-index:200;display:none;align-items:center;justify-content:center;
    padding:26px;background:rgba(20,24,31,.7);cursor:zoom-out;
    -webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}
  .lb.on{display:flex;animation:fadeIn .22s ease both}
  @keyframes fadeIn{from{opacity:0}to{opacity:1}}
  .lb img{max-width:100%;max-height:100%;border-radius:10px;background:#fff;
    box-shadow:0 40px 90px -24px rgba(0,0,0,.66)}
  .lbhint{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);
    font-size:12px;color:rgba(255,255,255,.72);pointer-events:none}

  @media (max-width:820px){
    .dh{flex-direction:column;gap:12px}
    .dh-num{font-size:46px}
    .dh h2{font-size:24px}
    .qa{grid-template-columns:1fr;gap:14px}
    .srcwrap{grid-template-columns:1fr;gap:16px}
    .srcnav{position:static;flex-direction:row;gap:6px;flex-wrap:wrap}
    .srcbtn{border-left:none;border-bottom:2px solid transparent;padding:8px 4px;width:auto}
    .srcbtn.on{border-left:none;border-bottom-color:var(--accent)}
    .ftag{width:auto;text-align:left}
    .hero h1{font-size:26px}
  }
  @media (prefers-reduced-motion:reduce){
    *{animation:none!important;transition:none!important}
    html{scroll-behavior:auto}
  }
</style>
</head>
<body>

<main id="home">
  <div class="wrap">
    <header class="hero">
      <h1>__HERO_H1__</h1>
      <p class="lede">__HERO_LEDE__</p>
    </header>

    <h2 class="sec">__COMMON_HEAD__</h2>
    <div class="flow">
__FLOW_ROWS__
      <p class="flowcite">__FLOW_CITE__</p>
    </div>

    <h2 class="sec">__PAPERS_HEAD__</h2>
    <div class="grid" id="grid">
__CARDS__
    </div>

    <footer>
__FOOTER__
    </footer>
  </div>
</main>

<section id="detail" aria-hidden="true">
  <div class="topbar">
    <button class="tbtn" type="button" id="back">__BACK_LABEL__</button>
    <div class="tmid">
      <span class="tidx" id="tidx">01 / 10</span>
      <span class="tname" id="tname">—</span>
      <span class="troute" id="troute">—</span>
    </div>
    <div class="tprog" id="prog"></div>
  </div>
  <div class="dwrap" id="pane"></div>
</section>

__TEMPLATES__

<div class="lb" id="lb" role="dialog" aria-label="放大查看图示">
  <img id="lbimg" alt="">
  <span class="lbhint">点击任意处或按 Esc 关闭</span>
</div>

<script>
(function(){
  var body = document.body;
  var pane = document.getElementById('pane');
  var detail = document.getElementById('detail');
  var tIdx = document.getElementById('tidx');
  var tName = document.getElementById('tname');
  var tRoute = document.getElementById('troute');
  var prog = document.getElementById('prog');
  var grid = document.getElementById('grid');
  var cards = [].slice.call(grid.querySelectorAll('.card'));
  var lb = document.getElementById('lb');
  var lbimg = document.getElementById('lbimg');
  var TOTAL = cards.length;
  var cur = 1;

  function nameOf(el){
    var h = el.querySelector('.c-en');
    return h ? h.textContent : '';
  }
  var NAMES = {}, ROUTES = {};
  cards.forEach(function(c){
    NAMES[+c.dataset.n] = nameOf(c);
    ROUTES[+c.dataset.n] = c.querySelector('.c-route').textContent;
  });

  function wireTabs(){
    var btns = [].slice.call(pane.querySelectorAll('.srcbtn'));
    var panes = [].slice.call(pane.querySelectorAll('.srcpane'));
    btns.forEach(function(b){
      b.addEventListener('click', function(){
        btns.forEach(function(x){ x.classList.remove('on'); });
        panes.forEach(function(x){ x.classList.remove('on'); });
        b.classList.add('on');
        var t = pane.querySelector('.srcpane[data-pane="' + b.dataset.tab + '"]');
        if (t) { t.classList.add('on'); }
      });
    });
  }

  function paint(n){
    pane.innerHTML = '';
    var tpl = document.getElementById('t-' + n);
    if (tpl) { pane.appendChild(tpl.content.cloneNode(true)); }
    tIdx.textContent = (n < 10 ? '0' : '') + n + ' / ' + TOTAL;
    tName.textContent = NAMES[n] || '';
    tRoute.textContent = ROUTES[n] || '';
    cur = n;
    var nav = document.createElement('nav');
    nav.className = 'dnav';
    nav.innerHTML =
      (n > 1
        ? '<button class="nbtn prev" type="button" data-go="' + (n - 1) + '"><span>← 上一篇</span><b>' + NAMES[n - 1] + '</b></button>'
        : '<button class="nbtn prev" type="button" disabled><span>← 上一篇</span><b>已是第一篇</b></button>') +
      (n < TOTAL
        ? '<button class="nbtn next" type="button" data-go="' + (n + 1) + '"><span>下一篇 →</span><b>' + NAMES[n + 1] + '</b></button>'
        : '<button class="nbtn next" type="button" disabled><span>下一篇 →</span><b>已是最后一篇</b></button>');
    pane.appendChild(nav);
    [].slice.call(nav.querySelectorAll('[data-go]')).forEach(function(el){
      el.addEventListener('click', function(){ go(+el.dataset.go); });
    });
    wireTabs();
    detail.scrollTop = 0;
    prog.style.width = '0%';
  }

  function open(n){
    paint(n);
    body.classList.add('detail');
    detail.setAttribute('aria-hidden', 'false');
    if (history.replaceState) { history.replaceState(null, '', '#p' + (n < 10 ? '0' : '') + n); }
    [].slice.call(pane.querySelectorAll('.qasec, .srcsec')).forEach(function(s, i){
      s.style.animation = 'none';
      void s.offsetWidth;
      s.style.animation = 'riseIn .5s cubic-bezier(.2,.7,.3,1) ' + (0.08 + i * 0.06) + 's both';
    });
  }
  function close(){
    body.classList.remove('detail');
    detail.setAttribute('aria-hidden', 'true');
    if (history.replaceState) { history.replaceState(null, '', location.pathname + location.search); }
  }
  function go(n){ if (n < 1 || n > TOTAL) { return; } paint(n); open(n); }

  cards.forEach(function(c){
    function act(){ open(+c.dataset.n); }
    c.addEventListener('click', act);
    c.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); act(); }
    });
  });
  document.getElementById('back').addEventListener('click', close);

  document.addEventListener('keydown', function(e){
    if (lb.classList.contains('on')) {
      if (e.key === 'Escape') { lb.classList.remove('on'); lbimg.src = ''; }
      return;
    }
    if (e.key === 'Escape' && body.classList.contains('detail')) { close(); return; }
    if (!body.classList.contains('detail')) { return; }
    if (e.key === 'ArrowRight') { go(cur + 1); }
    if (e.key === 'ArrowLeft') { go(cur - 1); }
  });

  detail.addEventListener('scroll', function(){
    var max = detail.scrollHeight - detail.clientHeight;
    prog.style.width = (max > 0 ? (detail.scrollTop / max * 100) : 0) + '%';
  }, {passive: true});

  document.addEventListener('click', function(e){
    var t = e.target;
    if (t && t.closest && t.closest('.dfig img')) {
      lbimg.src = t.src; lb.classList.add('on'); return;
    }
    if (t === lb || t === lbimg) { lb.classList.remove('on'); lbimg.src = ''; }
  });

  var m = /#p(\d\d)/.exec(location.hash);
  if (m) { open(+m[1]); }
})();
</script>
</body>
</html>
"""

# ================= 项目配置 → CSS 变量 / 模板片段 =================
def route_vars(routes, accent, amber='#854F0B', per_line=3):
    """生成 :root 里的路线色变量（每行 3 个，与配色表的排布一致）。"""
    lines, cur = [], []
    for _name, key, color in routes:
        cur.append('--%s:%s;' % (key, color))
        if len(cur) == per_line:
            lines.append('    ' + ' '.join(cur)); cur = []
    if cur:
        lines.append('    ' + ' '.join(cur))
    lines.append('    --accent:%s; --am-m:%s;' % (accent, amber))
    return '\n'.join(lines)


def route_rules(routes, per_line=3):
    """生成 .r-xxx{--rc:var(--xxx)} 规则。"""
    lines, cur = [], []
    for _name, key, _color in routes:
        cur.append('.r-%s{--rc:var(--%s)}' % (key, key))
        if len(cur) == per_line:
            lines.append('  ' + ' '.join(cur)); cur = []
    if cur:
        lines.append('  ' + ' '.join(cur))
    return '\n'.join(lines)


def flow_rows(rows):
    """「共同判断」流程行。rows = [(标签, 结论, 出处, 是否淡化)]"""
    out = []
    for tag, node, note, done in rows:
        out.append('      <div class="frow"><span class="ftag">%s</span>\n'
                   '        <span class="fnode%s">%s</span>\n'
                   '        <span class="fnote">%s</span></div>'
                   % (html.escape(tag), ' done' if done else '',
                      html.escape(node), html.escape(note)))
    return '\n'.join(out)


def esc_head(heading, kicker):
    """二级标题：<h2 class="sec">中文<em>Kicker</em></h2>"""
    return '%s<em>%s</em>' % (html.escape(heading), html.escape(kicker))


page = (page
        .replace('__CARDS__', '\n'.join(cards))
        .replace('__TEMPLATES__', '\n'.join(templates))
        .replace('__ROOT_VARS__', route_vars(ROUTES, P.ACCENT))
        .replace('__ROUTE_RULES__', route_rules(ROUTES))
        .replace('__HTML_TITLE__', html.escape(P.HTML_TITLE))
        .replace('__HERO_H1__', html.escape(P.HERO_H1))
        .replace('__HERO_LEDE__', html.escape(P.HERO_LEDE))
        .replace('__COMMON_HEAD__', esc_head(P.COMMON_HEADING, P.COMMON_KICKER))
        .replace('__FLOW_ROWS__', flow_rows(P.COMMON_ROWS))
        .replace('__FLOW_CITE__', html.escape(P.COMMON_CITE))
        .replace('__PAPERS_HEAD__', esc_head(P.PAPERS_HEADING, P.PAPERS_KICKER))
        .replace('__FOOTER__', '\n'.join('      ' + l for l in P.FOOTER_LINES))
        .replace('__BACK_LABEL__', html.escape(P.BACK_LABEL)))

left = re.findall(r'__[A-Z_]+__', page)
if left:
    sys.exit('模板占位符未替换：%s' % sorted(set(left)))

open(OUT_HTML, 'w', encoding='utf-8').write(page)
print('html:', OUT_HTML, len(page), 'chars')
