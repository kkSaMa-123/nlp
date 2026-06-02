# 长期记忆对话 Agent Milestone 进展报告

## 1. 项目概述

本项目目标是实现一个支持长期记忆的对话 Agent。普通大语言模型本身不会自动记住上一次对话内容，所以我们要做的是：让 Agent 能从历史多轮对话中提取记忆、保存记忆、在回答新问题时找回相关记忆，并且在记忆重复或冲突时进行一定管理。

本项目主要参考了以下思路：

| 参考工作 | 本项目采用的思路 |
|---|---|
| Evaluating Very Long-Term Conversational Memory of LLM Agents | 使用长期对话记忆问答任务作为评测方向 |
| Mem0 | 参考“提取记忆、检查重复/冲突、更新或合并记忆”的流程 |
| Generative Agents | 参考 reflection，用已有记忆生成更高层的总结性记忆 |
| MemoryBank | 作为相关工作了解，目前还没有实现遗忘曲线 |

目前项目已经能端到端运行：输入历史对话，系统提取并管理记忆，然后根据问题检索记忆并生成答案。同时，我们已经完成了 baseline 对照、小样本实验、p10 扩展实验和本地 judge 参考评测。

## 2. 当前进度

目前整体进度大约为 **75%-80%**。

已经完成的内容：

- 跑通三个必要 baseline：No-memory、Full-context、Raw-turn RAG。
- 实现基础长期记忆 Agent：`AppendOnlyMemoryAgent`。
- 实现记忆提取模块：从原始对话中抽取独立的“派生记忆”。
- 实现记忆存储和检索模块：保存记忆向量，并根据问题检索 top-k 相关记忆。
- 实现细节记忆 `detail notes`：额外保存日期、书名、地点、食物清单、车名、时间长度等容易被总结漏掉的信息。
- 实现记忆去重、合并和更新框架：`UpdateMemoryAgent`。
- 实现 reflection 机制：`UpdateReflectionAgent`，用已有 active memories 生成更高层的总结记忆。
- 实现日志记录：记录提取出的记忆、检索到的记忆、prompt、回答和更新统计。
- 完成 small set 多组消融实验。
- 完成 p10 扩展实验：10 段对话、40 道问题。
- 完成本地 `qwen2.5:3b` judge 参考评测。
- 编写了运行脚本、结果汇总脚本和成本统计脚本。

还没有完全完成的内容：

- 还没有使用 DeepSeek / DashScope 等云端强模型做正式 LLM-as-Judge。
- bad case 分析目前已有初步结果，但还需要整理成最终报告中的 3-5 个典型案例。
- 还没有跑完整数据集，目前主要结果来自 small set 和 p10 set。
- 最终论文式报告和展示 PPT 还没有完成。

## 3. 当前系统结构

当前项目代码结构基本符合任务要求：

```text
memory_agent/
├── agent/
│   ├── baselines.py       # No-memory baseline
│   └── controller.py      # 长期记忆 Agent 主流程
├── memory/
│   ├── store.py           # 记忆存储和向量检索
│   ├── writer.py          # 从对话中提取记忆
│   ├── retriever.py       # 检索封装
│   ├── updater.py         # 去重、合并、更新
│   └── reflection.py      # reflection 高层记忆
├── eval/
│   └── run_eval.py        # 项目评测入口
experiments/
├── run_small_experiments.sh
├── run_p10_experiments.sh
├── run_p10_cloud_judge.sh
├── summarize_predictions.py
├── analyze_bad_cases.py
└── compute_costs.py
```

系统流程如下：

```text
历史对话
→ MemoryWriter 提取记忆
→ MemoryUpdater 去重/合并/更新
→ MemoryReflector 生成高层 reflection 记忆
→ MemoryStore 保存 active memories
→ 问题到来时检索相关记忆
→ LLM 根据检索记忆生成答案
```

和 Vanilla RAG 的区别是：

- Vanilla RAG 直接检索原始对话片段。
- 我们的系统先把原始对话整理成记忆，再检索这些记忆。
- 这样更接近长期记忆 Agent，而不是简单把历史文本塞进向量库。

## 4. 初步成果

### 4.1 small set 结果

small set 使用 `eval_kit/eval_set_small.json`，共 8 道问题，主要用于快速调试和消融。这里的 F1 是粗略字符串指标，不是最终正式 judge 分数。

| 系统 | 粗略 F1 | EM | Unknown 数 | 平均回答耗时 |
|---|---:|---:|---:|---:|
| No-memory | 0.000 | 0.000 | 8 | 0.132s |
| Full-context | 0.105 | 0.000 | 2 | 17.362s |
| Raw-turn RAG | 0.201 | 0.000 | 2 | 0.731s |
| Append memory, m=4 | 0.231 | 0.125 | 5 | 0.590s |
| Append memory + detail notes | 0.304 | 0.000 | 4 | 1.023s |
| Update memory + detail notes | 0.289 | 0.000 | 4 | 1.080s |
| Update + Reflection | 0.289 | 0.000 | 4 | 1.303s |

small set 上的主要观察：

- No-memory 基本无法回答长期记忆问题。
- Full-context 很慢，因为它需要把完整历史放进 prompt。
- Raw-turn RAG 比 No-memory 好，但直接检索原始对话不够稳定。
- 追加式记忆已经能超过 Raw-turn RAG。
- 加入 detail notes 后 small set 粗略 F1 从 0.231 提升到 0.304，说明具体细节记忆是有帮助的。
- 去重合并减少了记忆数量，但 small set 上没有直接提升分数。
- Reflection 已经能运行，但 small set 里问题更偏具体事实，所以暂时没有带来明显提升。

### 4.2 p10 扩展实验结果

p10 set 使用 `eval_kit/eval_set_p10.json`，共 10 段对话、40 道问题，每类问题 10 道。

| 系统 | 题数 | 粗略 F1 | EM | Unknown 数 | 平均回答耗时 |
|---|---:|---:|---:|---:|---:|
| No-memory baseline | 40 | 0.000 | 0.000 | 40 | 0.110s |
| Full-context baseline | 40 | 0.160 | 0.050 | 7 | 7.306s |
| Raw-turn RAG baseline | 40 | 0.071 | 0.000 | 17 | 0.788s |
| Update + Reflection 最终系统 | 40 | 0.124 | 0.000 | 21 | 1.221s |

p10 的按题型粗略 F1：

| 系统 | 多跳问题 | 开放域问题 | 单跳问题 | 时间问题 |
|---|---:|---:|---:|---:|
| No-memory | 0.000 | 0.000 | 0.000 | 0.000 |
| Full-context | 0.174 | 0.339 | 0.083 | 0.044 |
| Raw-turn RAG | 0.010 | 0.123 | 0.049 | 0.104 |
| Update + Reflection | 0.050 | 0.134 | 0.094 | 0.219 |

p10 上的主要观察：

- 最终系统粗略 F1 高于 Raw-turn RAG baseline。
- 最终系统在 temporal、single-hop、multi-hop 上都比 Raw-turn RAG 有提升。
- Full-context 仍然是强 baseline，但平均耗时明显更高。
- 最终系统的 unknown 数偏多，说明回答 prompt 偏保守，后续需要优化。

### 4.3 本地 judge 参考结果

目前使用本地 `qwen2.5:3b` 做了一轮开发版 LLM-as-Judge。这个 judge 模型较弱，所以结果只作为参考，不能当最终正式分数。

| 系统 / Judge 模型 | 样本数 | Overall Score | F1 | EM |
|---|---:|---:|---:|---:|
| No-memory / qwen2.5:3b | 40 | 0.275 | 0.000 | 0.000 |
| Full-context / qwen2.5:3b | 40 | 0.475 | 0.154 | 0.050 |
| Raw-turn RAG / qwen2.5:3b | 40 | 0.375 | 0.072 | 0.000 |
| Update + Reflection / qwen2.5:3b | 40 | 0.475 | 0.119 | 0.000 |

本地 judge 下，最终系统和 Full-context 的 Overall Score 都是 0.475，高于 Raw-turn RAG 的 0.375。但由于 judge 是本地 3B 模型，正式结论还需要云端强模型重新评测。

### 4.4 记忆管理统计

small set 中，`UpdateMemoryAgent` 的记忆管理统计如下：

| 指标 | 数值 |
|---|---:|
| 原始提取记忆数 | 854 |
| 最终 active 记忆数 | 677 |
| 减少记忆数 | 177 |
| ADD | 677 |
| IGNORE | 8 |
| MERGE | 169 |
| UPDATE | 0 |

这说明当前系统已经能够做重复记忆的合并和忽略。small set 中没有明显新旧冲突，所以没有触发 UPDATE。

p10 中，`Update + Reflection` 最终系统的统计如下：

| 指标 | 数值 |
|---|---:|
| 提取记忆数 | 1756 |
| Reflection 前 active 记忆数 | 1448 |
| Reflection 记忆数 | 34 |
| Reflection 后 active 记忆数 | 1482 |

这说明 reflection 模块已经可以正常生成高层记忆，并加入后续检索。

### 4.5 成本统计

p10 实验中的平均 LLM 调用和耗时如下：

| 系统 | 总 LLM 调用数 | 平均每题 LLM 调用数 | 平均回答耗时 |
|---|---:|---:|---:|
| No-memory | 40 | 1.000 | 0.110s |
| Full-context | 40 | 1.000 | 7.306s |
| Raw-turn RAG | 40 | 1.000 | 0.788s |
| Update + Reflection | 322 | 8.050 | 1.221s |

Update + Reflection 的调用更多，是因为它包含记忆写入和 reflection。它的回答耗时比 Raw-turn RAG 高一些，但远低于 Full-context。

## 5. 当前结论

目前可以比较客观地说：

1. 项目已经不是只有想法，核心代码和实验流水线已经跑通。
2. 必要 baseline 已经完成，可以和自己的系统进行对照。
3. 自己的长期记忆系统已经实现了“提取记忆、存储记忆、检索记忆、回答问题、去重合并、reflection”的完整流程。
4. 在 p10 实验中，最终系统的粗略 F1 高于 Raw-turn RAG，并且本地 judge 总分也高于 Raw-turn RAG。
5. 当前系统还没有稳定超过 Full-context，但 Full-context 代价更高，而且在长上下文下扩展性较差。
6. 现在最需要补的是正式云端 judge、bad case 分析和最终报告，而不是重新推倒代码。

## 6. 目前存在的问题

### 6.1 结果还不够强

最终系统虽然超过 Raw-turn RAG，但提升不算特别大。尤其 open-domain 和 multi-hop 问题还有明显提升空间。

### 6.2 Unknown 偏多

最终系统在 p10 中有 21 个 unknown。说明系统有时可能检索到了部分信息，但回答 prompt 过于保守，或者检索结果不够集中。

### 6.3 Reflection 的效果还没有充分体现

Reflection 模块已经实现，但目前提升不明显。原因可能是当前题目很多依赖具体事实，而 reflection 更适合人物画像、长期偏好、跨 session 归纳类问题。

### 6.4 UPDATE 尚未充分验证

当前主要触发 MERGE 和 IGNORE，没有触发 UPDATE。后续如果想证明冲突更新能力，可以找更大样本，或者构造一两个冲突记忆测试。

### 6.5 正式 judge 还没完成

本地 3B judge 只适合开发阶段参考。最终报告最好使用 DeepSeek 或 DashScope 重新跑一次 LLM-as-Judge。

## 7. 下一步计划

### 7.1 优先完成正式评测

下一步最重要的是配置云端 API，运行：

```bash
bash experiments/run_p10_cloud_judge.sh
```

目标是得到可以写进最终报告的正式 judge 分数。

### 7.2 整理 bad case

从失败样例中选 3-5 个，分析问题出在哪一环：

| 失败类型 | 判断方式 |
|---|---|
| 写入失败 | 关键事实没有被提取成记忆 |
| 检索失败 | 关键事实在记忆库里，但回答时没有被检索到 |
| 生成失败 | 检索到了相关记忆，但模型没有正确使用 |
| 更新失败 | 新旧记忆没有正确合并或覆盖 |

这部分是最终报告里很重要的内容。

### 7.3 优化最终系统

可以做的改进包括：

- 调整回答 prompt，减少不必要的 unknown。
- 改进检索打分，让问题关键词和记忆关键词匹配更稳定。
- 对 reflection 记忆单独设置类型或权重，避免它和事实记忆混在一起造成干扰。
- 在更大评测集上观察 UPDATE 是否触发。

### 7.4 完成最终报告和展示

最终报告建议包含：

- 项目目标和参考论文。
- 系统架构图。
- 记忆提取、检索、更新、reflection 的实现说明。
- baseline 对比表。
- 消融实验表。
- 按问题类型的结果。
- bad case 分析。
- 当前不足和未来改进。

## 8. 三人分工建议

### 同学 A：代码和实验负责人

负责内容：

- 维护 `memory_agent/` 代码。
- 跑 p10 或更大规模实验。
- 配置云端 judge。
- 记录每组实验命令和输出文件。

当前最该做：

```bash
bash experiments/run_p10_cloud_judge.sh
```

### 同学 B：结果分析负责人

负责内容：

- 整理 `experiments/results/small_experiment_summary.md`。
- 从 judge 结果中提取总分、分类分数、bad cases。
- 分析每个失败样例属于写入失败、检索失败还是生成失败。
- 做结果表格。

当前最该做：

```text
整理 3-5 个 bad case，并写清楚失败原因。
```

### 同学 C：报告和展示负责人

负责内容：

- 写最终报告。
- 做系统架构图。
- 整理参考论文和项目定位。
- 做展示 PPT。

当前最该做：

```text
把 milestone 报告扩展成最终报告初稿。
```

## 9. Milestone 总结

截至目前，本项目已经完成了长期记忆 Agent 的主要代码框架和初步实验。系统已经可以从历史对话中提取记忆、去重合并、生成 reflection，并在回答问题时检索相关记忆。实验方面，已经完成了 small set 和 p10 set 的 baseline 对比，最终系统在 p10 上优于 Raw-turn RAG baseline，但仍未稳定超过 Full-context。

下一阶段的重点不是重新设计整个系统，而是完成正式云端 judge、整理 bad case、优化 unknown 问题，并把已有代码和实验结果写成最终报告。

