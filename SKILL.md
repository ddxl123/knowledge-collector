---
name: knowledge-collector
description: 为忆哒学习应用收集各领域/学科的学习资料。通过逐步提问明确用户需求后，深入挖掘所有可能的数据来源进行收集和格式转换。输出字段由忆哒App模板决定，无需用户指定。严格遵循版权规范。
license: MIT
metadata:
  {
    "openclaw": {
      "requires": { "bins": ["python3"] },
      "integrates": ["github", "browser-automation", "pdf-text-extractor", "opencr-skill", "education"],
      "emoji": "📚"
    }
  }
---

# knowledge-collector

为忆哒学习应用收集学习资料，转换为忆哒批量生成碎片格式。

## 快速启动

收到请求后，按顺序执行 7 个步骤。每个步骤有明确的进入/退出条件。

```
Step 1 需求确认 → Step 2 收集数据 → Step 3 分析格式 → Step 4 处理数据 → Step 5 验证 → Step 6 输出 → Step 7(可选) 生成学习材料
```

## 依赖自检（首次运行前）

```bash
REQUIRED_SKILLS=("pdf-text-extractor" "opencr-skill" "education")
SKILLS_DIR="$HOME/.openclaw/workspace/skills"
for skill in "${REQUIRED_SKILLS[@]}"; do
  [ -d "$SKILLS_DIR/$skill" ] && [ -f "$SKILLS_DIR/$skill/SKILL.md" ] && echo "✅ $skill" || { echo "⏳ 安装 $skill..."; openclaw skills install "$skill"; }
done
```

## 忆哒格式规范

```
{{字段1}}{{字段2}}{{字段3}}▮{{字段1}}{{字段2}}{{字段3}}
```

- 每个字段用 `{{` `}}` 包裹，知识点间用 `▮` 分隔
- 同一批次字段数量和顺序必须一致
- 字段值中不能包含 `{{` `}}` `▮`（需提前清理）

| 内容类型 | 推荐字段 | 示例 |
|---|---|---|
| 词汇 | word, meaning | `{{abandon}}{{v. 放弃}}` |
| 词汇+音标 | word, phonetic, meaning | `{{abandon}}{{əˈbændən}}{{v. 放弃}}` |
| 选择题 | title, content, answer | `{{#1}}{{题目...}}{{A}}` |
| 知识卡片 | question, answer, tags | `{{什么是光合作用}}{{...}}{{生物}}` |

## Step 1: 需求确认

**不要直接开始收集。先明确需求。**

按顺序提问（已知信息跳过）：
1. **收集什么？** 学科/领域、内容类型、大概数量
2. **数据从哪来？** 已有文件 / 网络搜索 / 指定数据源
3. **版权确认** 根据风险等级提示用户（见版权章节）

**提问原则：** 每次 1-2 个问题，根据回答动态调整。

**进入 Step 2 的条件：**
- ✅ 知道收集什么（学科、类型、数量）
- ✅ 知道数据来源（文件路径 / URL / 搜索关键词）
- ✅ 用户已确认版权提示

## Step 2: 收集数据

**核心：想尽一切办法，深入挖掘所有可能的数据来源。不满足于第一个结果，多源交叉验证。**

### 收集策略（按优先级）

| 优先级 | 策略 | 工具 | 适用场景 |
|---|---|---|---|
| 1 | 开源数据集 | `gh` CLI | GitHub 词汇表、题库、数据集 |
| 2 | 网络搜索 | `web_search` + `web_fetch` | 通用搜索 |
| 3 | 结构化数据源 | API / `web_fetch` | 维基百科、在线词典、考试官网 |
| 4 | 用户数据 | `read` | 用户提供的文件/文本 |
| 5 | 浏览器自动化 | `browser` | JS 渲染页面、需翻页/交互 |
| 6 | PDF 文档 | `pdf-text-extractor` | 教材 PDF、扫描件（自动 OCR） |
| 7 | 图片/扫描件 | `opencr-skill` | 拍照笔记、扫描试卷、公式/表格 |
| 8 | 深度挖掘 | `browser` console + 多源拼接 | 以上都不够时 |

### GitHub 搜索速查

```bash
gh search repos "关键词" --sort stars --limit 10 --json fullName,description,stargazersCount
gh api repos/owner/repo/contents/ --jq '.[].name'
gh api repos/owner/repo/contents/path --jq '.content' | base64 -d > local.txt
gh search code "关键词" --repo owner/repo --json path
gh release download v1.0 --repo owner/repo --pattern '*.csv'
```

**搜索策略：** 先英文关键词 → 再中文关键词 → 按 stars 排序 → 检查 LICENSE → 找数据文件（`.txt` `.csv` `.json` `.md`）

### 浏览器自动化

当 `web_fetch` 返回内容为空或不完整时（JS 渲染、需交互），切换到 `browser`：

```
browser(action="open", url="URL", label="data")
browser(action="snapshot", targetId="data", refs="aria")
browser(action="act", targetId="data", kind="click", ref="axN")      # 翻页/展开
browser(action="act", targetId="data", kind="fill", ref="axN", text="关键词")  # 搜索
browser(action="act", targetId="data", kind="evaluate", fn="document.querySelector('.content').innerText")  # 提取
```

### 收集原则

- **不轻易放弃**：一个来源找不到就换关键词、换平台、换语言
- **多源验证**：同一数据尽量从 2+ 来源交叉验证
- **主动补全**：某来源数据不完整时，从其他来源补充
- **数量达标**：达到或超过用户要求的数量

## Step 3: 分析格式 → 决策树

```
高度结构化？
├─ 有明确分隔符（制表符/破折号/冒号/竖线）
│   → parse_dash.py / parse_tab.py / parse_csv.py / yida_utils.parse_delimited()
├─ 缩进层级
│   → parse_indent.py / yida_utils.parse_indented()
├─ 编号列表
│   → parse_numbered.py
├─ JSON/JSONL
│   → parse_json.py
├─ CSV
│   → parse_csv.py
├─ Markdown 表格
│   → parse_markdown.py
├─ HTML 表格
│   → BeautifulSoup 或正则提取
│
├─ 半结构化（有规律但不一致）
│   → AI 辅助提取 JSON → to_yida() 转换
│
└─ 非结构化（自由文本）
    → AI 直接提取知识点 → 生成忆哒格式
```

**快速识别：** 看前 10 行——有统一分隔符？有缩进？有编号？是 JSON/CSV/HTML？

## Step 4: 处理数据

### 方式 A: 脚本解析（推荐，可复现）

```python
import sys, os
sys.path.insert(0, "{baseDir}/scripts")
from yida_utils import to_yida, validate, read_input, write_output

content = read_input("input.txt")
# ... 解析逻辑 ...
yida = to_yida(items, ["field1", "field2"])
ok, errs = validate(yida)
write_output(yida, "output.txt")
```

**yida_utils.py 函数速查：**

| 函数 | 说明 |
|---|---|
| `to_yida(items, field_names)` | dict 列表 → 忆哒格式字符串 |
| `validate(yida_str, expected_fields)` | 验证格式，返回 (bool, errors) |
| `read_input(path)` | 读文件（支持路径或 stdin） |
| `write_output(content, path)` | 写文件 + 打印预览 |
| `parse_delimited(content, sep)` | 通用分隔符解析 |
| `parse_numbered_list(content)` | 编号列表解析 |
| `parse_key_value(content)` | 键值对解析 |
| `parse_indented(content)` | 缩进层级解析 |
| `dedup(items, key_fields)` | 去重（按指定字段） |
| `clean_field(value)` | 清洗字段值（去除 `{{` `}}` `▮`） |
| `merge(*item_lists)` | 合并多个数据源 |
| `auto_parse(content, hint=None)` | 自动检测格式并解析 |
| `print_stats(items, extra)` | 打印解析统计 |

### 方式 B: AI 辅助（复杂格式）

1. AI 提取为 JSON → 2. `to_yida()` 转换

### 方式 C: AI 直接生成（非结构化）

让 AI 从段落/文章中直接输出忆哒格式。

## Step 5: 验证输出

**必须执行的检查清单：**
- [ ] 字段数一致（每个知识点字段数量相同）
- [ ] 括号匹配（每个 `{{` 有对应 `}}`）
- [ ] 无空字段
- [ ] 无非法字符（字段值中无 `{{` `}}` `▮`）
- [ ] 分隔符正确（知识点间 `▮`）
- [ ] 内容准确（抽样检查几条）

```bash
# 独立验证 CLI
python3 {baseDir}/scripts/validate.py output.txt
python3 {baseDir}/scripts/validate.py output.txt --fields 2  # 指定期望字段数
```

## Step 6: 输出

| 方式 | 说明 |
|---|---|
| 单文件 | 所有结果写入一个 `.txt` 文件 |
| 多文件 | 按类别/分组写入多个文件 |
| 直接打印 | 小量数据输出到 stdout |

**命名规范：** `{主题}_忆哒格式.txt` 或 `{主题}_{类别}.txt`

## Step 7（可选）: 生成学习材料

用 `education` skill 生成配套材料：

```bash
bash {educationSkillDir}/scripts/script.sh plan "英语四级词汇" --weeks 4
bash {educationSkillDir}/scripts/script.sh quiz "英语四级高频词汇" --count 20 --type mcq
bash {educationSkillDir}/scripts/script.sh flashcard "光合作用" --count 30 --format csv
```

## 批量处理

当有多个文件需要处理时，使用 `batch.py`：

```bash
python3 {baseDir}/scripts/batch.py ./raw_data/ -o ./output/
python3 {baseDir}/scripts/batch.py ./raw_data/ --format tab -o ./output/
python3 {baseDir}/scripts/batch.py file1.txt file2.csv file3.json -o ./output/
```

## 示例脚本

`{baseDir}/scripts/` 下的解析脚本：

| 脚本 | 格式特征 | 运行方式 |
|---|---|---|
| `parse_dash.py` | `word - meaning` 破折号分隔 | `python3 scripts/parse_dash.py data.txt` |
| `parse_tab.py` | 制表符分隔多列 | `python3 scripts/parse_tab.py data.txt` |
| `parse_indent.py` | 缩进层级结构 | `python3 scripts/parse_indent.py data.txt` |
| `parse_numbered.py` | 编号列表 `1. word meaning` | `python3 scripts/parse_numbered.py data.txt` |
| `parse_csv.py` | CSV（自动检测分隔符） | `python3 scripts/parse_csv.py data.csv --fields word,meaning` |
| `parse_json.py` | JSON / JSONL | `python3 scripts/parse_json.py data.json --fields word,meaning` |
| `parse_markdown.py` | Markdown 表格 | `python3 scripts/parse_markdown.py data.md` |
| `parse_cet4.py` | 四级词汇表（在线获取） | `python3 scripts/parse_cet4.py` |
| `parse_gaokao_history.py` | 高考历史选择题（在线获取） | `python3 scripts/parse_gaokao_history.py` |
| `batch.py` | 批量处理多个文件 | `python3 scripts/batch.py ./raw_data/ -o ./output/` |
| `validate.py` | 独立验证 CLI | `python3 scripts/validate.py output.txt` |

所有脚本支持 `-o output.txt` 参数保存到文件。

## 错误恢复

| 问题 | 恢复策略 |
|---|---|
| `web_fetch` 返回空/不完整 | 切换 `browser` 工具 |
| GitHub CDN 超时 | 换 raw.githubusercontent.com 或 gh api 直接下载 |
| 格式解析失败 | 降低 `parse_delimited` 的 `min_cols`，或切换 AI 辅助 |
| 去重后数量不足 | 扩大搜索范围，增加关键词变体 |
| OCR 识别率低 | 尝试更高分辨率图片，或换 OCR 引擎 |
| 字段值含特殊字符 | `clean_field()` 自动清理 |

## 缓存策略

- 已下载的原始数据存入 `raw_data/` 目录
- 重复请求同一数据源时，先检查 `raw_data/` 是否已有
- 在线获取的脚本（如 `parse_cet4.py`）默认输出到 `raw_data/`
- 避免对同一 URL 重复请求（浪费带宽 + 可能触发限流）

## 版权合规

**所有版权风险等级的内容均可收集，但需根据风险等级提示用户。**

| 级别 | 说明 | 提示方式 |
|---|---|---|
| 🟢 低风险 | 公共领域、开放许可、事实性数据 | 直接收集 |
| 🟡 中风险 | 网站原创内容、用户生成内容 | 提示使用条款，建议仅供个人学习 |
| 🔴 高风险 | 整本教材、付费课程、官方题库 | ⚠️ 强烈提示，用户确认后继续 |

**合规原则：**
- 优先开放许可资源（CC0、CC-BY、公共领域）
- 完整记录来源（URL、作者、日期）
- 仅供个人学习使用
- 如需商业使用，请获取授权

**提示模板：**

> ⚠️ 版权风险提示：该内容属于受版权保护的资料（来源：xxx）。收集后仅供个人学习使用，严禁商业用途和公开传播。是否继续？

详见 `{baseDir}/docs/copyright-guide.md`。

## 处理 Checklist

1. ✅ 需求确认（收集什么、从哪来、版权确认）
2. ✅ PDF？→ `pdf-text-extractor`；图片？→ OpenOCR
3. ✅ `gh` CLI 搜索 GitHub 开源数据集
4. ✅ `web_search` + `web_fetch` 网络搜索
5. ✅ 内容不完整？→ `browser` 工具自动化
6. ✅ 多源交叉验证，补全缺失数据
7. ✅ 看前 10 行，识别格式 → 选择解析方式
8. ✅ 运行解析脚本 + `validate.py` 验证
9. ✅ 抽样检查内容准确性
10. ✅ 保存到文件
11. ✅（可选）用 `education` skill 生成学习材料
