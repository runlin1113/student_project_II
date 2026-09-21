---
name: papers-to-showcase-web
description: "Turn a folder of paper PDFs and literature notes into a single-file, zero-dependency academic showcase website. Pipeline: select & route-classify the papers, extract 摘要/引言/结论 translations, auto-crop each paper's pipeline figure out of its PDF, author the per-paper 五问 (five-question) analysis, then generate the site — a 3:4 card wall whose cards use the pipeline figure as cover with a real blurred-glass content layer, plus a one-paper-per-screen reading view (glass sticky topbar, figure lightbox, 5-question grid, three text tabs switching 摘要/引言/结论). No local paths, no per-project code edits: all project data lives in one config file. Use when a user asks to 把论文做成网页/展示页/卡片墙/汇报页, 合并两份文献笔记并做一个 HTML, 一篇论文一个画面, or wants a papers showcase site."
description_zh: "把一批论文 PDF + 调研笔记做成单文件学术展示网页：选文分类 → 译文抽取 → pipeline 图自动裁取 → 五问解读 → 3:4 卡片墙 + 单篇全屏阅读视图（毛玻璃 / 图表封面 / 三键切换原文）；全部项目数据集中在一个配置文件中，无需改代码"
version: 2.0.0
agent_created: true
allowed-tools: Bash,Read,Write,Edit
display_name: "论文展示网页生成"
---

# 论文展示网页生成

把「一批论文 PDF + 调研笔记」变成**单文件、零依赖、学术汇报风**的展示网页。
一次生成两份交付物：展示网页 + 合并版 Markdown。

本 skill 自带跑通的生成器、取图脚本与校验脚本；**项目相关的一切都写在一个配置文件里**，
脚本不需要修改。设计与踩坑记录都在 `references/`，源码在 `assets/`。

## 安装与依赖

把整个 `papers-to-showcase-web/` 目录放进 agent 的 skills 目录即可（例如
`~/.workbuddy/skills/`、`~/.claude/skills/`，或任何 agent 约定的技能目录）。
也可以不安装——直接把文件夹给 agent，让它读本文件按流程执行。

依赖（只用标准库之外的三个）：

```bash
python -c "import pymupdf, PIL" || pip install pymupdf pillow   # 取图与压缩必需
node --version      # 可选：仅用于校验内联 JS 语法
google-chrome --version   # 可选：仅用于 --shots 截图复核（Chrome / Edge / Chromium 均可）
```

脚本会用 `shutil.which` + 常见安装路径自动找 `node` 与浏览器；找不到就跳过该项并给提示，
可以用环境变量 `NODE` / `CHROME` 手动指定。

## 成品规格（固定，不要自创）

| 页面 | 内容 |
|---|---|
| **主页** | 标题区（h1 + 一句 lede）→「共同判断」流程面板 + 一句观测旁证 → 一组 3:4 卡片（pipeline 图作封面 + 毛玻璃文字层）→ 页脚（来源 / 版权 / 口径声明） |
| **单篇页** | `position:fixed; inset:0` 全屏层，一屏一论文：毛玻璃吸顶栏（返回 / 序号 / 短名 / 路线 / 上下篇 / 滚动进度条）→ hero（巨号序号 + 衬线短名 + 中文标题 + arXiv·日期·落位序位）→ pipeline 图（点击放大）→ 五问解读（**2 列 + 第 5 问通栏琥珀**）→ 原文（左侧三个纯文字按键「摘要/引言/结论」，右侧只显示选中那一段）→ 底部上下篇导航卡 |
| **交互** | hash 路由 `#p04` 可直达可分享、`←/→` 翻篇、`Esc` 返回、点图开灯箱、卡片可 Tab 聚焦 + Enter/Space 打开 |
| **交付** | 1 个 `.html`（图片 base64 内嵌，不依赖外部资源）+ 1 份合并版 Markdown |

固定文案：**必须**是「五问解读」而不是「要点解读」；五问标题一字不改（见步骤三）。

## 何时使用

- 用户给一批论文（PDF 或已整理笔记）要「做成网页 / 展示页 / 卡片墙 / 汇报页」
- 用户要把两份文献笔记**合并成一份**并同时要一个 HTML
- 用户提出「一篇论文一个画面」「五问解读」「pipeline 图作封面」「毛玻璃」这类结构要求
- 用户明确列出五问清单（那就是本 skill 的五问，直接套用）

**不适用**：只要文字报告或问题树 → 用 `paper-problem-tree-read`。

## 目录约定

在用户的工作目录下这样组织（名称可改，改完同步写进 `project.py`）：

```
<project>/
  notes-from-reading.md        源笔记 A：要点解读 + 速查表（用户已有，不要改）
  notes-translation.md         源笔记 B：摘要 / 引言 / 结论三段译文（用户已有，不要改）
  papers/*.pdf                 论文原文
  papers/figs/                 取图产物（自动生成：figNN_*.png / NN_*_mid.jpg / NN_*_bg.jpg / manifest.json）
  build/
    project.py                 ← 唯一的项目配置（从 assets/project.sample.py 复制后填写）
    build_site.py              ← 从 skill 复制，不改
    extract_figs.py            ← 从 skill 复制，不改
    validate_site.py           ← 从 skill 复制，不改
  showcase.html                交付物 1
  merged.md                    交付物 2
```

## 七步流程

### 步骤一 · 选文与分类（决定后面所有内容）

1. 列目录，确认篇数。**8–20 篇合适，10 篇最佳**（四列卡片墙刚好两行半，单篇翻页手感也够）。
2. **核验身份，不能省**：文件名常是编号或乱码。逐篇确定 `英文标题 / 中文标题 / arXiv 编号 / 日期`，
   编号与日期到官方页面核验（arXiv 网页），**不要凭记忆写**。
3. 留一份**速查表**（源笔记 A 的第「一」节）：`| N | 短名 | 中文名 | 技术路线 | 核心方法一句话 | 关键数字 | arXiv |`。
4. **按技术路线分桶**：路线之间必须互不重复，且能解释「为什么这几篇算一批」。
   每篇产出 `(路线, 落位序位, 是否★优先精读)`，写进 `project.py` 的 `PAPERS_META`。
   - 路线驱动**配色**（每条路线一个克制的强调色）、卡片药丸、顶栏标签，所以路线名要短（4–5 字）。
   - 落位序位 = 按与用户课题的贴合度排序，在回复里说明「先读哪篇」。

### 步骤二 · 抽取三段译文

每篇取 **摘要 / 引言 / 结论** 三段译文，写成源笔记 B：`## N. 短名 —— 中文短名`，
其下 `**中文标题**：…`、`` `arXiv:xxxx.xxxxx`（日期）``、`### 摘要`、`### 引言`、`### 结论`。

- **只译正文 prose**；图表内文字与数学符号不逐字译，关键术语保留英文或括号注原文。
- 几十 KB 中文**用脚本按 `## N.` 切段，别手抄**。
- 在文档头部与页脚写明：译文口径、合并时间、以 PDF 原文为准。
- 源笔记 A 的结构（二级标题前缀）与这里的结构都是**约定**，见 `references/content-contract.md`。

### 步骤三 · 写五问（成品质量的分水岭）

五问标题**固定如下，一字不改**：

```
1 这个工作解决什么问题   2 怎么解决的      3 为什么可以解决？
4 如何证明有效性（用什么数据集）          5 我们的机会点
```

| 问 | 要写成什么 | 容易写错成 |
|---|---|---|
| 1 | **它诊断的问题**，含上一代方法的死结（"现有 X 只做到 A，撑不起 B"） | 它做了什么 |
| 2 | 机制链条：A 引擎做 X → B 引擎做 Y，可带规模数字 | 罗列优点 |
| 3 | **机制层面的理由**（为什么这条路成立） | "因为实验效果好" |
| 4 | **基准名 + 数字**（如 Terminal-Bench 2.1 +11.9 / Qwen3） | "作者做了大量实验" |
| 5 | 对用户课题的机会点，**开头用加粗亮出那句判断**，后接具体做法 | 泛泛的"值得借鉴" |

内容只能来自该篇摘要/引言/结论与原文数字，**不引入外部信息**。答案写进 `project.py` 的 `QA`
（整段 Markdown，支持 `**加粗**` 与 `` `行内代码` ``）。详细约束见 `references/content-contract.md`。

### 步骤四 · 裁 pipeline 图

```bash
cp <skill>/assets/{project.sample.py,build_site.py,extract_figs.py,validate_site.py} build/
mv build/project.sample.py build/project.py     # 然后填写 project.py
python build/extract_figs.py build/project.py
```

`FIG_TARGETS` 里每篇一条：`pdf`（PDF 文件名，不含扩展名，**必须与磁盘一致**）、`fig_page` / `cap_page`
（图与图题所在页）、`label`（`Figure 1`）、`prefix`（图题开头几个词，用于定位）。

三条路径：`cluster`（默认，图题定位 + 图形元素连通聚类）→ `override=(y0,y1)`（聚类不出来时人工锚定）
→ `substitute`（图损坏时换该篇另一张完整的图，**并在页面上写明替代原因**）。

**必须打开 `papers/figs/figcheck.png` 对照图逐张看一眼** —— 自动裁切一定有 1–3 张要兜底。
判定标准：只含图、不含正文、不含图题（图题由 HTML 的 `<figcaption>` 渲染）。

### 步骤五 · 生成

```bash
python build/build_site.py build/project.py
```

产出两份文件（路径由 `project.py` 的 `OUT_HTML` / `OUT_MD` 决定）。
**生成器的代码与外观不要改**：需要调的是 `project.py`。

### 步骤六 · 校验（不可跳过）

```bash
python <skill>/assets/validate_site.py showcase.html --shots
```

脚本自检：JS 语法（`node --check`）、标签配对、占位符残留、错误转义、
卡片/模板/五问/按键/图示计数、是否残留逐张入场动画；`--shots` 再拍无头截图。

**四张图必须亲眼确认**：① 主页首屏已见卡片与封面 ② 单篇页封面/图示位置正确
③ 玻璃层底下有真实纹理（不是纯白块）④ 图题没有在图里和 HTML 里各出现一次。

### 步骤七 · 交付

`present_files` 同时给 html 与合并版 md。回复里讲清：内容结构、五问与配图上的取舍、
以及**所有已知缺陷**（哪篇用了替代图、哪张图偏暗等）。不要隐瞒降级项。

## 反模式（不要这样做）

- **不要给卡片加逐张延迟的入场动画**。用户会理解成"页面要加载一下才弹出来"。（默认交付静默即显版本）
- **不要用 `background-size: cover` 把横向 pipeline 图塞进竖卡片**，会裁成约 18% 宽的竖条，图就废了。
- **不要把长文本放进 JS 字符串**。译文一律作为 HTML 文本节点 / `<template>` 输出，从根上消灭引号转义问题。
- **不要把图题烘焙进图片**，也不要用"上一个文本块底边"当图区上界。
- **不要为适配新项目去改 `build_site.py` 的 CSS 或结构**——外观是验收过的规格；要改的是 `project.py`。
- **不要只做静态检查就交付**，白屏与错位只有渲染出来才看得见。
- **不要改用户的两份源笔记**；一切合并产物都由脚本生成，可重跑。
- **不要在脚本里写死绝对路径**；路径全部走 `project.py`，这样换机器、换目录都不用改代码。

## 参考文件

- `references/content-contract.md` —— `project.py` 字段表、源笔记结构约定、五问写作约束
- `references/design-system.md` —— 设计令牌、字体、毛玻璃配方、卡片三层、布局数值、动效与响应式
- `references/pitfalls.md` —— 22 条已踩过的坑与排查命令
- `assets/build_site.py` / `extract_figs.py` / `validate_site.py` / `project.sample.py`
- `README.md` —— 人类读者入口（安装、快速开始、许可）
