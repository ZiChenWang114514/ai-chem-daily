# AIX Daily 五频道日报 · 2026-08-18

今日精选以尚待同行评议的预印本和可直接采用的软件正式发布为主，未见入选的同行评议论文或公开观点。AI×化学关注药物发现、电解液微观结构与天然产物酶学；AI×生物呈现临床影像、罕见病电子病历和肿瘤分化研究。工程频道聚焦 llama.cpp 与 JAX 的兼容、模型支持和性能改进。AI×数学与 AI Voices 暂无足够高质量更新，预印本结果不应视为定论。

## AI × Chem

采集 415，候选 60，精选 10。来源状态：各来源已完成

- [Discovery of Selective Small-Molecule Ligands of SV2C by AI-Enhanced Virtual Screening and Experimental Validation](https://www.biorxiv.org/content/10.64898/2026.08.11.744237) — 研究以SV2A冷冻电镜结构为模板构建SV2C同源模型，结合MD、GaMD、卷积神经网络评分和虚拟筛选，从596万化合物中筛得候选，并对71个化合物进行热稳定性、放射性配体竞争、Ki和亚型选择性实验。共发现22个活性分子，其中化合物56对SV2C的Ki为3.25 μM，且相对SV2A、SV2B均表现出十倍以上选择性。
- [Evidence for significant multi-Li+ clustering in common lithium-ion battery electrolytes](https://doi.org/10.26434/chemrxiv-2025-ndqzk/v4) — 研究将机器学习原子级模拟、核磁共振、电化学测量和量子化学计算结合起来，提出常见锂离子电池电解液中存在无阴离子参与的多Li+团簇，并认为这类易被还原的结构有助于解释含碳酸乙烯酯混合溶剂的经验优势。其机器学习力场仅由气相团簇量子化学数据参数化，却能再现多种凝聚相实验现象。
- [TRACER navigates rearrangement-driven sesterterpene chemical space via multimodal enzyme-product representation learning](https://www.biorxiv.org/content/10.64898/2026.08.16.745124) — TRACER将酶序列表征与萜类产物化学型共同学习，用于预测倍半萜合酶的骨架重排。模型指导基因组挖掘发现两种双功能合酶及四种此前未报道的碳骨架，并以密度泛函计算、定点突变和分子动力学分析环化级联及关键位点E305的作用。

[查看频道专页](https://zichenwang114514.github.io/ai-chem-daily/channels/aixchem/)

## AI × Bio

采集 620，候选 60，精选 13。来源状态：各来源已完成

- [Deep Learning-Based Classification of Bone Lesions on CT Scans of Metastatic Spine Disease Patients: A 3D-Convolutional Neural Network Approach](https://www.medrxiv.org/content/10.64898/2026.08.13.26360407) — 回顾性纳入 151 名转移性脊柱肿瘤患者、2,125 个椎体，以 3D-CNN 将粗粒度体素预测转为椎体病灶类型判定；三折验证和独立留出集上，集成模型准确率为 84.7%。
- [Early Detection of Erythropoietic Protoporphyria Using Sequential Machine Learning on Longitudinal Electronic Health Records](https://www.medrxiv.org/content/10.64898/2026.08.15.26360514) — 在两家旧金山医疗系统的纵向电子病历中，以 74 例确诊红细胞生成性原卟啉症训练时序模型，并在未重训的外部医院检验。外部 AUC 为 0.72，模型可在记录诊断前中位 264 天提示高风险。
- [VRK1 kinase maintains an undifferentiated proliferative state in neuroblastoma tumor cells](https://www.biorxiv.org/content/10.64898/2026.08.05.742965) — 结合患者肿瘤数据、组织芯片、单细胞转录组、细胞系与患者来源细胞以及异种移植模型，研究显示抑制 VRK1 会伴随神经母细胞瘤分化标志上升与增殖降低。

[查看频道专页](https://zichenwang114514.github.io/ai-chem-daily/channels/aixbio/)

## AI × Math

采集 0，候选 0，精选 0。来源状态：OpenReview: RuntimeError: 未配置 OpenReview 账号

- 今日无足够高质量更新。

[查看频道专页](https://zichenwang114514.github.io/ai-chem-daily/channels/aixmath/)

## AI Voices

采集 7，候选 7，精选 0。来源状态：X: RuntimeError: HTTP 402 额度不足，请在 X Developer Console 充值 credits

- 今日无足够高质量更新。

[查看频道专页](https://zichenwang114514.github.io/ai-chem-daily/channels/aivoices/)

## Engineering

采集 35，候选 35，精选 8。来源状态：各来源已完成

- [b10448](https://github.com/ggml-org/llama.cpp/releases/tag/b10448) — ggml-org/llama.cpp b10448 正式加入 Kimi-K3 文本模型的转换、推理与聊天模板支持，涵盖推理内容、流式输出和工具调用解析，并修复模型保存后会丢失 KDA 门限参数的问题。
- [JAX v0.11.1](https://github.com/jax-ml/jax/releases/tag/jax-v0.11.1) — jax-ml/jax jax-v0.11.1 停止反序列化 2026-01-15 前导出的模块，移除两项旧优化配置并改用 EffortLevel；同时修复 cuDNN 融合注意力的 vmap/FP8 路径及小矩阵行列式的数值稳定性。
- [b10456](https://github.com/ggml-org/llama.cpp/releases/tag/b10456) — ggml-org/llama.cpp b10456 调整 SYCL 量化复制内核的线程和线程块配置。在 Intel Arc 70 的 q4_0→f32 路径上，官方发布说明的吞吐量由 20.21 GB/s 提升至 158.19 GB/s。

[查看频道专页](https://zichenwang114514.github.io/ai-chem-daily/channels/engineering/)

[查看完整网站与历史归档](https://zichenwang114514.github.io/ai-chem-daily/)
