# 小样本实验记录

评测集：`eval_kit/eval_set_small.json`

生成模型：本地 Ollama 上的 `qwen2.5:3b`

说明：这里记录的是本地快速指标，不是最终的 LLM-as-Judge 分数。最终报告仍需要用 `run_judge.py` 做正式打分。

## 总体结果

| 系统 | 输出文件 | 题数 | 粗略 F1 | 完全匹配 | Unknown 数 | 平均回答耗时 |
|---|---:|---:|---:|---:|---:|---:|
| 无记忆 baseline | `predictions_nomem_small.json` | 8 | 0.000 | 0.000 | 8 | 0.132s |
| 全上下文 baseline | `predictions_fullctx_small.json` | 8 | 0.105 | 0.000 | 2 | 17.362s |
| 原始对话 RAG baseline | `predictions_rag_small.json` | 8 | 0.201 | 0.000 | 2 | 0.731s |
| 追加式记忆，m=4，top-k=6 | `predictions_append_small.json` | 8 | 0.231 | 0.125 | 5 | 0.590s |
| 追加式记忆，m=4，top-k=10，混合检索 | `predictions_append_small_hybrid.json` | 8 | 0.141 | 0.000 | 5 | 0.872s |
| 追加式记忆，m=4，细节记忆，top-k=10 | `predictions_append_small_detail.json` | 8 | 0.304 | 0.000 | 4 | 1.023s |
| 更新式记忆，规则去重合并，细节记忆，top-k=10 | `predictions_update_small_rule.json` | 8 | 0.289 | 0.000 | 4 | 1.080s |
| 追加式记忆，m=8，top-k=10 | `predictions_append_small_m8.json` | 8 | 0.101 | 0.000 | 5 | 0.911s |

## 追加式记忆消融

| 配置 | 提取到的记忆数量 | 结果 |
|---|---:|---|
| `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=6` | 5 段对话共 504 条记忆 | 第一版可用结果，粗略 F1 为 0.231。 |
| `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=10`, `MEMORY_KEYWORD_WEIGHT=0.25` | 5 段对话共 504 条记忆 | 简单关键词混合检索没有提升整体效果。 |
| `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=10`, `MEMORY_DETAIL_NOTES=1` | 5 段对话共 854 条记忆 | 当前小样本最好结果，细节记忆提高了召回。 |
| `UpdateMemoryAgent`, `MEMORY_DETAIL_NOTES=1`, `MEMORY_UPDATE_USE_LLM=0` | 5 段对话共提取 854 条，最终保留 677 条 active 记忆 | 去重合并减少了 177 条重复或相近记忆，分数略低于 append-only detail。 |
| `MEMORY_PER_SESSION=8`, `MEMORY_TOP_K=10` | 5 段对话共 821 条记忆 | 单纯增加 LLM 提取条数没有帮助，可能引入了检索噪声。 |

## 按题型粗略 F1

| 系统 | 多跳问题 | 开放域问题 | 单跳问题 | 时间问题 |
|---|---:|---:|---:|---:|
| 原始对话 RAG | 0.043 | 0.222 | 0.358 | 0.182 |
| 追加式记忆，m=4 | 0.000 | 0.500 | 0.150 | 0.273 |
| 追加式记忆，m=4，混合检索 | 0.000 | 0.167 | 0.148 | 0.250 |
| 追加式记忆，m=4，细节记忆 | 0.000 | 0.182 | 0.333 | 0.701 |
| 更新式记忆，规则去重合并 | 0.000 | 0.182 | 0.296 | 0.679 |
| 追加式记忆，m=8 | 0.000 | 0.000 | 0.222 | 0.183 |

## 更新式记忆实验统计

配置：`UpdateMemoryAgent`, `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=10`, `MEMORY_DETAIL_NOTES=1`, `MEMORY_UPDATE_USE_LLM=0`

| 对话 | 提取记忆数 | 最终存储数 | Active 数 | Obsolete 数 | ADD | IGNORE | MERGE | UPDATE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `conv-26` | 129 | 99 | 99 | 0 | 99 | 0 | 30 | 0 |
| `conv-30` | 125 | 103 | 103 | 0 | 103 | 0 | 22 | 0 |
| `conv-41` | 215 | 167 | 167 | 0 | 167 | 0 | 48 | 0 |
| `conv-43` | 188 | 146 | 146 | 0 | 146 | 8 | 34 | 0 |
| `conv-50` | 197 | 162 | 162 | 0 | 162 | 0 | 35 | 0 |
| **合计** | **854** | **677** | **677** | **0** | **677** | **8** | **169** | **0** |

本轮 small set 中没有触发规则版 UPDATE，主要发生的是 MERGE 和 IGNORE。这说明当前样本里重复/相近记忆较多，但明显的新旧冲突较少。后续如果要展示冲突更新，可以开启 `MEMORY_UPDATE_USE_LLM=1`，或者在完整数据集上观察是否出现 UPDATE。

## 细节记忆实验耗时

| 对话 | Session 数 | 总记忆数 | 细节记忆数 | ingest 耗时 |
|---|---:|---:|---:|---:|
| `conv-26` | 19 | 129 | 57 | 66.1s |
| `conv-30` | 19 | 125 | 56 | 61.7s |
| `conv-41` | 32 | 215 | 96 | 104.0s |
| `conv-43` | 29 | 188 | 85 | 89.8s |
| `conv-50` | 30 | 197 | 90 | 89.6s |

## 细节记忆逐题表现

| 题目 | 类型 | 参考答案 | 模型回答 | 简要判断 |
|---|---|---|---|---|
| `conv-26_q25` | 时间 | 10 July 2023 | Two days ago, which was 10 July 2023. | 正确。 |
| `conv-30_q33` | 时间 | 20 June, 2023 | Yesterday (20 June 2023). | 正确。 |
| `conv-41_q94` | 开放域 | Salads, sandwiches, homemade desserts | Salads, sandwiches, banana split sundae, homemade desserts. | 基本正确，但多了额外细节。 |
| `conv-43_q4` | 单跳 | 一长串书名 | Harry Potter, Game of Thrones, The Hobbit, The Name of the Wind. | 部分正确，仍漏掉几本书。 |
| `conv-43_q15` | 多跳 | likely John's friend, colleague or family | unknown | 仍然失败。 |
| `conv-43_q29` | 单跳 | Middle school, high school, college; 4 years | unknown | 仍然失败。 |
| `conv-50_q39` | 多跳 | Dodge Charger | unknown | 仍然失败。 |
| `conv-50_q71` | 开放域 | A few months | unknown | 相比 m=4 基础版退步。 |

## 混合检索实验耗时

| 对话 | Session 数 | 提取记忆数 | ingest 耗时 |
|---|---:|---:|---:|
| `conv-26` | 19 | 76 | 70.0s |
| `conv-30` | 19 | 75 | 63.6s |
| `conv-41` | 32 | 127 | 104.2s |
| `conv-43` | 29 | 110 | 100.1s |
| `conv-50` | 30 | 116 | 95.2s |

## m=8 实验耗时

| 对话 | Session 数 | 提取记忆数 | ingest 耗时 |
|---|---:|---:|---:|
| `conv-26` | 19 | 127 | 94.1s |
| `conv-30` | 19 | 133 | 92.0s |
| `conv-41` | 32 | 204 | 139.7s |
| `conv-43` | 29 | 168 | 125.3s |
| `conv-50` | 30 | 189 | 128.1s |

## m=8 逐题表现

| 题目 | 类型 | 参考答案 | 模型回答 | 简要判断 |
|---|---|---|---|---|
| `conv-26_q25` | 时间 | 10 July 2023 | Caroline went to a transgender conference in July. | 部分正确，但不如 m=4 精确。 |
| `conv-30_q33` | 时间 | 20 June, 2023 | Jon visited networking events yesterday (20 June 2023). | 正确。 |
| `conv-41_q94` | 开放域 | Salads, sandwiches, homemade desserts | unknown | 没记到或没检索到。 |
| `conv-43_q4` | 单跳 | 一长串书名 | Name of the Wind, A Dance with Dragons, etc. | 部分正确，漏掉多本书。 |
| `conv-43_q15` | 多跳 | likely John's friend, colleague or family | unknown | 没记到或没检索到。 |
| `conv-43_q29` | 单跳 | Middle school, high school, college; 4 years | unknown | 没记到或没检索到。 |
| `conv-50_q39` | 多跳 | Dodge Charger | unknown | 没记到或没检索到。 |
| `conv-50_q71` | 开放域 | A few months | unknown | 相比 m=4 基础版退步，可能是检索噪声。 |

## 当前结论

追加式记忆系统已经能跑通，并且在这个很小的样本上可以超过原始对话 RAG baseline。基础版 `m=4` 的粗略 F1 是 0.231，加入高信号细节记忆后提升到 0.304。

单纯增加每个 session 的记忆条数没有带来提升，反而可能让检索上下文变乱。简单的关键词加向量混合检索也没有明显帮助。相比之下，额外保存书名、日期、食物清单、地点、车名、时长等“高信号细节”更有价值。

下一步应在这个更强的记忆基础上继续做 proposal 中的核心模块：记忆去重/冲突更新，以及 reflection。这样既能控制记忆噪声，也能补强多跳问题。
