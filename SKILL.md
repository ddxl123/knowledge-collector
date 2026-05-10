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

**CLI 入口：** `{baseDir}/scripts/kc.py`（快捷方式 `{baseDir}/kc`）

## 工作流程

```
需求确认 → 收集数据 → 解析转换 → 验证 → 交付
```

### 1. 需求确认

**先问再做。** 已知信息跳过。按顺序确认：
1. 收集什么（学科、内容类型、数量）
2. 数据来源（已有文件 / 网络 / 指定数据源）
3. **输出位置**（用户必须明确指定，例如：桌面、下载文件夹、某个项目目录）
4. 版权确认（见末尾版权章节）

**输出路径规则：**
- 用户说「桌面」→ `~/Desktop/`
- 用户说「下载」→ `~/Downloads/`
- 用户给了具体路径 → 直接使用
- 用户未指定 → **必须询问**，不要自行假设

### 2. 收集数据（优先级从高到低）

| 优先级 | 来源 | 方法 |
|---|---|---|
| 1 | 用户已有文件 | 直接 `kc parse` |
| 2 | 预置数据源 | `kc fetch cet4` |
| 3 | GitHub 数据集 | `gh search repos/code` → 下载 |
| 4 | 网络搜索 | `web_search` + `web_fetch` |
| 5 | JS 渲染页面 | `browser` 工具自动化 |
| 6 | PDF/图片 | `pdf-text-extractor` / `opencr-skill` |

### 3. 解析转换

根据数据类型选择处理方式（看前 10 行判断）：

**脚本直接解析：** 有统一分隔符/编号/缩进 → `kc parse --format <格式>`

**脚本+AI结合：** 有结构化元数据但正文不规则 → 脚本拆分结构，AI 提取正文知识点

**AI 辅助：** 格式不规则但有规律 → AI 先提取为 dict 列表 → `to_yida()` 转换

**AI 直接生成：** 纯文本段落 → AI 提取知识点并生成忆哒格式字符串

### 4. 验证（必须）

```bash
python3 {baseDir}/scripts/kc.py validate output.txt --fields N
python3 {baseDir}/scripts/kc.py stats output.txt
```

### 5. 交付

**输出到用户指定的位置。** 命名：`{主题}_忆哒格式.txt`

```bash
python3 {baseDir}/scripts/kc.py fetch cet4 -o ~/Desktop/CET4词汇_忆哒格式.txt
python3 {baseDir}/scripts/kc.py parse data.txt -o ~/Desktop/高考历史_忆哒格式.txt
python3 {baseDir}/scripts/kc.py batch ./raw_data/ -o ~/Desktop/忆哒输出/
```

---

## CLI 参考

```bash
python3 {baseDir}/scripts/kc.py parse data.txt --format tab -o out.txt
python3 {baseDir}/scripts/kc.py parse data.txt --map old1:new1 -o out.txt
python3 {baseDir}/scripts/kc.py parse data.txt --filter "tag=高考" -o out.txt
python3 {baseDir}/scripts/kc.py validate out.txt --fields 2
python3 {baseDir}/scripts/kc.py batch ./raw_data/ -o ./output/
python3 {baseDir}/scripts/kc.py fetch cet4 -o out.txt
python3 {baseDir}/scripts/kc.py stats out.txt
python3 {baseDir}/scripts/kc.py clean broken.txt -o fixed.txt
python3 {baseDir}/scripts/kc.py convert data.txt --map word:vocab -o out.txt
python3 {baseDir}/scripts/kc.py merge a.txt b.txt -o merged.txt
python3 {baseDir}/scripts/kc.py preview out.txt --limit 5
```

**格式** `--format`: `auto`(默认) `csv` `json` `tab` `dash` `markdown` `numbered` `indent`

**过滤** `--filter`: `field=value` / `field!=value` / `field~=regex`

**数据源** `kc fetch`: `cet4` `cet6` `ielts` `gaokao-history` `gaokao-geography`

---

## 忆哒格式规范

```
{{字段1}}{{字段2}}▮{{字段1}}{{字段2}}
```

- 字段用 `{{` `}}` 包裹，知识点间 `▮` 分隔
- 同批次字段数和顺序必须一致
- 字段值内禁止 `{{` `}}` `▮`

---

## Python API

```python
import sys; sys.path.insert(0, "{baseDir}/scripts")
from yida_utils import to_yida, validate, write_output, auto_parse
from yida_utils import dedup, clean_field, merge, convert_fields, filter_items
from yida_utils import retry_fetch, batch_process

# AI 提取为 items 后转忆哒格式
items = [{"word": "abandon", "meaning": "v. 放弃"}, ...]
yida = to_yida(items, ["word", "meaning"])
ok, errs = validate(yida, expected_fields=2)
write_output(yida, "output.txt")
```

---

## 错误恢复

| 问题 | 策略 |
|---|---|
| `web_fetch` 返回空 | 切换 `browser` 工具 |
| GitHub CDN 超时 | `retry_fetch()` 自动重试 3 次 |
| 编码乱码 | `read_input()` 自动检测 UTF-8/GBK/GB18030 |
| 格式解析失败 | 换 `--format` 或 AI 辅助 |
| 字段值含特殊字符 | `kc clean` 自动修复 |

## 版权合规

| 级别 | 说明 | 动作 |
|---|---|---|
| 🟢 低 | 公共领域、开放许可、事实数据 | 直接收集 |
| 🟡 中 | 网站原创、用户生成内容 | 提示使用条款 |
| 🔴 高 | 整本教材、付费课程、官方题库 | ⚠️ 强烈提示，用户确认后继续 |

> ⚠️ 提示：该内容受版权保护（来源：xxx）。仅供个人学习，严禁商用和传播。是否继续？

详见 `{baseDir}/docs/copyright-guide.md`。

---

## 依赖自检

用到时再检查，不用的跳过：

```bash
for skill in pdf-text-extractor opencr-skill education; do
  [ -d "$HOME/.openclaw/workspace/skills/$skill" ] && echo "✅ $skill" || echo "⏳ 缺失: $skill"
done
```
