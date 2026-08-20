# AIxDaily · 2026-08-20

今日精选：AI × Chem 16 项，AI × Bio 13 项，AI × Math 16 项，AI Voices 10 项，Engineering 7 项。今日五个频道均有精选，研究侧以预印本为主：化学聚焦分子生成、虚拟筛选与逆合成，生物涵盖跨模态单细胞、细菌蛋白语言模型和空间组学；数学集中讨论验证、自主构造和缺失前提推理。AI观点频道收录公开帖文及其发布主张，尚待独立核验；工程频道则为正式软件发布，提示关注升级兼容性。

## AI × Chem

采集 2196，候选 60，精选 16。来源状态：各来源已完成

- [Systematic Benchmarking of AI-Based Molecular Generation Models for Structure-Based Drug Design](https://www.biorxiv.org/content/10.64898/2026.08.14.744939) — 在176个蛋白—配体体系上比较12类分子生成与优化方法，并以SAFC结合受体构象集合、集合对接和相互作用图，为生成分子给出具备动力学信息的功能排序。
- [Discovery of Selective Small-Molecule Ligands of SV2C by AI-Enhanced Virtual Screening and Experimental Validation](https://www.biorxiv.org/content/10.64898/2026.08.11.744237) — 以AI增强虚拟筛选和中等通量生物物理检测，从596万商业化合物中找到多类选择性SV2C小分子配体，其中化合物56对SV2C的Ki为3.25 μM。
- [Training Chemical Plausibility-Aware Large Language Models for Single-Step Retrosynthesis](https://arxiv.org/abs/2608.18940v1) — 构建含约4560万条已验证反应的CREED-CCV-2+USPTO-XL，训练C3LM，并以Top-K提示和化学合理性、创新性奖励改进单步逆合成。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixchem/)

## AI × Bio

采集 2330，候选 60，精选 13。来源状态：各来源已完成

- [Single-cell foundation models benefit from cross-modal training: adding proteomics data beats parameter scaling](https://www.biorxiv.org/content/10.64898/2026.08.14.744845) — 以 44,843 个蛋白质组样本继续预训练 Tahoe-x1，比较跨模态训练与单纯扩大 RNA 模型参数规模的效果。
- [A contextualised protein language model reveals the functional syntax of bacterial evolution](https://www.biorxiv.org/content/10.1101/2025.07.20.665723) — 在超过 130 万个细菌基因组上训练 Bacformer，以全基因组蛋白序列上下文关联蛋白组织、功能与表型。
- [Spatial second-order features predict glioma malignant transformation](https://www.biorxiv.org/content/10.64898/2026.08.14.744974) — 对 18 例回顾性 IDH 突变胶质瘤活检开展空间 DNA/RNA 整合分析，研究恶性转化的预测特征。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixbio/)

## AI × Math

采集 1233，候选 60，精选 16。来源状态：OpenReview: RuntimeError: 未配置 OpenReview 账号

- [Grading the Graders: Verification Autonomy Levels (L0-L5) for LLM Reasoning](https://arxiv.org/abs/2608.19009v1) — 提出 Verification Autonomy Levels（VAL）L0–L5，用验证规范的来源与判定结论所能保证的内容，统一描述 LLM 推理验证方案。
- [ALPS: Measuring Valid Creativity in Large Language Models with Mathematical Construction](https://arxiv.org/abs/2608.15979v1) — ALPS 以可自动判定的代数律任务，测试模型能否构造满足条件的无限数学结构，或证明这类结构不存在。
- [Ask, Condition or Abstain: Reinforcement Learning for Missing-Premise Reasoning](https://arxiv.org/abs/2608.16554v1) — ACA-RL 训练模型在题目前提缺失时选择追问、给出条件式答案或弃答，并发布覆盖数学、逻辑和现实文字题的 MPB。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixmath/)

## AI Voices

采集 62，候选 60，精选 10。来源状态：各来源已完成

- [@ornith_：Aloha! 🌺Introducing Ornith-1.5, a family of open-source LLMs spanning 9B Dense, 35B MoE, and 397B MoE, trained with self](https://x.com/ornith_/status/2090074077084127302) — Ornith 发布 Ornith-1.5 开源模型家族，覆盖 9B 稠密、35B MoE 与 397B MoE 三种规模，并公布了推理、智能体和编程基准成绩。发布方称，其训练采用端到端自我改进循环，模型会提出任务、生成任务脚手架，并产出用于强化学习的解题轨迹。
- [@OpenAI：As models become more capable, the risks associated with developing and testing them internally also grow. We temporaril](https://x.com/OpenAI/status/2089777845187031262) — OpenAI 表示，为加强研究环境并扩展监测覆盖，其面向部署的最新模型强化学习训练暂停两周；计划中最大规模的前沿强化学习运行仍处于暂停状态。
- [@UnslothAI：We’re releasing new Qwen3.8-27B GGUFs with 10% higher accuracy. Unsloth Dynamic V3 outperforms others by >10% on Div-300](https://x.com/UnslothAI/status/2090103470015828184) — Unsloth 发布用于 Qwen3.8-27B 的新 GGUF 量化版本，并称 Dynamic V3 在 Div-300、KLD 等测试中优于其他方案；同时提供号称可在 8GB 内存运行的 1-bit 量化版本。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aivoices/)

## Engineering

采集 45，候选 45，精选 7。来源状态：各来源已完成

- [0.148.0](https://github.com/openai/codex/releases/tag/rust-v0.148.0) — openai/codex 发布 rust-v0.148.0，加入会话导出、fork、归档与恢复、Amazon Bedrock Runtime 内置提供商，以及异步 Hook 和 MCP 工具调用；同时改进会话恢复、网络重连与 Windows/Linux 沙箱限制。
- [JAX v0.11.1](https://github.com/jax-ml/jax/releases/tag/jax-v0.11.1) — jax-ml/jax 发布 jax-v0.11.1，加入 `jax.numpy.top_k`，并调整 Exported 模块反序列化、`EffortLevel` 配置、数组 API 返回类型和负索引默认行为。
- [v0.14.24](https://github.com/run-llama/llama_index/releases/tag/v0.14.24) — run-llama/llama_index 发布 v0.14.24，修复文档摄取、聊天记忆、检索、工具参数和多家向量库兼容性问题，并新增 Claude Sonnet 5、Claude Opus 5、GPT-5.6、Gemini 3.7 Flash 等模型支持。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/engineering/)

[查看完整网站与历史归档](https://zichenwang114514.github.io/ai-x-daily/)
