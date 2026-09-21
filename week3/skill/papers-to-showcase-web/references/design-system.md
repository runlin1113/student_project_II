# 设计规范（照抄即可复现同样效果）

## 三条设计意图

1. **学术汇报风，不是产品落地页**：衬线中文标题 + 等宽数字 + 大量留白 + 克制的强调色。不要圆润可爱的插画风，不要渐变按钮，不要彩色图标。
2. **一切「卡片」都是毛玻璃，而不是半透明白块**：玻璃必须有真实内容可糊（背景渐变或图片纹理）。
3. **一篇论文一屏**：进入单篇后是独立的全屏层，不是同一个页面向下滚动。

## 一、设计令牌

```css
:root{
  /* 墨色层级（正文 → 最淡） */
  --ink:#14181F; --ink2:#3B4453; --ink3:#6B7484; --ink4:#9AA1AC;
  --paper:#F7F8FA; --line:rgba(20,24,31,.10); --line2:rgba(20,24,31,.16);

  /* 技术路线强调色（每条路线一个，克制、偏灰调，不要高饱和） */
  --syn:#2A5A8C;      /* 环境合成 蓝 */
  --reuse:#1F7A6B;    /* 环境复用 青 */
  --evo:#8A5A1F;      /* 环境演化 棕 */
  --reshape:#6B4C8A;  /* 环境重塑 紫 */
  --reward:#8A3A3A;   /* 奖励构造 红 */
  --neuro:#3A6B2A;    /* 神经合成 绿 */

  --accent:#2A5A8C;   /* 默认强调色，取第一条路线色 */
  --am-m:#854F0B;     /* 琥珀深色：★、机会点卡、降级说明 */

  --serif:"Songti SC","Source Han Serif SC","Noto Serif SC",Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  --mono:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;
}
```

字体分工（**不要混用**）：

| 用途 | 字体 |
|---|---|
| 中文标题、卡片短名、巨号序号 | `--serif`（衬线，学术感来源） |
| arXiv 号、编号、`SOURCE TEXT` 这类小标签 | `--mono` |
| 正文、说明 | `--sans` |

路线色用法：容器加 `class="r-syn"` 后，其内部一律用 `var(--rc)` 取色 → `.r-syn{--rc:var(--syn)}`。
卡片左侧竖条、路线药丸、顶栏标签、「阅读 →」全部走 `--rc`，**一个色系贯穿一张卡**。

## 二、背景：毛玻璃的前提

```css
body::before{content:"";position:fixed;inset:0;z-index:-1;
  background:
    radial-gradient(820px 560px at 10% -8%,rgba(42,90,140,.13),transparent 62%),
    radial-gradient(680px 500px at 94% 4%,rgba(138,90,31,.10),transparent 60%),
    radial-gradient(760px 600px at 66% 104%,rgba(31,122,107,.10),transparent 62%),
    linear-gradient(180deg,#FAFBFC 0%,#F3F5F8 100%)}
```

**这是整套视觉的地基。** 全平背景上，`backdrop-filter` 与"半透明白卡"看不出区别；有了柔和的径向色斑，玻璃才有层次。

单篇页自己是全屏层，需再给一层底：`background:linear-gradient(180deg,#FAFBFC 0%,#F2F4F8 100%)`。

## 三、毛玻璃配方（四件套，一字不改）

```css
background:linear-gradient(180deg,rgba(255,255,255,.80),rgba(255,255,255,.58));
border:1px solid rgba(255,255,255,.86);
-webkit-backdrop-filter:blur(16px) saturate(170%);backdrop-filter:blur(16px) saturate(170%);
box-shadow:0 1px 2px rgba(20,24,31,.05), 0 14px 30px -24px rgba(20,24,31,.3),
           inset 0 1px 0 rgba(255,255,255,.9);
```

要点：**上白下透的渐变** + **白边框** + **`inset` 顶部内高光**。少任何一项都会塌成"灰白方块"。
使用位置：共同判断面板、卡片玻璃层、上下篇导航卡、指示灯箱遮罩、顶栏。
按钮另加 `:hover{transform:translateY(-1px);box-shadow:0 4px 14px -6px rgba(20,24,31,.3)}`。

## 四、卡片（3:4，三层结构）

```css
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:22px}
.card{position:relative;aspect-ratio:3/4;border-radius:16px;overflow:hidden;cursor:pointer;
  border:1px solid rgba(255,255,255,.72);background:rgba(255,255,255,.42);
  backdrop-filter:blur(18px) saturate(170%)}
```

三层（缺一层就出问题）：

| 层 | 作用 | 关键属性 |
|---|---|---|
| `.bg` | **模糊底衬** —— 给玻璃层提供可糊的真实纹理 | `inset:-14%` + `background-size:cover` + `filter:blur(22px) saturate(150%)` + `opacity:.44` + 用 `_bg.jpg`（56px 小图） |
| `.plate` | 顶部 46%，白板承载**清晰**封面图 | `background-size:contain` + `background-color:#fff` + 圆角 10px + 淡投影，用 `_mid.jpg`（560px） |
| `.glass` | 从 42% 到底部，`backdrop-filter:blur(20px) saturate(180%)`，承载**全部文字** | 上边框 `1px solid rgba(255,255,255,.92)`；`::before` 画左侧 2px 路线色条 |

**为什么必须 `.bg`**：pipeline 图多是 4:1 横向，塞进 3:4 竖卡**只能用 `contain`**（`cover` 会裁成约 18% 宽的竖条，流程图彻底不可读）。但 `contain` 留下大片白，玻璃层背后就没东西可糊 → 于是额外铺一层该图自己被模糊的小副本。

卡片文字（全部单行数截断，防止长短不一撑破卡片）：

- `.c-num` 衬线 `01`（18px，`--ink4`）→ `.c-route` 路线药丸（10.5px，`--rc`）→ `.c-star` ★（靠右）
- `.c-en` 衬线短名 19px，`-webkit-line-clamp:2`
- `.c-cn` 中文标题 11.5px，`--ink3`，clamp 2
- `.c-key` 一句话方法 12px，`flex:1`，clamp 3，前面挂 `.c-kl`「方法」小标签
- `.c-foot` 分隔线上方：等宽 arXiv 号 + 「阅读 →」（悬停才浮现）

**卡片不得有入场动画。** 逐张延迟 + `animation-fill-mode:both` 会让最后一张 0.5 秒后才出现，用户理解为"页面要加载"。

## 五、主页布局

```
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}
.hero{padding:40px 0 20px;text-align:center}   h1 衬线 28px / lede 13.5px max-width:62ch
h2.sec{衬线 19px; display:flex;align-items:baseline;gap:12px}
h2.sec em{mono 11px; letter-spacing:.14em; text-transform:uppercase; color:var(--ink4)}
h2.sec::after{content:"";flex:1;height:1px;background:var(--line)}   /* 标题右侧长横线 */
```

- 「共同判断」面板：每行 = `.ftag`（右对齐 182px 小标签）+ `.fnode`（白底圆角结论）+ `.fnote`（灰字出处）。
- 面板下方 `.flowcite`：左 3px 琥珀竖线 + 极浅琥珀底，写那句**观测旁证**（如"同一天出现同向结论说明是领域共识"）。这是全页最有说服力的一句，不要省。
- 首屏预算：1440×900 内必须看到第一排卡片封面 —— hero 与面板的 padding/字号已经压过一档，不要再放大。

## 六、单篇布局

```css
#detail{position:fixed;inset:0;z-index:60;overflow-y:auto;
  opacity:0;transform:translateY(30px) scale(.988);pointer-events:none;
  transition:opacity .4s cubic-bezier(.2,.7,.3,1),transform .4s ...}
body.detail #detail{opacity:1;transform:none;pointer-events:auto}
body.detail{overflow:hidden}
```

- **顶栏**：`position:sticky;top:0`，毛玻璃，`padding:12px clamp(20px,3.2vw,60px)`（**与正文同一 clamp**，按钮才对得齐正文边缘）；底部 `.tprog` 2px 滚动进度条。
- **内容宽**：`.dwrap{max-width:1520px;margin:0 auto;padding:0 clamp(20px,3.2vw,60px) 90px}`。
  （曾用 1120px，用户反馈"太窄"改为 1520px。**不要退回窄版**。）
- **hero**：`.dh-num` 衬线 64px（巨号 `01`，`--ink4`）在左，右侧路线药丸 + 衬线 31px 短名 + 15px 中文标题 + 一行 `--mono` 元信息（arXiv / 日期 / 落位序位）。
- **图示**：`.dfig` 全宽毛玻璃框，图 `width:100%` + `border-bottom`，图题在 `<figcaption>`（12.5px），可选 `.fignote` 琥珀降级说明。`cursor:zoom-in` → 点击开灯箱。
- **五问**：`.qa{grid-template-columns:1fr 1fr;gap:18px}`，**显式两列**（`auto-fit` 在 1520px 下会变三列 → 五问排成 3+2、第二行留空）。
  每格毛玻璃，`h4` 前挂 10.5px 的圆形序号标签；第 5 问 `.opp` 通栏 + `#FAEEDA` 琥珀系底 + `--am-m` 编号。
- **原文**：`.srcwrap{grid-template-columns:118px 1fr;gap:52px}`。
  左列 `.srcnav` `position:sticky;top:88px`，按键 `.srcbtn` 是**纯文字**（无背景无边框），当前项靠 `border-left:2px solid var(--accent)` + 文字变深 + `font-weight:500` 标记。
  右列 `.srcbody{min-width:0}` —— **没有边框、没有背景、没有内边距、没有 max-width**：正文直接落在页面背景上，占满剩余宽度。段落 15px / `line-height:1.95`。
- **底部导航**：`.dnav` 两张毛玻璃卡（上一篇左对齐 / 下一篇右对齐），首末篇 `disabled` 并写"已是第一篇"。

## 七、动效与无障碍

| 元素 | 动效 |
|---|---|
| 卡片 | **无入场动画**（即显）；hover `translateY(-5px)` + 阴影加深 |
| 单篇进入 | 整体 `opacity 0→1` + `translateY(30px)→0` + `scale(.988)→1`，400ms |
| 分节入场 | `.qasec` / `.srcsec` 用 `riseIn .5s`，延迟 `0.08 + i*0.06` 错峰；重开时先置 `animation:none` 再 `void offsetWidth` 强制重放 |
| 原文切换 | `fadeUp .3s`（`translateY(7px)`） |
| 灯箱 | `fadeIn .22s` |

```css
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
```

**这不是可选项**：无头截图验证依赖它（无头 Chrome 不推进 CSS 动画），同时也是无障碍降级路径。

## 八、响应式

```css
@media (max-width:820px){
  .dh{flex-direction:column}  .dh-num{font-size:46px}  .dh h2{font-size:24px}
  .qa{grid-template-columns:1fr;gap:14px}
  .srcwrap{grid-template-columns:1fr;gap:16px}
  .srcnav{position:static;flex-direction:row;flex-wrap:wrap}
  .srcbtn{border-left:none;border-bottom:2px solid transparent}   /* 竖线换成下划线 */
  .srcbtn.on{border-bottom-color:var(--accent)}
  .hero h1{font-size:26px}
}
```

## 九、体积预算（单文件 ≤1.2 MB）

| 资源 | 规格 | 单张 |
|---|---|---|
| 单篇大图 | 1900px 上限、256 色 palette PNG | 16–97 KB |
| 卡片封面 | 560px JPEG q82 | 10–41 KB |
| 卡片模糊底衬 | 56px JPEG q45 | 0.3–0.7 KB |

全尺寸图**只内嵌一次**（单篇页），卡片用中/小图，10 篇规模实测 1.11 MB、30 个 data URI。
