# 示例原始数据

每种文件代表一种常见的数据格式，用于演示不同的解析思路。

| 文件 | 格式特征 |
|---|---|
| `irregular_vocab_01.txt` | 混合格式：破折号分隔、缩进、冒号分隔 |
| `irregular_vocab_02.txt` | 制表符分隔的多列数据 |
| `irregular_vocab_03.txt` | 编号列表 + 分类标签 |
| `irregular_vocab_04.txt` | 缩进层级结构（词典式） |
| `vocabulary_01.txt` | 简单制表符 2 列 |
| `vocabulary_02.txt` | 简单制表符 2 列 |

## 在线数据源

以下数据可通过 `kc fetch` 在线获取，不随仓库分发：

| 命令 | 说明 |
|---|---|
| `kc fetch cet4` | CET-4 高频词汇 |
| `kc fetch cet6` | CET-6 词汇 |
| `kc fetch ielts` | IELTS 核心词汇 |
| `kc fetch gaokao-history` | 高考历史真题 |
| `kc fetch gaokao-geography` | 高考地理真题 |

## 输出格式

所有示例脚本都输出忆哒批量生成碎片格式：

```
{{字段1}}{{字段2}}▮{{字段1}}{{字段2}}▮...
```

**示例输出：**
```
{{abandon}}{{v. 放弃；抛弃}}▮{{abstract}}{{adj. 抽象的；n. 摘要}}▮{{achieve}}{{v. 实现；达到}}
```
