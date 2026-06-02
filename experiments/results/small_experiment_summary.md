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
| 更新式记忆 + Reflection，细节记忆，top-k=10 | `predictions_update_reflection_small.json` | 8 | 0.289 | 0.000 | 4 | 1.303s |
| 更新式记忆 + Reflection + 谨慎推断 prompt | `predictions_update_reflection_small_infer.json` | 8 | 0.275 | 0.000 | 3 | 1.345s |
| 追加式记忆，m=8，top-k=10 | `predictions_append_small_m8.json` | 8 | 0.101 | 0.000 | 5 | 0.911s |

## 追加式记忆消融

| 配置 | 提取到的记忆数量 | 结果 |
|---|---:|---|
| `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=6` | 5 段对话共 504 条记忆 | 第一版可用结果，粗略 F1 为 0.231。 |
| `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=10`, `MEMORY_KEYWORD_WEIGHT=0.25` | 5 段对话共 504 条记忆 | 简单关键词混合检索没有提升整体效果。 |
| `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=10`, `MEMORY_DETAIL_NOTES=1` | 5 段对话共 854 条记忆 | 当前小样本最好结果，细节记忆提高了召回。 |
| `UpdateMemoryAgent`, `MEMORY_DETAIL_NOTES=1`, `MEMORY_UPDATE_USE_LLM=0` | 5 段对话共提取 854 条，最终保留 677 条 active 记忆 | 去重合并减少了 177 条重复或相近记忆，分数略低于 append-only detail。 |
| `UpdateReflectionAgent`, `MEMORY_DETAIL_NOTES=1`, `MEMORY_UPDATE_USE_LLM=0`, `MEMORY_REFLECTIONS=6` | 5 段对话共生成 16 条 reflection 记忆 | 当前 small set 分数与 UpdateMemoryAgent 相同，reflection 未带来额外提升。 |
| `UpdateReflectionAgent`, `MEMORY_ALLOW_INFERENCE=1` | 5 段对话重新运行，允许模型根据强间接证据做 likely/probably 推断 | Unknown 从 4 降到 3，但粗略 F1 从 0.289 降到 0.275，因此不作为最终主配置。 |
| `MEMORY_PER_SESSION=8`, `MEMORY_TOP_K=10` | 5 段对话共 821 条记忆 | 单纯增加 LLM 提取条数没有帮助，可能引入了检索噪声。 |

## 按题型粗略 F1

| 系统 | 多跳问题 | 开放域问题 | 单跳问题 | 时间问题 |
|---|---:|---:|---:|---:|
| 原始对话 RAG | 0.043 | 0.222 | 0.358 | 0.182 |
| 追加式记忆，m=4 | 0.000 | 0.500 | 0.150 | 0.273 |
| 追加式记忆，m=4，混合检索 | 0.000 | 0.167 | 0.148 | 0.250 |
| 追加式记忆，m=4，细节记忆 | 0.000 | 0.182 | 0.333 | 0.701 |
| 更新式记忆，规则去重合并 | 0.000 | 0.182 | 0.296 | 0.679 |
| 更新式记忆 + Reflection | 0.000 | 0.182 | 0.296 | 0.679 |
| 更新式记忆 + Reflection + 谨慎推断 prompt | 0.000 | 0.182 | 0.345 | 0.573 |
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

## Reflection 实验统计

配置：`UpdateReflectionAgent`, `MEMORY_PER_SESSION=4`, `MEMORY_TOP_K=10`, `MEMORY_DETAIL_NOTES=1`, `MEMORY_UPDATE_USE_LLM=0`, `MEMORY_REFLECTIONS=6`

| 对话 | 提取记忆数 | Reflection 前 Active 数 | Reflection 数 | Reflection 后 Active 数 | ADD | IGNORE | MERGE | UPDATE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `conv-26` | 129 | 99 | 2 | 101 | 99 | 0 | 30 | 0 |
| `conv-30` | 125 | 103 | 2 | 105 | 103 | 0 | 22 | 0 |
| `conv-41` | 215 | 167 | 3 | 170 | 167 | 0 | 48 | 0 |
| `conv-43` | 188 | 146 | 3 | 149 | 146 | 8 | 34 | 0 |
| `conv-50` | 197 | 162 | 6 | 168 | 162 | 0 | 35 | 0 |
| **合计** | **854** | **677** | **16** | **693** | **677** | **8** | **169** | **0** |

本轮 reflection 实验能正常生成高层记忆，但在 8 题 small set 上没有提升 QA 粗略 F1。主要原因可能是当前 small set 中问题更依赖具体事实和细节，而不是高层人物画像。该实验仍然完成了 proposal 中 reflection 方向的代码闭环和消融对照。

## 本地 Judge 参考结果

使用本地 `qwen2.5:3b` 对 `predictions_update_reflection_small.json` 进行了一次开发版 LLM-as-Judge。结果文件：

```text
experiments/results/results_update_reflection_small_localjudge.json
```

| Judge 模型 | 样本数 | Overall Score | F1 | EM | 平均回答耗时 |
|---|---:|---:|---:|---:|---:|
| `qwen2.5:3b` | 8 | 0.750 | 0.279 | 0.000 | 1.304s |

注意：本地 3B 模型作为 judge 偏弱，分数只作为开发参考，不能替代正式实验。最终报告应使用 DeepSeek 或 DashScope 等更强的云端模型重新运行 `run_judge.py`。

## p10 扩展实验结果

评测集：`eval_kit/eval_set_p10.json`

该评测集由 `prepare_eval_set.py --per_category 10 --seed 42` 生成，共 10 段对话、40 道题，每类 10 题。

| 系统 | 输出文件 | 题数 | 粗略 F1 | EM | Unknown 数 | 错误数 | 平均回答耗时 |
|---|---|---:|---:|---:|---:|---:|---:|
| No-memory baseline | `predictions_nomem_p10.json` | 40 | 0.000 | 0.000 | 40 | 0 | 0.110s |
| Full-context baseline | `predictions_fullctx_p10.json` | 40 | 0.160 | 0.050 | 7 | 0 | 7.306s |
| 原始对话 RAG baseline | `predictions_rag_p10.json` | 40 | 0.071 | 0.000 | 17 | 0 | 0.788s |
| Update + Reflection 最终系统 | `predictions_update_reflection_p10.json` | 40 | 0.124 | 0.000 | 21 | 0 | 1.221s |

### p10 按题型粗略 F1

| 系统 | 多跳问题 | 开放域问题 | 单跳问题 | 时间问题 |
|---|---:|---:|---:|---:|
| No-memory baseline | 0.000 | 0.000 | 0.000 | 0.000 |
| Full-context baseline | 0.174 | 0.339 | 0.083 | 0.044 |
| 原始对话 RAG baseline | 0.010 | 0.123 | 0.049 | 0.104 |
| Update + Reflection 最终系统 | 0.050 | 0.134 | 0.094 | 0.219 |

### p10 Reflection 统计

| 对话 | 提取记忆数 | Reflection 前 Active 数 | Reflection 数 | Reflection 后 Active 数 |
|---|---:|---:|---:|---:|
| `conv-26` | 129 | 99 | 2 | 101 |
| `conv-30` | 125 | 103 | 2 | 105 |
| `conv-41` | 215 | 167 | 3 | 170 |
| `conv-42` | 183 | 158 | 2 | 160 |
| `conv-43` | 188 | 146 | 3 | 149 |
| `conv-44` | 176 | 158 | 6 | 164 |
| `conv-47` | 203 | 176 | 2 | 178 |
| `conv-48` | 183 | 163 | 6 | 169 |
| `conv-49` | 160 | 125 | 2 | 127 |
| `conv-50` | 197 | 162 | 6 | 168 |
| **合计** | **1756** | **1448** | **34** | **1482** |

p10 结果显示，最终系统在粗略 F1 上高于原始对话 RAG baseline，尤其在 temporal、single-hop 和 multi-hop 上都有提升。不过系统的 unknown 数更多，说明当前回答策略偏保守，后续可通过改进检索和回答 prompt 继续优化。

### p10 成本统计

成本统计文件：

```text
experiments/results/cost_summary_p10.json
```

| 系统 | 总 LLM 调用数 | 平均每题 LLM 调用数 | 平均回答耗时 |
|---|---:|---:|---:|
| No-memory baseline | 40 | 1.000 | 0.110s |
| Full-context baseline | 40 | 1.000 | 7.306s |
| 原始对话 RAG baseline | 40 | 1.000 | 0.788s |
| Update + Reflection 最终系统 | 322 | 8.050 | 1.221s |

说明：Update + Reflection 的 LLM 调用包括每个 session 的记忆写入、每段对话的 reflection，以及每道题的回答。当前 `MEMORY_UPDATE_USE_LLM=0`，因此 updater 不额外调用 LLM。

### p10 本地 Judge 参考结果

使用本地 `qwen2.5:3b` 进行开发版 LLM-as-Judge。结果文件：

```text
experiments/results/results_nomem_p10_localjudge.json
experiments/results/results_fullctx_p10_localjudge.json
experiments/results/results_rag_p10_localjudge.json
experiments/results/results_update_reflection_p10_localjudge.json
```

| 系统 / Judge 模型 | 样本数 | Overall Score | F1 | EM | 平均回答耗时 |
|---|---:|---:|---:|---:|---:|
| No-memory / `qwen2.5:3b` | 40 | 0.275 | 0.000 | 0.000 | 0.110s |
| Full-context / `qwen2.5:3b` | 40 | 0.475 | 0.154 | 0.050 | 7.306s |
| RAG baseline / `qwen2.5:3b` | 40 | 0.375 | 0.072 | 0.000 | 0.788s |
| Update + Reflection / `qwen2.5:3b` | 40 | 0.475 | 0.119 | 0.000 | 1.221s |

Update + Reflection 的分类结果：

| 类型 | 题数 | Judge Score | F1 | 正确 | 部分 | 错误 |
|---|---:|---:|---:|---:|---:|---:|
| multi_hop | 10 | 0.300 | 0.050 | 1 | 4 | 5 |
| open_domain | 10 | 0.500 | 0.130 | 3 | 4 | 3 |
| single_hop | 10 | 0.400 | 0.072 | 3 | 2 | 5 |
| temporal | 10 | 0.700 | 0.224 | 6 | 2 | 2 |

注意：本地 3B judge 仍然只作为开发参考；正式提交建议使用 DeepSeek 或 DashScope 重新评测。

### p10 云端 Judge 正式结果

使用硅基流动云端模型 `deepseek-ai/DeepSeek-V4-Pro` 进行 LLM-as-Judge。四个结果文件均显示 `judge_failures=0`，说明本轮 judge 调用成功，可以作为正式实验结果记录。

结果文件：

```text
experiments/results/results_nomem_p10.json
experiments/results/results_fullctx_p10.json
experiments/results/results_rag_p10.json
experiments/results/results_update_reflection_p10.json
```

| 系统 / Judge 模型 | 样本数 | Judge Score | F1 | EM | 平均回答耗时 | 正确 | 部分 | 错误 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| No-memory / `deepseek-ai/DeepSeek-V4-Pro` | 40 | 0.000 | 0.000 | 0.000 | 0.110s | 0 | 0 | 40 |
| Full-context / `deepseek-ai/DeepSeek-V4-Pro` | 40 | 0.400 | 0.154 | 0.050 | 7.306s | 11 | 10 | 19 |
| Raw-turn RAG / `deepseek-ai/DeepSeek-V4-Pro` | 40 | 0.263 | 0.073 | 0.000 | 0.788s | 7 | 7 | 26 |
| Update + Reflection / `deepseek-ai/DeepSeek-V4-Pro` | 40 | 0.325 | 0.119 | 0.000 | 1.221s | 9 | 8 | 23 |

Update + Reflection 的分类结果：

| 类型 | 题数 | Judge Score | F1 | 正确 | 部分 | 错误 |
|---|---:|---:|---:|---:|---:|---:|
| multi_hop | 10 | 0.100 | 0.050 | 1 | 0 | 9 |
| open_domain | 10 | 0.500 | 0.130 | 4 | 2 | 4 |
| single_hop | 10 | 0.200 | 0.072 | 0 | 4 | 6 |
| temporal | 10 | 0.500 | 0.224 | 4 | 2 | 4 |

正式云端 judge 结果显示：最终系统 `Update + Reflection` 的 Judge Score 为 0.325，高于原始对话 RAG baseline 的 0.263，说明派生记忆 + 去重合并 + reflection 的方案比直接检索原始对话片段更有效。最终系统仍低于 Full-context 的 0.400，但平均回答耗时为 1.221s，明显低于 Full-context 的 7.306s。

从题型看，最终系统在 temporal 和 open_domain 上表现最好，二者 Judge Score 都达到 0.500；multi_hop 仍然较弱，只有 0.100。这和 bad case 分析一致：多跳问题经常需要从间接线索推断，而当前系统容易回答 unknown 或漏掉桥接事实。

### p10 Bad Case 证据分析

为了判断失败到底来自写入、检索还是生成，额外从 `Update + Reflection` 的 p10 本地 judge 错例中抽取了 5 个 WRONG 案例，并关联回答日志中的 top retrieved memories。输出文件：

```text
experiments/results/memory_failure_cases_update_reflection_p10_localjudge.json
experiments/results/memory_failure_cases_update_reflection_p10_localjudge.md
```

初步观察：

| 案例 | 类型 | 模型回答 | 初步定位 |
|---|---|---|---|
| `conv-26_q27` | multi_hop | unknown | top memories 已包含 Caroline 想从事 counseling/mental health 的线索，模型没有进一步推出“不太会把写作当职业”。更像生成阶段过于保守。 |
| `conv-26_q30` | multi_hop | unknown | 检索结果大量是 Caroline 和 LGBTQ community 的相关信息，但缺少“Melanie 是否属于该群体”的直接证据。属于检索到相关主题但证据不足。 |
| `conv-26_q77` | multi_hop | unknown | top memory 中有 Melanie roadtrip 出事故的记录，模型没有利用该线索推断她短期内可能不会再去。更像生成阶段过于保守。 |
| `conv-42_q23` | single_hop | unknown | 检索到了 screenplay rejection，但没有完整检索到“第一部/第三部 screenplay 的主题”。属于检索命中不完整。 |
| `conv-42_q60` | multi_hop | unknown | 检索到了 Nate gaming 相关记忆，但没有检索到 Xenoblade 2 和 Nintendo Switch 的关键桥接信息。属于写入或检索缺失。 |

这些 bad cases 说明当前系统的主要问题不是完全没有记忆，而是：

1. 多跳问题需要从间接线索推断时，回答 prompt 偏保守，容易输出 unknown。
2. 检索有时只命中主题相关记忆，但漏掉关键桥接事实。
3. 后续优化可以针对“已检索到线索但回答 unknown”的情况，要求模型在证据足够时给出 cautious inference，而不是直接放弃。

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

目前 proposal 中的两个核心方向都已经有代码和 small-set 结果：记忆去重/冲突更新，以及 reflection。下一步应扩大评测规模，并使用 LLM-as-Judge 获得正式分数；同时整理 bad case，分析写入、检索、生成和更新各环节的失败原因。
