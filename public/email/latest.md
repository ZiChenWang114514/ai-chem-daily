# AI × Chem 每日预印本精选 · 2026-08-16

抓取 289 篇，筛得 20 篇候选，最终精选 15 篇。

1. [Learning from human and chemical languages to predict biological function](https://www.biorxiv.org/content/10.64898/2026.08.09.743788) — PubCheF-1把分子结构与其出现论文中的功能语言标签关联，直接预测生物功能。模型筛得跨全部β-内酰胺酶类别的结构多样抑制剂；候选物可结合活性位点、恢复耐药病原体对抗生素的敏感性，并在动物感染模型中显示活性。

2. [SafeChem: A Benchmark Dataset for Multi-Label Chemical Hazard Prediction and LLM Safety Hallucination Evaluation](https://doi.org/10.26434/chemrxiv.15007436/v1) — SafeChem汇集32211种化学物质、结构表示、理化描述符及30项GHS危害标签，同时评测分子多标签分类和大模型安全判断。六类基线在高频标签上的宏AUPRC为0.45至0.55，中频标签仅0.08至0.28；八个大模型在500种高危物质上遗漏幻觉率均超过0.21。

3. [Neural Networks Accelerate Ab Initio Multiple Spawning Simulations: A Case Study of Using Machine Learning Potentials for Excited State Dynamics](https://doi.org/10.26434/chemrxiv.15007443/v1) — 该研究检验机器学习势能面能否加速非绝热从头算多重生成动力学。乙烯和去质子化GFP发色团上的低测试误差仍掩盖圆锥交叉附近的假能隙、伪简并和态序错误；按小能隙切换至量子化学的混合方案将成本降低约一个数量级，并复现激发态布居衰减。

4. [Physically Grounded Generative Modeling of All-Atom Biomolecular Dynamics](https://www.biorxiv.org/content/10.64898/2026.02.15.705956) — BioKinema采用受朗之万动力学相关衰减启发的时空扩散架构，并以分层预测与插值生成连续时间的全原子轨迹，缓解长时生成误差累积。摘要称其可复现蛋白构象系综的热力学与动力学，解析配体诱导变化和变构作用，并借助增强采样估计稀有解离路径。

5. [CALFP-MHC: Interpretable Pan-Allelic Prediction of Peptide-MHC Binding and Presentation Using Chemically Grounded Fingerprints and Contrastive Learning](https://www.biorxiv.org/content/10.64898/2026.08.10.743877) — CALFP-MHC以化学信息学指纹描述氨基酸官能团、连接关系和子结构，再结合监督对比预训练与卷积-Transformer预测肽-MHC结合。约1870万对样本上AUC达0.93至0.97，在200:1失衡下仍高于0.90；独立质谱配体和新抗原数据也保持较强区分能力。

6. [A leakage-controlled benchmark shows apparent codon-language-model advantages in synonymous-variant prediction are evaluation artifacts](https://www.biorxiv.org/content/10.64898/2026.08.12.744371) — 该研究系统复查密码子语言模型预测同义变异的优势，发现随机划分下2.3至14.3个百分点的分词收益及最高10个百分点的模型领先均受泄漏和评测设置驱动。基因留出、汇总统计及探针设置审计后优势全部消失，作者据此发布CodonBench并估计当前样本量难以可靠识别微弱信号。

7. [Benchmark Averages Hide the Failures That Matter: Quantizing ESM-2 for Protein Variant-Effect Prediction](https://www.biorxiv.org/content/10.64898/2026.08.10.744024) — 研究在完整ProteinGym替换基准的201项实验、241万变异和三种ESM-2规模上比较六种数值精度。平均相关性变化虽小，INT8仍使单项实验的ρ从0.591降至0.223；改用非对称激活量化可消除受损实验，而准确率、内存和速度的帕累托最优组合全部来自6.5亿参数模型。

8. [LEN-Seek: Fast and scalable ligand binding-site similarity search in the latent space of an SE(3)-invariant graph VAE](https://www.biorxiv.org/content/10.64898/2026.08.14.744759) — LEN-Seek用SE(3)不变图变分自编码器，把结合位点的三维几何、理化环境及Ankh蛋白语言模型特征压缩到概率潜空间，以向量检索替代逐对结构比对。与ProBiS相比，它保留了相当部分相似位点的检出能力，同时把单次比较成本降低约3400倍。

9. [AI4Loop: an Artificial Intelligence Framework Reveals Increased 3D Chromatin Interactions and Therapeutic Vulnerabilities across 12,000 Cancer Samples](https://www.biorxiv.org/content/10.64898/2026.08.12.744314) — AI4Loop从RNA测序数据推断基因中心的三维染色质互作网络，并在12347份、覆盖32种癌症的转录组上观察到肿瘤互作普遍增强。模型网络的癌症分类优于单纯表达量；结合逾5万份药物扰动转录组后筛得候选药，Hi-C实验确认eperezolid和radezolid可降低乳腺癌相关互作增益。

10. [Protein language models and the long tail of functional diversity](https://www.biorxiv.org/content/10.64898/2026.08.14.744703) — 研究聚焦蛋白语言模型预训练数据中常被剔除的单例序列；在含33.4亿条序列的GigaRef中，这类序列约占43%。替代聚类参数表明不少单例实际存在同源关系，互信息分析显示其可被模型学习；宏基因组单例还具有更密集、多样的结构域内容，序列同一性聚类会漏掉部分结构域同源。

[查看完整日报与历史归档](https://zichenwang114514.github.io/ai-chem-daily/)

> 数据来自 arXiv、bioRxiv 与 ChemRxiv 公开元数据。预印本未经同行评议。
