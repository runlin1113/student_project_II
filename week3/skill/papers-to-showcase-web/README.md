# papers-to-showcase-web

把一批论文 PDF + 调研笔记，做成**单文件、零依赖、学术汇报风**的展示网页。

一次生成两份交付物：

- **`showcase.html`** —— 主页面是 3:4 卡片墙，每张卡用该论文的 pipeline 图作封面、毛玻璃承载文字；
  点进去是「一屏一论文」：毛玻璃吸顶栏、pipeline 图（点击放大）、**五问解读**、
  以及左侧三个文字按键切换的摘要 / 引言 / 结论译文。全部图片 base64 内嵌，单文件可直接发给别人。
- **`merged.md`** —— 两份源笔记按论文重组的合并版（每篇 = 元信息 → 五问解读 → 三段译文）。

> 这是一个 Agent Skill：`SKILL.md` 给智能体读，本文件给人读。

## 快速开始

```bash
# 1) 装依赖（只有两个：取图与图片压缩）
pip install pymupdf pillow
#    可选：node 用于校验内联 JS 语法；Chrome/Edge/Chromium 用于截图复核

# 2) 把脚本放进你的项目
mkdir -p build
cp assets/{project.sample.py,build_site.py,extract_figs.py,validate_site.py} build/
mv build/project.sample.py build/project.py

# 3) 填 build/project.py（路径、文案、论文清单、五问答案）
#    字段说明见 references/content-contract.md

# 4) 取图 → 生成 → 校验
python build/extract_figs.py build/project.py        # 产出 papers/figs/，务必看一眼 figcheck.png
python build/build_site.py   build/project.py        # 产出 showcase.html + merged.md
python assets/validate_site.py showcase.html --shots # 静态校验 + 无头截图
```

**不需要改任何脚本**：项目相关的一切都在 `project.py` 里。脚本用 `shutil.which` 自动找
`node` 与浏览器，也可以用环境变量 `NODE` / `CHROME` 指定路径。

## 目录结构

```
papers-to-showcase-web/
├── SKILL.md                        智能体入口：成品规格 + 七步流程 + 反模式
├── README.md                       本文件
├── LICENSE
├── references/
│   ├── content-contract.md          project.py 字段表、源笔记结构约定、五问写作约束
│   ├── design-system.md             设计令牌 / 字体 / 毛玻璃配方 / 卡片三层 / 布局数值 / 动效
│   └── pitfalls.md                  22 条实际踩过的坑与排查命令
└── assets/
    ├── build_site.py                生成器（配置驱动，不建议修改）
    ├── extract_figs.py              从 PDF 自动裁 pipeline 图（三档规格）
    ├── validate_site.py             交付前校验（静态 + 截图）
    └── project.sample.py            项目配置模板 —— 复制为 project.py 后填写
```

## 它解决什么问题

把 8–20 篇论文（尤其是同一方向的「最新一批」）整理成汇报材料，通常要在三件事上反复耗时间：
**逐篇读摘要、从 PDF 里抠框架图、把内容排成能讲的形式**。这个 skill 把三件事流程化：

| 环节 | 做法 |
|---|---|
| 选文与分类 | 核验身份（标题 / arXiv / 日期），按技术路线分桶，给出与课题的贴合度序位 |
| 内容 | 每篇固定五问：解决什么问题 / 怎么解决 / 为什么能解决 / 怎么证明有效 / 我们的机会点 |
| 配图 | 按图题自动定位并从 PDF 裁出框架图，附对照图人工复核 |
| 呈现 | 卡片墙 + 单篇阅读双视图；学术风（衬线标题 + 等宽编号 + 毛玻璃 + 克制配色） |
| 交付 | 单文件 HTML（图片内嵌，可离线、可转发）+ 合并版 Markdown |

## 设计取向

- **一篇论文一屏**，不是把十篇堆在一个长页面里滚动。
- **毛玻璃必须有东西可糊**：卡片下铺该图自己的模糊副本，玻璃才有真实纹理，而不是半透明白块。
- **默认没有入场动画**：卡片即时可见。逐张延迟的动画会被误读成"页面在加载"。
- **内容只用原文**：五问答案不引入论文之外的信息；译文只覆盖正文，图表内文字不逐字译。

细节见 `references/design-system.md`。

## 许可

MIT —— 见 `LICENSE`。论文原文与图示版权归原作者，生成的页面仅建议用于内部研读。

## 贡献

`references/pitfalls.md` 是这份 skill 最有价值的部分之一。如果你踩到了新的坑，
欢迎补一条（现象 → 根因 → 处理），比改代码更有用。
