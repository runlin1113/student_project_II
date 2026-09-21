# 已知的坑与排查（全部实际踩过）

按流程阶段分组。每条都给出「现象 → 根因 → 处理」。

## 一、环境与阅读

**1. `import fitz` 会告警** —— 统一写 `import pymupdf`。
```bash
python -c "import pymupdf, PIL" || pip install pymupdf pillow
```

**2. Read 工具读长文本会被截断** —— 超长会返回 `persisted-output` 预览，等于没读到。用 `offset`/`limit` 分块，**每块 ≤700 行**，按章节边界切而不是行数边界。

**3. 文件名 ≠ 论文身份** —— `2308.pdf` 可能既不是标题也不是 arXiv 编号。先做身份辨识表（文件名 ↔ 真实标题 ↔ 机构 ↔ arXiv），再去官网核验编号与日期。

## 二、图示裁取

**4. 用「上一个文本块底边」当图区上界 → 只裁到图题上方一条边。**
图内的标签文字本身就是文本块，会把上界卡在图内部。**必须收集 `get_image_info()` 的 bbox ∪ `get_drawings()` 的 rect，做连通聚类**（容忍约 30pt 内部留白），并过滤掉高度 > 0.85 页高的背景块。

**5. 有些图聚类不出来** —— 图在页中而矢量元素不足、短宽型图、跨页浮动体。给每条 `FIG_TARGETS` 留 `override=(y0, y1)` 人工兜底，用 `page.search_for('图内某个标签')` 算出 y 范围。
若图与图题不同页，聚类时要放宽下界：`cluster_bbox(page, cap_y0 + 40)`。

**6. 图题被烘焙进图片，页面上出现两次。**
裁图时收到图题上沿：`y1 = min(y1, cap_bbox[1] - 3)`（前提 `cap_page == fig_page`），图题交给 HTML 的 `<figcaption>` 渲染——顺带还能被搜索、被选中。

**7. 损坏的 PDF 取不到图** —— 报 `object is not a stream`。
先试重写：`d.save('out.pdf', garbage=4, deflate=True, clean=True)`；换 `pypdfium2` 解析器（它能容忍的更多，但也可能直接拒绝加载整个文档）；网络重下 arXiv 往往被阻断。**确实恢复不了就换该篇另一张完整的图，并在页面上用琥珀色 `.fignote` 写明"原图损坏、改用 Figure N 示意"** —— 不要静默糊弄，也不要假装有图。

**8. 自动裁切必须人工过一遍对照图。** `extract_figs.py` 结尾会拼一张 `figcheck.png`（在 `FIGS_DIR` 下），逐张检查：只含图、不含正文、不含图题。10 篇规模通常有 1–3 张要兜底。

**9. 论文 PDF 改名后，图示脚本的路径会静默失效。**

`FIG_TARGETS` 里的 `pdf=` 若写 arXiv 编号文件名（`2609.05576`），一旦按论文名重命名（`EnvCraft`），
10 条里有 9 条失效 —— `pymupdf.open` 直接抛错，或被 try 吞掉后少几张图而无人察觉。
**改名后先跑一次路径自检再重跑裁图**：

```bash
python -c "
import os, sys, importlib.util
spec = importlib.util.spec_from_file_location('p', 'build/project.py')
P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
have = set(os.listdir(P.PAPERS_DIR))
bad = [t['pdf'] for t in P.FIG_TARGETS if t['pdf'] + '.pdf' not in have]
print('缺失路径:', bad or '无 —— 全部命中')
"
```

判定修复可靠：修复前后各跑一次，用 `md5sum` 对比 `FIGS_DIR/*`，应逐字节一致。

## 三、生成与转义

**10. 长文本不要放进 JS 字符串。**
中文内容里的半角双引号 `"` 会提前终止字面量（页面直接白屏）。规则：
- 内容超过几千字 → **一律作为 HTML 文本节点 / `<template>` 输出**，JS 只做显隐与交互。
- 确需放进 JS（如问题树数据）→ 中文引号统一用 `「」` 或 `“”`，写完 `node --check` 校验。

**11. Markdown 列表嵌套被拆成两个平行区块** —— 按 `^- ` 逐行收集会把「父条目 + 缩进子列表」拆开。写递归解析：
```python
LIST_RE = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.*)$')
def parse_list(lines, i, base_indent):   # 遇到更深缩进就递归，挂进上一条 <li>
```

**12. 递归生成的 HTML 被二次转义** —— 页面上直接显示 `<ol><li><strong>` 字样。
`inline()` 里的 `html.escape()` 把已经是 HTML 的子列表又转义了一遍。必须**先转义纯文本、再拼子列表**：
```python
items.append(inline(content) + sub)      # 对
items.append(inline(content + sub))      # 错
```
自查：生成后 `grep -c '&lt;\(ol\|ul\|li\|p\|strong\)&gt;'` 应为 0。

**13. 五问网格在宽屏会变成三列** —— `repeat(auto-fit,minmax(420px,1fr))` 在 1520px 下算成 3 列，五问排成 3+2、第二行留空两格。改用**显式两列** `1fr 1fr`（移动端覆写为 `1fr`）。

## 四、校验与交付

**14. 无头 Chrome 不推进 CSS 动画** —— 带 `animation-fill-mode:both` 且 `from{opacity:0}` 的元素会停在不可见状态，截图看起来"只渲染了一张卡"。加 `--force-prefers-reduced-motion` 看到真实布局（前提是页面写了 reduced-motion 降级）。

**15. 卡片不要加逐张延迟入场动画。**
`animation:cardIn .55s ... both; animation-delay:calc(var(--i)*55ms)` 让第 10 张 0.5 秒后才出现，用户会认为"点开页面要加载一下才弹出来"。**默认交付静默即显版本**，动效仅在用户明确要求时加。

**16. 外链图片在预览面板会 404** —— 有些预览环境只托管交付的那一个 HTML 文件（形如 `/static-html/<hash>/<文件名>`），同级子目录的图取不到。**一律 base64 内嵌**（原图另存 `FIGS_DIR/` 备用）。单文件因此到 1 MB 量级，可接受。

**17. 交付前必须跑一次渲染** —— 静态检查过了不等于没白屏。
```bash
python <skill>/assets/validate_site.py showcase.html --shots
```

**18. 临时文件要清理，脚本与配置要保留** —— 截图目录 `_check/`、对照图 `figcheck.png` 是临时产物；
`build/` 下的脚本与 `project.py` 必须保留，源笔记更新后一键重跑即可同步刷新交付物。

**19. 不要修改用户的两份源笔记。** 合并产物一律由脚本生成。

**20. 一次性补丁脚本别指望跨命令存活。**
开发中出现过"写入报成功、下一条命令就 `No such file`"：某次补丁脚本与 `pitfalls.md.bak` 备份同时消失，
而 `_check/`、`figcheck.png` 这类文件却正常保留 —— 与沙箱/同步盘的文件回收机制有关，文件名规则不完全可预测。三条对策：

- 一次性补丁**在写入的同一条命令里跑完**，或干脆用编辑工具直接改目标文件；
- 备份用 `名称_v2` 后缀，不要用 `.bak`；
- 改完立刻 `grep` 验证结果，不要默认"上一步成功了"。

**21. 批量改编号要降序、且必须先确认文件没被改过。**
把 `9..18` 顺移成 `10..19` 时：① 必须**从大到小**替换，否则先做的 9→10 会被随后的 10→11 二次命中，一路错到底；
② 动手前确认文件**尚未顺移过**——曾因在已顺移过的文件上又顺移一遍，结果 #9 空号、#19 重复。
改完用 `grep -o '^\*\*[0-9]*\.' 文件 | tr -d '*.'` 打印编号序列，确认连续、无缺号、无重号。

**22. 脚本换目录运行时，manifest 里的相对路径会失效。**
第一版把图片路径写成项目相对路径（`papers/figs/fig01_x.png`），脚本一旦从 `build/` 目录运行就全部
`exists()` 失败 —— 页面静默缩到 74 KB（正常 1.1 MB），图全没了。规则：
**`manifest.json` 只存文件名，路径由配置的 `FIGS_DIR` 解析**，解析函数对「绝对路径 / 目录相对 / 纯文件名」三级兜底。
症状很好认：**产出 HTML 明显变小 = 图没内嵌进去**（正常 1 MB 量级）。

## 五、已知的未解决项

- **中文行宽**：正文满宽（1520px）时一行约 74 个汉字，超出中文舒适区（35–45 字/行）。
  这是需求方明确要求的宽度；若要收敛，在 `.srcbody` 加 `max-width:100ch` 即可。
- **主页与单篇页宽度不一致**：主页 `.wrap` 1180px、单篇 `.dwrap` 1520px。若要统一，改 `.wrap` 一处。
