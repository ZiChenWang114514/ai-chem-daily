# AIX每日精读 · 2026-08-19

今日精选：AI × Chem 16 项，AI × Bio 14 项，AI × Math 7 项，AI Voices 1 项，Engineering 8 项。今日五频道共同日期为8月19日。科研栏目以预印本为主：化学聚焦分子生成横向评测、复杂天然产物逆合成与晶体配体坐标验证；生物关注表型—基因关联外部核验和人群级EHR模型；数学考察可机检构造、缺失前提推理及概率逻辑护栏。入选条目中未见同行评议论文。AI声音仅有一篇NVIDIA公开技术博客，缺少具体机制与评测；工程栏目集中于软件发布。

## AI × Chem

采集 1078，候选 60，精选 16。来源状态：各来源已完成

- [Systematic Benchmarking of AI-Based Molecular Generation Models for Structure-Based Drug Design](https://www.biorxiv.org/content/10.64898/2026.08.14.744939) — 该研究在176个经整理的蛋白—配体体系上比较12种分子生成与优化方法，并提出整合受体构象集合、集合对接和蛋白—配体相互作用图的SAFC功能分类器，用于对生成分子进行动力学感知的功能排序。
- [Superhuman Centaur Retrosynthesis Through Targeted LLM-enabled Decomposition in DeepRetro2](https://doi.org/10.26434/chemrxiv.15007537/v1) — DeepRetro2将LLM逆合成与递归分子拆解、子问题迭代生成和人工化学判断结合，在maitotoxin、bryostatin 1、bryostatin 3和luvesilocin上构建了可逐步细化的合成拆解方案。
- [Resolution-standardized evaluation of ligand atomic coordinates in crystallographic structures using machine learning](https://www.biorxiv.org/content/10.64898/2026.08.17.745351) — 研究提出原子级Box Correlation Coefficient（aBCC）及3D-CNN模型QAEmap，以分辨率标准化方式评价晶体结构中配体原子坐标与电子密度的一致性；在约3.5 Å以内预测仍可靠。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixchem/)

## AI × Bio

采集 1183，候选 60，精选 14。来源状态：各来源已完成

- [Assessing the Reliability of LLM-Generated Phenotype-Genotype Associations Through External Validation](https://www.biorxiv.org/content/10.64898/2026.08.13.744701) — 对四个 LLM 生成表型—基因及表型—SNP 关联的能力开展外部知识库验证；4,196 条关联中 74.19% 可匹配至少一个外部基因组知识库，但强证据比例仅为 9.15%。
- [Foresight-England: Development of a National-Scale Generative AI Model of Electronic Health Records for Medical Event Prediction across the COVID-19 Pandemic](https://arxiv.org/abs/2608.16273v1) — Foresight-E 描述了一个基于约 6,100 万人去标识化纵向 NHS 电子健康记录训练的 2.43 亿参数生成式模型；数据访问暂停，当前未报告定量结果。
- [Phenotype-associated spatial biomarker discovery in spatial transcriptomics with spHOT](https://www.biorxiv.org/content/10.64898/2026.08.11.744312) — spHOT 利用空间基础模型嵌入、层级组织域树和师生多实例学习，从样本级标签定位与表型相关的空间转录组标志物。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixbio/)

## AI × Math

采集 452，候选 60，精选 7。来源状态：OpenReview: RuntimeError: 未配置 OpenReview 账号

- [ALPS: Measuring Valid Creativity in Large Language Models with Mathematical Construction](https://arxiv.org/abs/2608.15979v1) — ALPS 以等式律为题目单元，要求系统构造满足该律的无限数学结构，或证明此类结构不存在；答案由自动证明检查器验证，并以可无限生成的新题降低训练数据重合风险。
- [Ask, Condition or Abstain: Reinforcement Learning for Missing-Premise Reasoning](https://arxiv.org/abs/2608.16554v1) — ACA-RL 将完整题目转化为带局部缺失前提标注的训练实例，训练模型在追问、条件作答和弃答之间作出选择；MPB 含 274 道经人工核验的数学、逻辑和现实文字题。
- [PL-Guard: Probabilistic Logic Reasoning for LLM Guardrails](https://arxiv.org/abs/2608.15673v1) — PL-Guard 将提示—回答对的语义归因与策略推理拆开：本地 LLM 输出谓词概率，ProbLog 按符号规则作显式概率推理。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixmath/)

## AI Voices

采集 17，候选 17，精选 1。来源状态：X: RuntimeError: HTTP 402 额度不足，请在 X Developer Console 充值 credits

- [How AI Coding Agents Can Unlock Materials Simulation with NVIDIA ALCHEMI Toolkit](https://developer.nvidia.com/blog/how-ai-coding-agents-can-unlock-materials-simulation-with-nvidia-alchemi-toolkit/) — NVIDIA 官方技术博客探讨 AI 编程智能体如何借助 ALCHEMI Toolkit 促进材料模拟；可见导语将原子尺度模拟概括为三项要求：科学知识、计算高效的模拟实现和可访问的接口。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aivoices/)

## Engineering

采集 29，候选 29，精选 8。来源状态：各来源已完成

- [langchain-openai==1.5.2a1](https://github.com/langchain-ai/langchain/releases/tag/langchain-openai%3D%3D1.5.2a1) — langchain-ai/langchain 发布 langchain-openai==1.5.2a1，扩大 OpenAI SDK 与模型兼容性，并修复流式推理、上下文窗口和 MCP 凭据处理问题。
- [0.148.0](https://github.com/openai/codex/releases/tag/rust-v0.148.0) — openai/codex 发布 rust-v0.148.0，加入会话导出、分叉和归档、Bedrock Runtime，以及异步 Hooks/MCP；同时加强跨平台沙箱限制。
- [b10448](https://github.com/ggml-org/llama.cpp/releases/tag/b10448) — ggml-org/llama.cpp 发布 b10448，新增 Kimi-K3 text model、转换支持及带 reasoning、内容和 typed tool calls 的 Kimi-K3 chat format。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/engineering/)

[查看完整网站与历史归档](https://zichenwang114514.github.io/ai-x-daily/)
