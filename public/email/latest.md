# AIxDaily · 2026-08-21

今日精选聚焦 AI 方法、验证与工具。化学和生命科学频道收录的均为预印本，涉及分子优化、跨情境组学预测与单细胞跨模态训练；数学频道也以预印本讨论推理验证和偏好不确定性。公开观点频道包含机构帖文及公测发布，工程频道则为正式软件发布，信息均应按其原始发布形态理解。

## AI × Chem

采集 1250，候选 60，精选 16。来源状态：各来源已完成

- [A multi-agent molecular optimization framework leads to a rapid-recovery intravenous anesthetic candidate with an improved safety margin](https://www.biorxiv.org/content/10.64898/2026.08.17.745149) — MASCOT 将化学约束图编辑搜索与三个职责专门化智能体结合，用于在效力、药代和安全性之间进行先导化合物优化。它在6项基准设置中表现最佳，并由 remimazolam 衍生物 RM-7 的动物研究给出实验延伸：该候选物显示出更高效力、更快功能恢复、更宽安全窗及保留的 flumazenil 可逆性。
- [Monroe: A Molecular Foundation Model for In-Context Probabilistic Inference](https://arxiv.org/abs/2608.18982v1) — Monroe 是面向低数据生物测定预测的分子基础模型：在超过8,100万 PM6 分子上预训练，改进立体化学图表示、构象去噪和多任务训练，并以 TabPFN 进行上下文下游预测。在 Polaris 与 activity cliff 基准上，它达到或超过已有模型；其 PFN 下游策略也提升了 MiniMol 和 CheMeleon。
- [Training Chemical Plausibility-Aware Large Language Models for Single-Step Retrosynthesis](https://arxiv.org/abs/2608.18940v1) — 该研究以 Top-K 提示训练 C3LM，使单步逆合成可表达多个化学上合理的答案；模型在约4,560万条经验证反应组成的 CREED-CCV-2+USPTO-XL 上训练，并结合 ChemCensor 与新颖性奖励。在 OOD URSA-expert-2026 基准中报告了最佳表现，并分析了 LLM 与传统模型的互补反应空间。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixchem/)

## AI × Bio

采集 1259，候选 60，精选 14。来源状态：各来源已完成

- [Signature Recontextualization: Mapping perturbational signatures across biological contexts](https://www.biorxiv.org/content/10.64898/2026.08.14.744937) — 提出跨生物学情境扰动转录组预测的统一基准 sigRecon，比较投影、网络传播、深度学习和基础模型方法，并覆盖细胞系与大鼠组织扰动数据。
- [Single-cell foundation models benefit from cross-modal training: adding proteomics data beats parameter scaling](https://www.biorxiv.org/content/10.64898/2026.08.14.744845) — 以44,843份蛋白质组样本继续预训练 Tahoe-x1，70M 参数模型在多数既有基准上达到或超过更大的 RNA-only 模型。
- [Assessing the Reliability of LLM-Generated Phenotype-Genotype Associations Through External Validation](https://www.biorxiv.org/content/10.64898/2026.08.13.744701) — 在4,196条由四个 LLM 生成的表型—基因及表型—SNP 关联上，以 Ensembl、GWAS Catalog 和 OMIM 进行外部验证。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixbio/)

## AI × Math

采集 521，候选 60，精选 9。来源状态：OpenReview: RuntimeError: 未配置 OpenReview 账号

- [Grading the Graders: Verification Autonomy Levels (L0-L5) for LLM Reasoning](https://arxiv.org/abs/2608.19009v1) — 提出 Verification Autonomy Levels（VAL）框架，以验证规格的来源和结论可保证的性质来区分 LLM 推理验证方案，并指出形式化可描述性质与开放世界经验任务在完备性上存在根本差异。
- [Preference Reasoning under Indeterminacy in Large Language Models](https://arxiv.org/abs/2608.18631v1) — 将 LLM 的偏好推理问题形式化为认识论不确定性与结构性不确定性两条轴，并报告当前模型常不能区分存在确定解和不存在确定解的实例。
- [Structure-Internalized Rule Language Model for Faithful Knowledge Graph Reasoning](https://arxiv.org/abs/2608.17443v1) — SIRLM 为知识图谱推理生成结构规则，并结合结构关系记忆、知识图谱 tokenizer 和受规则约束的神经符号推理器；作者在 36 个数据集上与 17 种 KGR 方法比较。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aixmath/)

## AI Voices

采集 82，候选 60，精选 10。来源状态：各来源已完成

- [@OpenAI：As models become more capable, the risks associated with developing and testing them internally also grow. We temporaril](https://x.com/OpenAI/status/2089777845187031262) — OpenAI 宣布，为加强研究环境并扩大监测范围，已暂缓面向部署的最新模型强化学习训练两周；其最大规模的前沿强化学习训练仍待小规模训练和评测提供更多对齐证据。编辑认为，这是一项罕见且具体的前沿模型研发安全实践披露。
- [@NVIDIAAI：We benchmarked 300+ NVIDIA verified skills to see how much they actually help agents on real tasks. Same task, same mode](https://x.com/NVIDIAAI/status/2090113635683340622) — NVIDIA 称，其在相同任务、模型和设置下测试了 300 多项已验证技能，仅改变代理是否获得该技能；发布方报告正确性、有效性和效率分别提高 41、39 和 35 个百分点，并开源了 SkillEvaluator。编辑认为，帖文提供了可复用的技能评测方向，但具体增益仍应结合基准任务和测量方法阅读。
- [@NVIDIAAI：We just released TensorRT Model Connect in Public Preview. You can take a supported @huggingface model to end-to-end Ten](https://x.com/NVIDIAAI/status/2089750360869233059) — NVIDIA 发布 TensorRT Model Connect 公测版：受支持的 Hugging Face 模型可通过两条命令转换为端到端 TensorRT 推理流程，无需中间 ONNX 导出，并可由原生 C++ API 调用。发布方还称该开源项目在人工指导和审阅下广泛使用了 Codex 代理。编辑认为，其中可直接检查的实现、测试与文档比“由代理构建”的表述更值得工程团队关注。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/aivoices/)

## Engineering

采集 46，候选 46，精选 9。来源状态：各来源已完成

- [Diffusers 0.40.0: New pipelines, tensor-parallel support, improved CLI, and more](https://github.com/huggingface/diffusers/releases/tag/v0.40.0) — huggingface/diffusers v0.40.0 发布多条音频、视频和图像生成管线，提供 tensor-parallel 推理，并将 Modular Diffusers 转为稳定支持；同时移除 JAX/Flax 支持并修复分片检查点的路径遍历问题。
- [0.149.0](https://github.com/openai/codex/releases/tag/rust-v0.149.0) — openai/codex rust-v0.149.0 为终端工作流加入 `codex agents` 任务面板、`codex queue`、工作目录命令和更完整的 Vim 编辑，并加强诊断、会话恢复和安全处理。
- [v0.14.24](https://github.com/run-llama/llama_index/releases/tag/v0.14.24) — run-llama/llama_index v0.14.24 修复摄取、记忆、检索、工具调用与多项连接器问题，并扩展 Claude Sonnet 5、Claude Opus 5、GPT-5.6、Gemini 3.7 Flash 和 MCP 2.x 支持。

[查看频道专页](https://zichenwang114514.github.io/ai-x-daily/channels/engineering/)

[查看完整网站与历史归档](https://zichenwang114514.github.io/ai-x-daily/)
