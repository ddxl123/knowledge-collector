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

## 核心理念

**没有万能解析器。** 收到数据后，先分析格式特征，再选择合适的方式处理：

| 数据类型 | 处理方式 | 特点 |
|---|---|---|
| 结构化数据 | 写 Python 解析脚本 | 快速、可复现 |
| 半结构化/复杂数据 | AI 辅助提取 + 脚本转换 | 灵活、兜底 |
| 非结构化数据 | AI 直接提取并生成忆哒格式 | 无需脚本 |

判断顺序：先看前 10 行 → 有统一分隔符/缩进/编号？→ 用脚本解析 → 格式不规则？→ AI 辅助 → 纯文本段落？→ AI 直接生成。

## 快速参考

**CLI 统一入口**（推荐）:
```bash
python3 {baseDir}/scripts/kc.py parse data.txt --format tab -o out.txt
python3 {baseDir}/scripts/kc.py validate out.txt --fields 2
python3 {baseDir}/scripts/kc.py batch ./raw_data/ -o ./output/
python3 {baseDir}/scripts/kc.py fetch cet4 -o cet4.txt
python3 {baseDir}/scripts/kc.py stats out.txt
python3 {baseDir}/scripts/kc.py clean broken.txt -o fixed.txt
```

## 工作流程

```
Step 1 需求确认 → Step 2 收集数据 → Step 3 解析转换 → Step 4 验证输出 → Step 5 交付
```

### Step 1: 需求确认

**不要直接开始收集。先明确需求。**

按顺序提问（已知信息跳过）：
1. **收集什么？** 学科/领域、内容类型、大概数量
2. **数据从哪来？** 已有文件 / 网络搜索 / 指定数据源
3. **版权确认** 根据风险等级提示用户（见版权章节）

**进入 Step 2 的条件：** 知道收集什么 + 知道数据来源 + 用户已确认版权

### Step 2: 收集数据

**核心原则：想尽一切办法，多源交叉验证，不轻易放弃。**

#### 优先级 1: 用户已有文件
```bash
# 直接解析用户文件
python3 {baseDir}/scripts/kc.py parse 用户文件.txt -o output.txt
```

#### 优先级 2: 预置在线数据源
```bash
# 四级词汇（自动获取）
python3 {baseDir}/scripts/kc.py fetch cet4 -o cet4.txt
# 高考历史真题
python3 {baseDir}/scripts/kc.py fetch gaokao-history -o gaokao_history.txt
```

#### 优先级 3: GitHub 开源数据集
```bash
gh search repos "关键词" --sort stars --limit 10 --json fullName,description
gh api repos/owner/repo/contents/ --jq '.[].name'
gh api repos/owner/repo/contents/path --jq '.content' | base64 -d > local.txt
gh search code "关键词" --repo owner/repo --json path
gh release download v1.0 --repo owner/repo --pattern '*.csv'
```

**搜索策略：** 先英文 → 再中文 → 按 stars 排序 → 检查 LICENSE → 找数据文件

#### 优先级 4: 网络搜索
使用 `web_search` + `web_fetch`。当内容为空或不完整时（JS 渲染），切换到 `browser` 工具。

#### 优先级 5: 浏览器自动化
```
browser(action="open", url="URL", label="data")
browser(action="snapshot", targetId="data", refs="aria")
browser(action="act", targetId="data", kind="click", ref="axN")      # 翻页/展开
browser(action="act", targetId="data", kind="fill", ref="axN", text="关键词")  # 搜索
browser(action="act", targetId="data", kind="evaluate", fn="document.querySelector('.content').innerText")  # 提取
```

#### 优先级 6: PDF/图片（需确认 skill 已安装）
- PDF → `pdf-text-extractor` skill
- 图片/扫描件 → `opencr-skill` (OpenOCR)

### Step 3: 解析转换

先看前 10 行，判断数据类型，再选择处理方式：

#### 结构化数据 → 脚本解析

| 特征 | 格式 | 命令 |
|---|---|---|
| `word - meaning` | 破折号 | `--format dash` |
| `word<TAB>meaning` | 制表符 | `--format tab` |
| `word,meaning` | CSV | `--format csv` |
| `[{"word":...}]` | JSON | `--format json` |
| `| word | meaning |` | Markdown | `--format markdown` |
| `1. word meaning` | 编号列表 | `--format numbered` |
| 缩进层级 | 词典式 | `--format indent` |
| 不确定 | 自动检测 | `--format auto`（默认） |

```bash
python3 {baseDir}/scripts/kc.py parse data.txt --format tab -o output.txt
python3 {baseDir}/scripts/kc.py parse data.csv --fields word,meaning -o output.txt
python3 {baseDir}/scripts/kc.py parse data.json --fields title,content,answer -o output.txt
```

#### 半结构化/复杂数据 → AI 辅助 + 脚本转换

格式不规则但有规律时，让 AI 先提取为 JSON，再用脚本转为忆哒格式：

```python
import sys, os
sys.path.insert(0, "{baseDir}/scripts")
from yida_utils import to_yida, validate, write_output

# AI 已提取为 items 列表
items = [{"word": "abandon", "meaning": "v. 放弃"}, ...]
yida = to_yida(items, ["word", "meaning"])
ok, errs = validate(yida)
write_output(yida, "output.txt")
```

#### 非结构化数据 → AI 直接生成

纯文本/段落/文章，让 AI 直接从内容中提取知识点并输出忆哒格式字符串。

**yida_utils.py 函数速查**：

| 函数 | 说明 |
|---|---|
| `to_yida(items, field_names)` | dict 列表 → 忆哒格式 |
| `validate(yida_str, expected_fields)` | 验证格式，返回 (bool, errors) |
| `auto_parse(content, hint)` | 自动检测格式并解析 |
| `read_input(path)` | 读文件（自动检测编码） |
| `write_output(content, path)` | 写文件 + 打印预览 |
| `dedup(items, key_fields)` | 去重 |
| `clean_field(value)` | 清洗字段值 |
| `merge(*item_lists)` | 合并多个数据源 |

### Step 4: 验证输出

**必须执行的检查**：
```bash
python3 {baseDir}/scripts/kc.py validate output.txt --fields 2
python3 {baseDir}/scripts/kc.py stats output.txt
```

验证清单：
- [ ] 字段数一致
- [ ] 括号匹配（`{{` `}}`）
- [ ] 无空字段
- [ ] 无非法字符（字段值中无 `{{` `}}` `▮`）
- [ ] 分隔符正确（知识点间 `▮`）
- [ ] 内容准确（抽样检查）

**修复问题**：
```bash
python3 {baseDir}/scripts/kc.py clean output.txt -o fixed.txt
```

### Step 5: 交付

| 方式 | 说明 |
|---|---|
| 单文件 | 所有结果写入一个 `.txt` 文件 |
| 多文件 | 按类别写入多个文件 |
| 直接打印 | 小量数据输出到 stdout |

**命名规范**：`{主题}_忆哒格式.txt` 或 `{主题}_{类别}.txt`

## 忆哒格式规范

```
{{字段1}}{{字段2}}{{字段3}}▮{{字段1}}{{字段2}}{{字段3}}
```

- 每个字段用 `{{` `}}` 包裹，知识点间用 `▮` 分隔
- 同一批次字段数量和顺序必须一致
- 字段值中不能包含 `{{` `}}` `▮`

| 内容类型 | 推荐字段 | 示例 |
|---|---|---|
| 词汇 | word, meaning | `{{abandon}}{{v. 放弃}}` |
| 词汇+音标 | word, phonetic, meaning | `{{abandon}}{{əˈbændən}}{{v. 放弃}}` |
| 选择题 | title, content, answer | `{{#1}}{{题目...}}{{A}}` |
| 知识卡片 | question, answer, tags | `{{什么是光合作用}}{{...}}{{生物}}` |

## 批量处理

```bash
# 处理目录下所有文件
python3 {baseDir}/scripts/kc.py batch ./raw_data/ -o ./output/
# 处理指定文件
python3 {baseDir}/scripts/kc.py batch file1.txt file2.csv -o ./output/
# 强制指定格式
python3 {baseDir}/scripts/kc.py batch ./data/ --format tab -o ./out/
```

## 依赖自检

**在 Step 1 开始前执行。** 缺失的 skill 按需安装（不会用到的跳过）。

```bash
REQUIRED_SKILLS=("pdf-text-extractor" "opencr-skill" "education")
SKILLS_DIR="$HOME/.openclaw/workspace/skills"
for skill in "${REQUIRED_SKILLS[@]}"; do
  if [ -d "$SKILLS_DIR/$skill" ] && [ -f "$SKILLS_DIR/$skill/SKILL.md" ]; then
    echo "✅ $skill"
  else
    echo "⏳ 缺失 $skill，正在安装..."
    openclaw skills install "$skill"
    if [ -d "$SKILLS_DIR/$skill" ] && [ -f "$SKILLS_DIR/$skill/SKILL.md" ]; then
      echo "✅ $skill 安装成功"
    else
      echo "❌ $skill 安装失败，请手动安装: openclaw skills install $skill"
    fi
  fi
done
```

## 错误恢复

| 问题 | 恢复策略 |
|---|---|
| `web_fetch` 返回空/不完整 | 切换 `browser` 工具 |
| GitHub CDN 超时 | 换 raw.githubusercontent.com 或 gh api 直接下载 |
| 编码问题（乱码） | `read_input()` 自动检测编码，支持 UTF-8/GBK/GB18030 |
| 格式解析失败 | 换 `--format` 参数，或用 AI 辅助提取 |
| 去重后数量不足 | 扩大搜索范围，增加关键词变体 |
| OCR 识别率低 | 尝试更高分辨率图片，或换 OCR 引擎 |
| 字段值含特殊字符 | `kc.py clean` 自动修复 |

## 缓存策略

- 已下载的原始数据存入 `raw_data/` 目录
- 重复请求同一数据源时，先检查 `raw_data/` 是否已有
- 避免对同一 URL 重复请求

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

**提示模板：**

> ⚠️ 版权风险提示：该内容属于受版权保护的资料（来源：xxx）。收集后仅供个人学习使用，严禁商业用途和公开传播。是否继续？

详见 `{baseDir}/docs/copyright-guide.md`。

## Step 7（可选）: 生成学习材料

用 `education` skill 生成配套材料。

```bash
bash {educationSkillDir}/scripts/script.sh plan "英语四级词汇" --weeks 4
bash {educationSkillDir}/scripts/script.sh quiz "英语四级高频词汇" --count 20 --type mcq
bash {educationSkillDir}/scripts/script.sh flashcard "光合作用" --count 30 --format csv
```

## 处理 Checklist

1. ✅ 需求确认（收集什么、从哪来、版权确认）
2. ✅ PDF？→ `pdf-text-extractor`；图片？→ OpenOCR
3. ✅ 检查预置数据源 `kc.py fetch`
4. ✅ `gh` CLI 搜索 GitHub 开源数据集
5. ✅ `web_search` + `web_fetch` 网络搜索
6. ✅ 内容不完整？→ `browser` 工具自动化
7. ✅ `kc.py parse` 转换为忆哒格式
8. ✅ `kc.py validate` + `kc.py stats` 验证
9. ✅ 保存到文件
10. ✅（可选）用 `education` skill 生成学习材料
