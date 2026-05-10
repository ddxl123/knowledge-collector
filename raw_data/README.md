# 示例原始数据

每种文件代表一种数据格式 + 学科领域，用于演示不同的解析思路。

## 英语词汇（原有）

| 文件 | 格式 |
|---|---|
| `irregular_vocab_01.txt` | 混合：破折号、缩进、冒号 |
| `irregular_vocab_02.txt` | 制表符多列 |
| `irregular_vocab_03.txt` | 编号列表 |
| `irregular_vocab_04.txt` | 缩进层级 |
| `vocabulary_01.txt` | 制表符 2 列 |
| `vocabulary_02.txt` | 制表符 2 列 |

## 其他学科（新增）

| 文件 | 学科 | 格式 |
|---|---|---|
| `chinese_history.txt` | 中国历史 | 破折号分隔 |
| `biology_concepts.csv` | 生物 | CSV 表格 |
| `physics_formulas.txt` | 物理 | 编号列表 |
| `geography_capitals.md` | 地理 | Markdown 表格 |
| `math_theorems.txt` | 数学 | 缩进层级 |
| `chemistry_elements.json` | 化学 | JSON 数组 |

## 输出格式

```
{{字段1}}{{字段2}}▮{{字段1}}{{字段2}}▮...
```
