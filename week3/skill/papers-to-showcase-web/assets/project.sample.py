# -*- coding: utf-8 -*-
"""项目配置模板 —— 复制为 project.py 后填写。**这是唯一需要按项目改的文件。**

`build_site.py` 与 `extract_figs.py` 都读这个文件；脚本本身不要改。
字段逐项说明见 ../references/content-contract.md。下面用一份三篇论文的虚构示例做骨架，
把中文/路径/清单换成你自己的内容即可。

    cp project.sample.py project.py
    python extract_figs.py project.py     # 先裁图
    python build_site.py   project.py     # 再生成
"""
import os

# 项目根目录：本文件放在 <root>/build/ 下，故取上一级。这样从任何目录运行都能找到文件。
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def p(*parts):
    return os.path.join(ROOT, *parts)


# ---------------------------------------------------------------- 路径
SUMMARY_MD = p('notes-summary.md')       # 源笔记 A：要点解读 + 速查表（结构见 content-contract.md）
TRANSLATION_MD = p('notes-translation.md')   # 源笔记 B：摘要 / 引言 / 结论三段译文
OUT_MD = p('merged.md')                  # 交付物 1：合并版 Markdown
OUT_HTML = p('showcase.html')            # 交付物 2：展示网页
PAPERS_DIR = p('papers')                 # 论文 PDF 目录
FIGS_DIR = p('papers/figs')              # 取图产物目录（自动创建）

# ---------------------------------------------------------------- 页面文案
HTML_TITLE = '示例 · 三篇论文速览'
HERO_H1 = '示例 · 三篇论文速览'
HERO_LEDE = '点击卡片进入单篇：含该论文的 pipeline 图、五问解读，以及摘要 / 引言 / 结论原文译文。'
BACK_LABEL = '← 返回列表'

COMMON_HEADING = '共同判断'
COMMON_KICKER = 'Shared Diagnosis'
# 每行 = (左标签, 结论, 出处, 是否淡化)。同一批论文共享的演进判断，3–6 行为宜。
COMMON_ROWS = [
    ('一阶问题', '这件事最早怎么做的', '历史方法 A · B', True),
    ('这一批', '它们共同在解决什么', '论文 1 / 论文 2', False),
    ('', '还差什么', '论文 3（换了个角度）', False),
]
# 面板底部那句观测旁证：最有说服力的一句，别省（例：同一天出现同向结论，说明是领域共识）
COMMON_CITE = '同一天出现同向结论，通常说明这已是领域共识而非个案。'

PAPERS_HEADING = '三篇论文'
PAPERS_KICKER = 'Three Papers'
# 页脚，每项一行；可含行内 HTML。**不要写前导缩进**（生成器会统一加）。
FOOTER_LINES = [
    '合并自 <code>notes-summary.md</code>（要点解读）与 '
    '<code>notes-translation.md</code>（三段译文）。<br>',
    '各篇图示从 <code>papers/*.pdf</code> 按图题自动裁取并内嵌（原文件保留在 '
    '<code>papers/figs/</code>），版权归原作者，此处仅供内部研读使用。<br>',
    '译文仅覆盖正文 prose，图表内部文字与数学符号未逐字译出；逐字核对请以 PDF 原文为准。',
]

# 单篇页的两枚小徽标（★ 与 落位序位）
STAR_BADGE = '优先精读'
PRIORITY_BADGE = '落位序位 第 %d'

# ---------------------------------------------------------------- 合并版 Markdown
MD_TITLE = '示例 · 三篇论文（要点解读 + 摘要 / 引言 / 结论译文）'
MD_HEADER_LINES = [
    '> 面向课题：示例课题',
    '> 合并自：`notes-summary.md` ＋ `notes-translation.md`',
    '> 未核验的数字请以 PDF 原文为准。',
]
MD_SECTIONS = dict(
    intro='〇、这批论文的共同判断',
    table='一、速查表',
    papers='二、逐篇：五问解读 + 三段译文',
    trend='三、三条趋势判断',
    land='四、落位建议',
    anchor='附 A：另需一并看的锚点',
    index='附 B：论文 PDF 与抽取文件索引',
)
MD_LABELS = dict(en_title='英文标题', cn_title='中文标题', source='出处', route='技术路线',
                 method='核心方法', numbers='关键数字', star='优先级', priority='落位建议序位')
STAR_NOTE = '★ 与课题直接同构，优先精读'
PRIORITY_FMT = '第 %d 篇'

# 源笔记的二级标题前缀（把下面这些换成你笔记里实际用的写法）
SOURCE_SECTIONS = dict(intro='〇', table='一、', detail='二、', trend='三、',
                       land='四、', anchor='附：', b_index='附：')

# ---------------------------------------------------------------- 分类与配色
# 每条路线 = (路线名, CSS 类后缀, 颜色)。后缀用短英文，会生成 .r-<后缀> 与 --<后缀> 变量。
# 颜色取克制的低饱和色，每条路线一个，贯穿卡片色条 / 药丸 / 顶栏标签。
ACCENT = '#2A5A8C'
ROUTES = [
    ('环境合成', 'syn', '#2A5A8C'),
    ('环境复用', 'reuse', '#1F7A6B'),
    ('环境演化', 'evo', '#8A5A1F'),
]
# {编号: (路线名, 落位序位, 是否★)}；序位 0 表示不显示
PAPERS_META = {
    1: ('环境合成', 1, True),
    2: ('环境复用', 2, False),
    3: ('环境演化', 0, False),
}
# {编号: 卡片短名} —— 卡片只放得下一两行，长标题必须给短名
SHORT = {1: 'Paper One', 2: 'Paper Two', 3: 'Paper Three'}

# ---------------------------------------------------------------- 图示裁取
# 每篇一条。必填：n 编号 / name 文件名短名 / pdf PDF 文件名（不含 .pdf，位于 PAPERS_DIR，
# **必须与磁盘上的文件名完全一致**）/ fig_page 图所在页 / cap_page 图题所在页 /
# label 图题标签（如 'Figure 1'）/ prefix 图题开头几个词（用于定位）。
# 可选：override=(y0, y1) 聚类失败时的人工兜底坐标；note 降级说明；substitute=True 标记替代图。
FIG_TARGETS = [
    dict(n=1, name='Paper1', pdf='paper1', fig_page=2, cap_page=2, label='Figure 1',
         prefix='Overview of our framework'),
    dict(n=2, name='Paper2', pdf='paper2', fig_page=3, cap_page=3, label='Figure 2',
         prefix='The pipeline consists of'),
    dict(n=3, name='Paper3', pdf='paper3', fig_page=2, cap_page=2, label='Figure 1',
         prefix='System overview', override=(120, 460)),
]

# ---------------------------------------------------------------- 五问内容
# 标题固定，一字不改；答案整段 Markdown，支持 **加粗** 与 `行内代码`。
Q_TITLES = [
    '这个工作解决什么问题',
    '怎么解决的',
    '为什么可以解决？',
    '如何证明有效性（用什么数据集）',
    '我们的机会点',
]

QA = {
    1: [
        '写**它诊断的问题**，含上一代方法的死结（"现有 X 只做到 A，撑不起 B"）。不要写它做了什么。',
        '写机制链条：A 做 X → B 做 Y，可带规模数字（合成了多少环境、多少任务）。',
        '写**机制层面的理由**：这条路为什么成立。不要写"因为实验效果好"。',
        '写**基准名 + 数字**，便于直接引用（例：Terminal-Bench 2.1 +11.9）。',
        '写对**用户课题的机会点**，开头用加粗亮出那句判断，后接具体做法。',
    ],
    2: [
        '第二篇的答案。',
        '……',
        '……',
        '……',
        '……',
    ],
    3: [
        '第三篇的答案。',
        '……',
        '……',
        '……',
        '……',
    ],
}
