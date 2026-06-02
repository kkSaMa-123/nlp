# 给队友的项目说明

## 1. 我们现在做到了什么

这个项目已经完成了长期记忆 Agent 的核心代码和主要实验结果。现在可以进入写最终报告和做 PPT 的阶段。

项目目标是做一个能“记住长期对话历史”的 Agent。它不是直接把所有历史对话塞给模型，而是先从历史对话中提取记忆，再在回答问题时检索相关记忆。

目前我们已经完成：

- 跑通三个 baseline：No-memory、Full-context、Raw-turn RAG。
- 实现自己的长期记忆 Agent。
- 实现记忆提取、记忆存储、记忆检索。
- 实现记忆去重、合并、更新框架。
- 实现 reflection 高层记忆。
- 跑完 small set 消融实验。
- 跑完 p10 扩展实验。
- 用硅基流动 `deepseek-ai/DeepSeek-V4-Pro` 完成云端 LLM-as-Judge。
- 整理了 bad case 和成本统计。

## 2. 我们实现了哪些代码

主要代码在 `memory_agent/`：

| 文件 | 作用 |
|---|---|
| `memory_agent/agent/baselines.py` | No-memory 和 Raw-turn RAG baseline |
| `memory_agent/agent/controller.py` | 主 Agent 流程，包括 AppendOnly、UpdateMemory、UpdateReflection |
| `memory_agent/memory/writer.py` | 从对话中提取记忆 |
| `memory_agent/memory/store.py` | 存储记忆和向量检索 |
| `memory_agent/memory/retriever.py` | 检索封装 |
| `memory_agent/memory/updater.py` | 记忆去重、合并、更新 |
| `memory_agent/memory/reflection.py` | 根据已有记忆生成 reflection 记忆 |
| `memory_agent/eval/run_eval.py` | 项目评测入口 |

最终系统是：

```text
memory_agent.agent.controller:UpdateReflectionAgent
```

它的流程是：

```text
历史对话
→ 提取普通事实记忆和 detail notes
→ 去重、合并、更新
→ 生成 reflection 记忆
→ 保存 active memories
→ 问题到来时检索相关记忆
→ LLM 根据记忆回答
```

## 3. 我们跑了哪些实验

主要实验脚本在 `experiments/`：

| 文件 | 作用 |
|---|---|
| `experiments/run_small_experiments.sh` | 跑 small set 实验 |
| `experiments/run_p10_experiments.sh` | 跑 p10 预测实验 |
| `experiments/run_p10_cloud_judge.sh` | 跑云端 LLM-as-Judge |
| `experiments/summarize_predictions.py` | 计算粗略 F1、EM、unknown 数 |
| `experiments/compute_costs.py` | 统计 LLM 调用次数和耗时 |
| `experiments/analyze_bad_cases.py` | 提取 judge 失败案例 |
| `experiments/analyze_memory_failures.py` | 结合检索日志分析失败原因 |

主要结果在 `experiments/results/`。

最重要的结果文件：

| 文件 | 说明 |
|---|---|
| `predictions_nomem_p10.json` | No-memory 的 p10 预测 |
| `predictions_fullctx_p10.json` | Full-context 的 p10 预测 |
| `predictions_rag_p10.json` | Raw-turn RAG 的 p10 预测 |
| `predictions_update_reflection_p10.json` | 我们最终系统的 p10 预测 |
| `results_nomem_p10.json` | No-memory 云端 judge 结果 |
| `results_fullctx_p10.json` | Full-context 云端 judge 结果 |
| `results_rag_p10.json` | Raw-turn RAG 云端 judge 结果 |
| `results_update_reflection_p10.json` | 我们最终系统云端 judge 结果 |
| `cost_summary_p10.json` | 成本统计 |
| `small_experiment_summary.md` | 完整实验记录 |

## 4. 最终云端 Judge 结果

使用硅基流动：

```text
Judge 模型：deepseek-ai/DeepSeek-V4-Pro
Base URL：https://api.siliconflow.cn/v1
```

p10 一共有 40 道题，每类 10 道。

| 系统 | Judge Score | F1 | EM | 平均回答耗时 |
|---|---:|---:|---:|---:|
| No-memory | 0.000 | 0.000 | 0.000 | 0.110s |
| Full-context | 0.400 | 0.154 | 0.050 | 7.306s |
| Raw-turn RAG | 0.263 | 0.073 | 0.000 | 0.788s |
| Update + Reflection | 0.325 | 0.119 | 0.000 | 1.221s |

最重要的结论：

- 我们的系统 `Update + Reflection` 高于 Raw-turn RAG：`0.325 > 0.263`。
- 说明“提取式记忆 + 去重合并 + reflection”比直接检索原始对话片段更有效。
- 我们的系统还没有超过 Full-context：`0.325 < 0.400`。
- 但是我们的系统比 Full-context 快很多：`1.221s` vs `7.306s`。

## 5. 按题型结果

我们最终系统 `Update + Reflection` 的分类结果：

| 类型 | Judge Score | 正确 | 部分 | 错误 |
|---|---:|---:|---:|---:|
| temporal | 0.500 | 4 | 2 | 4 |
| open_domain | 0.500 | 4 | 2 | 4 |
| single_hop | 0.200 | 0 | 4 | 6 |
| multi_hop | 0.100 | 1 | 0 | 9 |

主要观察：

- temporal 和 open_domain 表现最好。
- multi-hop 最弱，说明系统对跨记忆推理和桥接信息检索还不稳定。
- 这部分可以作为报告里的不足和未来改进。

## 6. 消融实验结论

small set 上的几个重要发现：

- Append memory 比 Raw-turn RAG 好。
- 加入 detail notes 对具体事实帮助明显。
- 单纯增加每个 session 的记忆数量没有帮助，可能会引入检索噪声。
- 去重/合并可以减少重复记忆，但不一定直接提升 QA 分数。
- Reflection 已经能生成高层记忆，但当前数据里很多问题更依赖具体事实，所以提升不明显。
- 允许模型做谨慎推断会减少 unknown，但粗略 F1 没有提升，所以最终配置没有开启。

## 7. Bad Case 结论

bad case 文件：

```text
experiments/results/memory_failure_cases_update_reflection_p10_localjudge.md
```

主要失败原因：

- 有些问题需要多跳推理，模型检索到了相关线索但没有推出答案。
- 有些检索结果只命中主题相关记忆，但漏掉关键桥接事实。
- 有些问题答案存在于历史里，但记忆提取时没有完整保留。
- 当前回答 prompt 偏保守，容易输出 `unknown`。

可以在报告中写：

> 当前系统的主要问题不是完全没有记忆，而是记忆检索和跨记忆推理还不够稳定。尤其是 multi-hop 问题，往往需要把多个 session 的线索合并起来，当前系统容易漏掉桥接信息或回答 unknown。

## 8. 报告应该怎么写

建议最终报告结构：

1. 项目背景：为什么长期记忆 Agent 重要。
2. 相关工作：Very Long-Term Conversational Memory、Mem0、Generative Agents、MemoryBank。
3. 系统设计：Memory Writer、Store、Retriever、Updater、Reflection、Controller。
4. Baseline：No-memory、Full-context、Raw-turn RAG。
5. 我们的方法：Update + Reflection。
6. 实验设置：本地 Qwen2.5-3B 生成，硅基流动 DeepSeek-V4-Pro 做 judge。
7. 实验结果：重点放 p10 云端 judge 表。
8. 消融实验：detail notes、update、reflection、prompt inference。
9. Bad case：选 3-5 个例子。
10. 结论和不足：超过 RAG，但没超过 Full-context，multi-hop 仍弱。

## 9. PPT 应该讲什么

PPT 可以按这个顺序：

1. 项目任务：长期记忆 Agent。
2. 普通 LLM 为什么没有长期记忆。
3. 我们的系统流程图。
4. 代码模块说明。
5. 实验设置。
6. 总体结果表。
7. 分类结果表。
8. bad case。
9. 总结：超过 RAG，速度优于 Full-context，multi-hop 仍需改进。

## 10. 队友接下来重点看哪些文件

写报告看：

```text
milestone_report.md
experiments/results/small_experiment_summary.md
TEAM_SUMMARY.md
```

跑代码看：

```text
README.md
experiments/run_p10_experiments.sh
experiments/run_p10_cloud_judge.sh
```

看最终系统代码：

```text
memory_agent/agent/controller.py
memory_agent/memory/writer.py
memory_agent/memory/store.py
memory_agent/memory/updater.py
memory_agent/memory/reflection.py
```

