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

**判断数据类型**（看前 10 行）：
- 有统一分隔符/编号/缩进？ → `kc parse --format <格式>`
- 格式不规则但有规律？ → AI 先提取为 JSON → `kc parse`
- 纯文本段落？ → AI 直接生成忆哒格式

### 4. 验证（必须）

```bash
kc validate output.txt --fields N
kc stats output.txt
```

### 5. 交付

**输出到用户指定的位置。** 命名：`{主题}_忆哒格式.txt`

```bash
# 示例：用户要求放桌面
kc fetch cet4 -o ~/Desktop/CET4词汇_忆哒格式.txt
kc parse data.txt -o ~/Desktop/高考历史_忆哒格式.txt
kc batch ./raw_data/ -o ~/Desktop/忆哒输出/
```

---

## CLI 参考

```bash
kc parse data.txt --format tab -o ~/Desktop/out.txt        # 解析
kc parse data.txt --map old1:new1,old2:new2 -o ~/Desktop/out.txt  # 解析+重命名字段
kc parse data.txt --filter "tag=高考" -o ~/Desktop/out.txt  # 解析+过滤
kc validate out.txt --fields 2                               # 验证
kc batch ./raw_data/ -o ~/Desktop/忆哒输出/                   # 批量
kc fetch cet4 -o ~/Desktop/CET4词汇_忆哒格式.txt              # 获取预置数据源
kc stats out.txt                                             # 统计
kc clean broken.txt -o fixed.txt                             # 清洗修复
kc convert data.txt --map word:vocab,meaning:def -o out.txt  # 转换字段名
kc merge a.txt b.txt -o merged.txt                           # 合并多个文件
kc preview out.txt --limit 5                                 # 预览
```

**格式参数** `--format`: `auto`(默认), `csv`, `json`, `tab`, `dash`, `markdown`, `numbered`, `indent`

**过滤表达式** `--filter`: `field=value` / `field!=value` / `field~=regex`

**预置数据源** `kc fetch`: `cet4`, `cet6`, `ielts`, `gaokao-history`, `gaokao-geography`

---

## 忆哒格式规范

```
{{字段1}}{{字段2}}▮{{字段1}}{{字段2}}
```

- 字段用 `{{` `}}` 包裹，知识点间 `▮` 分隔
- 同批次字段数和顺序必须一致
- 字段值内禁止 `{{` `}}` `▮`

| 内容类型 | 推荐字段 |
|---|---|
| 词汇 | word, meaning |
| 词汇+音标 | word, phonetic, meaning |
| 选择题 | title, content, answer |
| 知识卡片 | question, answer, tags |

---

## Python API（高级用法）

```python
import sys; sys.path.insert(0, "{baseDir}/scripts")
from yida_utils import to_yida, validate, write_output, auto_parse
from yida_utils import dedup, clean_field, merge, convert_fields, filter_items
from yida_utils import retry_fetch, batch_process

# AI 提取为 items 后转换
items = [{"word": "abandon", "meaning": "v. 放弃"}, ...]
yida = to_yida(items, ["word", "meaning"])
ok, errs = validate(yida, expected_fields=2)
write_output(yida, "output.txt")
```

---

## 错误恢复

| 问题 | 策略 |
|---|---|
| `web_fetch` 返回空/不完整 | 切换 `browser` 工具 |
| GitHub CDN 超时 | `retry_fetch()` 自动重试 3 次 |
| 编码乱码 | `read_input()` 自动检测 UTF-8/GBK/GB18030 |
| 格式解析失败 | 换 `--format` 或 AI 辅助 |
| 字段值含特殊字符 | `kc clean` 自动修复 |

## 版权合规

所有风险等级均可收集，根据等级提示用户后继续。

| 级别 | 说明 | 动作 |
|---|---|---|
| 🟢 低 | 公共领域、开放许可、事实数据 | 直接收集 |
| 🟡 中 | 网站原创、用户生成内容 | 提示使用条款 |
| 🔴 高 | 整本教材、付费课程、官方题库 | ⚠️ 强烈提示，用户确认后继续 |

> ⚠️ 提示模板：该内容受版权保护（来源：xxx）。仅供个人学习，严禁商用和传播。是否继续？

优先开放许可资源（CC0/CC-BY/公共领域）。记录来源（URL/作者/日期）。

详见 `{baseDir}/docs/copyright-guide.md`。

---

## 依赖自检

用到时再检查，不用的跳过：

```bash
for skill in pdf-text-extractor opencr-skill education; do
  [ -d "$HOME/.openclaw/workspace/skills/$skill" ] && echo "✅ $skill" || echo "⏳ 缺失: $skill"
done
```
