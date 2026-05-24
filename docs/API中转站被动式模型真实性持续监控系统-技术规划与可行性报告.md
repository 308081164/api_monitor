# API 中转站被动式模型真实性持续监控系统

## 技术规划与开发可行性报告

> **版本**: v1.0 | **日期**: 2026-05-24
> **定位**: 基于用户正常使用流量，被动分析 API 响应指纹，持续检测模型是否被"掺水"或替换

---

## 一、项目概述

### 1.1 问题定义

API 中转站/代理服务存在以下风险行为：

| 风险类型 | 描述 | 典型手段 |
|---------|------|---------|
| **模型替换** | 将用户请求的高价模型替换为低价模型 | GPT-4o → GPT-4o-mini、Claude Opus → Haiku |
| **模型掺水** | 按比例混合真实模型与廉价模型 | 70% 真模型 + 30% 廉价模型 |
| **量化降级** | 使用量化版本替代全精度模型 | FP16 → INT8/FP8 |
| **协议篡改** | 修改响应字段、截断上下文 | 删除 tool_calls、截断长上下文 |
| **动态切换** | 在不同时段使用不同后端 | 高峰期降级、上游变更不通知 |

### 1.2 核心设计原则

- **被动式**: 不发送额外测试请求，仅从用户正常使用的 API 响应中提取特征
- **实时性**: 随用户使用持续运行，发现异常立即告警
- **低侵入**: 以透明代理/中间件形态部署，用户无感知
- **可解释**: 告警时提供具体证据（而非仅一个分数）

### 1.3 预期输出

当检测到模型从 A 切换为 B 时，自动弹出提示：

```
⚠️ 模型切换检测告警

检测时间: 2026-05-24 14:32:15
中转站: api.example.com
请求模型: claude-sonnet-4-20250514

检测到变化:
  模型家族: Claude → GPT (置信度: 94.2%)
  文体指纹偏移: +0.37 (阈值: 0.15)
  词汇分布偏移: KL散度 = 0.42 (阈值: 0.20)

证据:
  [1] 响应中出现 GPT 特征词: "delve", "tapestry", "landscape"
  [2] 响应中缺失 Claude 特征词: "certainly", "I'd be happy to"
  [3] system_fingerprint 字段缺失/变更
  [4] 响应延迟模式与 GPT-4o-mini 匹配 (p=0.03)

建议: 当前后端可能已被替换为 GPT 系列模型
```

---

## 二、技术可行性分析

### 2.1 学术基础评估

本方案基于以下经过顶级会议/期刊验证的研究成果：

#### 2.1.1 跨模型家族识别 — ✅ 高度可行

| 论文 | 发表 | 核心结论 | 准确率 |
|------|------|---------|--------|
| Sun et al., *"Idiosyncrasies in Large Language Models"* (CMU/Berkeley) | arXiv 2025 | 使用 LLM2Vec 编码器训练分类器，可从文本输出识别来源模型 | **97.1%** (Chat API 5分类) |
| Fu et al., *"FDLLM: A Dedicated Detector for Black-Box LLMs Fingerprinting"* | arXiv 2025 | 使用 LoRA 微调提取深度特征，对未见模型准确率达 95% | **95%** (未见模型) |
| McGovern et al., *"Your Large Language Models Are Leaving Fingerprints"* | GenAIDetect 2025 | GradientBoost + n-gram/POS 特征，跨领域鲁棒 | **F1=0.98** (多模型识别) |
| Suzuki et al., *"Natural Fingerprints of Large Language Models"* | arXiv 2025 | 即使训练数据完全相同，不同模型仍可区分 | **85%** (6分类, Transformer) |

**结论**: 区分 GPT vs Claude vs Gemini vs Llama 等不同**模型家族**，技术上高度成熟，准确率 95%+。

#### 2.1.2 同家族不同规模识别 — ⚠️ 中等可行

| 论文 | 核心结论 |
|------|---------|
| Idiosyncrasies (CMU/Berkeley) | 同家族内不同规模模型区分准确率约 **80%** |
| LLMmap (USENIX Security 2025) | 主动探测可识别 42+ 模型版本，准确率 >95%（但需主动发探针） |

**结论**: 区分 GPT-4o vs GPT-4o-mini 等同家族不同规模模型可行但精度有限，需结合多信号融合。

#### 2.1.3 量化变体检测 — ❌ 纯文本方法不可行

| 论文 | 核心结论 |
|------|---------|
| Cai et al., *"Are You Getting What You Pay For?"* (UC Berkeley, NeurIPS 2025 Workshop) | **文本分类器在区分 FP16 vs INT8/FP8 时准确率接近 50%（随机水平）**，即使使用 BERT/T5/GPT-2/LLM2Vec 等强编码器 |

> ⚠️ **这是最重要的负面结论**: 纯文本被动方法**无法检测量化降级**。这是方案的根本性局限。

#### 2.1.4 时序侧信道 — ✅ 高度可行（需网络层访问）

| 论文 | 发表 | 核心结论 |
|------|------|---------|
| Alhazbi et al., *"LLMs Have Rhythm"* | IEEE OJCOMS 2025 | 利用 token 间时间间隔 (ITTs) 作为指纹，完全被动、非侵入式，**加密流量下仍有效** |

**结论**: 如果以代理模式部署（可观测网络流量），时序分析是极有价值的辅助信号。

#### 2.1.5 API 元数据信号 — ✅ 可行（零成本）

| 提供商 | 可用信号 | 检测价值 |
|--------|---------|---------|
| OpenAI | `system_fingerprint`、`model`、`logprobs` | 后端变更检测 |
| Anthropic Claude | `thinking_signature`（加密签名） | **密码学级别验证**，中转站无法伪造 |
| Google Gemini | `modelVersion`、`logprobs_result` | 模型版本验证 |

### 2.2 可行性总结

| 检测目标 | 被动文本分析 | +元数据 | +时序 | +Logprobs | 综合可行性 |
|---------|:-----------:|:------:|:----:|:--------:|:---------:|
| 跨家族替换 (GPT→Claude) | ✅ 97% | ✅ | ✅ | ✅ | **高** |
| 同家族降级 (GPT-4o→mini) | ⚠️ 80% | ⚠️ | ✅ | ✅ | **中高** |
| 量化降级 (FP16→INT8) | ❌ ~50% | ❌ | ⚠️ | ✅ | **低（纯被动）/ 中（需logprobs）** |
| 动态掺水 (混合路由) | ⚠️ | ⚠️ | ✅ | ✅ | **中** |
| 协议篡改 | N/A | ✅ | N/A | N/A | **高** |

> **核心结论**: 对于最常见的"跨家族模型替换"（如声称 GPT-4 实际用 Claude），被动式检测**技术上完全可行且精度很高**。对于更细微的"同家族降级"和"量化"，需要结合多信号融合，精度有所下降但仍具实用价值。

---

## 三、系统架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户应用程序                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ API 请求
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SentinelProxy (透明代理)                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ 请求拦截  │→│ 指纹采集引擎  │→│   多信号融合分析引擎       │  │
│  │ & 转发   │  │              │  │                           │  │
│  │          │  │ ┌──────────┐ │  │ ┌─────────────────────┐  │  │
│  │          │  │ │文本指纹  │ │  │ │ 模型家族分类器     │  │  │
│  │          │  │ │提取器    │ │  │ │ (LLM2Vec/DeBERTa)  │  │  │
│  │          │  │ ├──────────┤ │  │ ├─────────────────────┤  │  │
│  │          │  │ │元数据    │ │  │ │ 词汇分布偏移检测   │  │  │
│  │          │  │ │采集器    │ │  │ │ (KL散度/统计检验)  │  │  │
│  │          │  │ ├──────────┤ │  │ ├─────────────────────┤  │  │
│  │          │  │ │时序特征  │ │  │ │ 时序模式异常检测   │  │  │
│  │          │  │ │采集器    │ │  │ │ (ITT分析)          │  │  │
│  │          │  │ ├──────────┤ │  │ ├─────────────────────┤  │  │
│  │          │  │ │Logprobs  │ │  │ │ Logprobs分布偏移   │  │  │
│  │          │  │ │采集器    │ │  │ │ (置换检验)         │  │  │
│  │          │  │ └──────────┘ │  │ └─────────────────────┘  │  │
│  └──────────┘  └──────────────┘  └───────────┬───────────────┘  │
│                                           │                      │
│  ┌────────────────────────────────────────┐│                      │
│  │         告警 & 可视化引擎              ││                      │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ││                      │
│  │  │ 弹窗告警  │ │ 仪表板   │ │ 日志   │ ││                      │
│  │  └──────────┘ └──────────┘ └────────┘ ││                      │
│  └────────────────────────────────────────┘│                      │
└───────────────────────────────────────────┼──────────────────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │  中转站 API      │
                                  └──────────────────┘
```

### 3.2 核心模块

#### 模块 1: SentinelProxy — 透明代理层

**职责**: 拦截用户→中转站的所有 API 请求/响应，零侵入部署

**技术选型**:

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **反向代理 (Python FastAPI/Go)** | 完全控制请求/响应，可采集所有信号 | 需要修改 API base_url | ⭐⭐⭐⭐⭐ |
| **MITM 代理 (mitmproxy)** | 无需修改客户端代码 | HTTPS 证书信任问题 | ⭐⭐⭐ |
| **OpenTelemetry SDK 注入** | 标准化，可对接任意后端 | 仅能采集有限元数据，无法获取完整响应文本 | ⭐⭐ |
| **浏览器插件** | 最简单的部署方式 | 仅限浏览器场景 | ⭐⭐ |

**推荐方案**: 基于 Python 的反向代理，复用现有开源项目：

- **go-llm-gateway** (Go): 生产级 API 网关，每个请求记录完整日志
- **llm-cost-monitor** (Python): 透明代理模式，零代码修改
- **OpenLLMetry** (SDK): 基于 OpenTelemetry 标准的可观测性方案

#### 模块 2: 指纹采集引擎

**2.1 文本指纹提取器**

基于 McGovern et al. (2025) 和 Suzuki et al. (2025) 的方法：

```python
# 特征提取管线
class TextFingerprintExtractor:
    def extract(self, response_text: str) -> FingerprintFeatures:
        return FingerprintFeatures(
            # 词 n-gram 特征 (n=2,3,4)
            word_ngrams=self._extract_word_ngrams(response_text, ns=[2,3,4]),
            # 字符 n-gram 特征 (n=3,4,5)
            char_ngrams=self._extract_char_ngrams(response_text, ns=[3,4,5]),
            # 词性 n-gram 特征 (n=2,3,4)
            pos_ngrams=self._extract_pos_ngrams(response_text, ns=[2,3,4]),
            # 词汇丰富度指标
            vocab_richness=self._calc_vocab_richness(response_text),
            # 句子长度统计
            sentence_stats=self._calc_sentence_stats(response_text),
            # 模型特征词频率 (slop words)
            slop_word_freq=self._calc_slop_word_freq(response_text),
            # 可读性指标
            readability_scores=self._calc_readability(response_text),
        )
```

**可复用的开源轮子**:

| 项目 | 用途 | 许可证 |
|------|------|--------|
| [lmscan](https://github.com/stef41/lmscan) | 零依赖文本指纹扫描，12项统计特征 | Apache-2.0 |
| [llm-idiosyncrasies](https://github.com/locuslab/llm-idiosyncrasies) | LLM2Vec 分类器，预训练模型已发布 | 开源 |
| [FDLLM](https://arxiv.org/abs/2501.16029) | LoRA 微调深度特征提取 | 学术论文 |

**2.2 元数据采集器**

```python
class MetadataCollector:
    def collect(self, response: APIResponse) -> MetadataFeatures:
        return MetadataFeatures(
            # OpenAI 专用
            system_fingerprint=response.get("system_fingerprint"),
            model_field=response.get("model"),
            service_tier=response.get("service_tier"),
            # Claude 专用
            thinking_signature=response.get("signature"),
            stop_reason=response.get("stop_reason"),
            # 通用
            response_id=response.get("id"),
            usage=response.get("usage"),
            # 时序
            ttft=response.time_to_first_token,  # 首 token 延迟
            total_latency=response.total_latency,
            token_timestamps=response.token_timestamps,  # 各 token 时间戳
        )
```

**2.3 Logprobs 采集器** (可选，需 API 支持)

```python
class LogprobsCollector:
    def collect(self, response: APIResponse) -> LogprobsFeatures:
        # 从响应中提取 logprobs 分布
        logprobs = response.get("logprobs", {})
        return LogprobsFeatures(
            top_token_logprobs=[t["logprob"] for t in logprobs.get("top_logprobs", [])],
            token_entropy=self._calc_entropy(logprobs),
            avg_logprob=np.mean([t["logprob"] for t in logprobs.get("top_logprobs", [])]),
        )
```

#### 模块 3: 多信号融合分析引擎

**核心思路**: 单一信号有局限，多信号融合可大幅提升检测精度和鲁棒性。

```python
class FusionAnalyzer:
    def __init__(self):
        self.model_family_classifier = load_llm2vec_classifier()  # 模型家族分类
        self.baseline_store = BaselineStore()  # 基线存储
        self.drift_detector = DriftDetector()  # 漂移检测

    def analyze(self, features: CombinedFeatures) -> AnalysisResult:
        # 信号 1: 模型家族分类
        family_probs = self.model_family_classifier.predict(features.text_fingerprint)

        # 信号 2: 与基线的文本指纹偏移
        baseline = self.baseline_store.get(features.model_label)
        fingerprint_drift = self.drift_detector.detect_fingerprint_drift(
            features.text_fingerprint, baseline.text_fingerprint
        )

        # 信号 3: 元数据异常
        metadata_anomaly = self.drift_detector.detect_metadata_change(
            features.metadata, baseline.metadata
        )

        # 信号 4: 时序模式偏移
        timing_drift = self.drift_detector.detect_timing_drift(
            features.timing, baseline.timing
        )

        # 信号 5: Logprobs 分布偏移 (如果可用)
        logprobs_drift = None
        if features.logprobs:
            logprobs_drift = self.drift_detector.detect_logprobs_drift(
                features.logprobs, baseline.logprobs
            )

        # 多信号融合决策
        return self._fuse_signals(
            family_probs, fingerprint_drift, metadata_anomaly,
            timing_drift, logprobs_drift
        )
```

**融合决策逻辑**:

| 信号 | 权重 | 触发条件 |
|------|------|---------|
| 模型家族分类 | 0.35 | Top-1 类别与声称模型不一致 |
| 文本指纹漂移 | 0.25 | KL散度超过动态阈值 |
| 元数据变更 | 0.20 | system_fingerprint/thinking_signature 变更或缺失 |
| 时序模式漂移 | 0.10 | ITT 分布统计检验 p < 0.05 |
| Logprobs 漂移 | 0.10 | 置换检验 p < 0.01 |

#### 模块 4: 告警引擎

```python
class AlertEngine:
    def check_and_alert(self, result: AnalysisResult):
        if result.risk_level == RiskLevel.HIGH:
            # 高风险: 弹窗提示 + 详细报告
            self.show_popup(result)
            self.log_alert(result)
        elif result.risk_level == RiskLevel.MEDIUM:
            # 中风险: 静默记录 + 仪表板标记
            self.log_warning(result)
            self.update_dashboard(result)
        else:
            # 低风险: 仅记录
            self.log_info(result)
```

### 3.3 技术栈

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| **代理层** | Python (FastAPI / httpx) 或 Go | FastAPI 异步支持好，Go 性能更优 |
| **文本指纹** | lmscan + llm-idiosyncrasies | 零依赖 + 预训练分类器 |
| **ML 推理** | PyTorch + HuggingFace Transformers | 加载 LLM2Vec/DeBERTa 预训练模型 |
| **统计检验** | scipy (KS检验、置换检验) | 成熟的统计工具库 |
| **时序分析** | numpy + 自定义 BiLSTM | 参考 "LLMs Have Rhythm" 论文 |
| **基线存储** | SQLite / JSON | 轻量级本地存储 |
| **告警 UI** | Electron / Web Dashboard | 跨平台桌面弹窗 |
| **日志** | Python logging + 结构化 JSON | 便于审计和分析 |

---

## 四、可复用的开源"轮子"

### 4.1 直接可用的组件

| 组件 | 开源项目 | 用途 | 许可证 |
|------|---------|------|--------|
| **透明代理** | [go-llm-gateway](https://github.com/shubhambakre/go-llm-gateway) | API 网关，完整请求日志 | 开源 |
| **透明代理** | [llm-cost-monitor](https://github.com/rizwan-rizu/llm-cost-monitor) | 零代码修改的透明代理 | 开源 |
| **可观测性** | [OpenLLMetry](https://github.com/traceloop/openllmetry) | OpenTelemetry SDK | 开源 |
| **文本指纹** | [lmscan](https://github.com/stef41/lmscan) | 12项统计特征，零依赖 | Apache-2.0 |
| **模型分类器** | [llm-idiosyncrasies](https://github.com/locuslab/llm-idiosyncrasies) | LLM2Vec 预训练分类器 (97.1%) | 开源 |
| **模型指纹** | [llm-fingerprinter](https://github.com/litemars/LLM-Fingerprinter) | 75个探针，402维特征 | MIT |
| **中转站审计** | [api-relay-audit](https://github.com/toby-bridges/api-relay-audit) | 13步审计流程 | MIT |
| **中转站检测** | [Veridrop](https://github.com/canarybyte/veridrop) | 12项检测，加密级验证 | AGPL-3.0 |
| **审计代码** | [llm-api-audit](https://github.com/sunblaze-ucb/llm-api-audit) | Berkeley 论文官方代码 | 开源 |
| **论文合集** | [Awesome-LLM-Fingerprinting](https://github.com/shaoshuo-ss/Awesome-LLM-Fingerprinting) | 持续更新的论文列表 | 开源 |

### 4.2 需要自行开发的部分

| 模块 | 工作量 | 难度 | 说明 |
|------|--------|------|------|
| 透明代理封装 | 2-3天 | 低 | 基于 llm-cost-monitor 或 go-llm-gateway 二次开发 |
| 指纹采集引擎 | 3-5天 | 中 | 集成 lmscan + 自定义特征提取 |
| 多信号融合引擎 | 5-7天 | 高 | 核心算法，需设计权重和决策逻辑 |
| 基线管理与漂移检测 | 3-5天 | 中 | 统计检验 + 动态阈值 |
| 告警 UI (弹窗) | 2-3天 | 低 | Electron 或 Web 弹窗 |
| 时序分析模块 | 3-5天 | 中 | 参考 "LLMs Have Rhythm" 论文实现 |
| **总计** | **~20-30天** | | 单人全职开发估算 |

---

## 五、局限性与风险

### 5.1 技术局限

| 局限 | 严重程度 | 缓解措施 |
|------|---------|---------|
| **无法检测量化降级** (纯文本) | 🔴 高 | 结合 logprobs 信号（如 API 支持） |
| **冷启动问题**: 需要先建立基线 | 🟡 中 | 首次使用时引导用户发送若干请求建立基线 |
| **模型版本迭代**: 模型更新会导致基线过时 | 🟡 中 | 定期自动更新基线 + 官方 API 对照验证 |
| **对抗性中转站**: 可识别并规避检测 | 🟡 中 | 多信号融合 + 随机化采样降低被识别概率 |
| **短文本指纹不稳定**: 短响应特征不足 | 🟡 中 | 设置最小文本长度阈值，短文本仅依赖元数据信号 |
| **多语言支持**: 中英文效果最好，小语种较弱 | 🟠 中低 | 优先支持中英文，逐步扩展 |

### 5.2 误报/漏报风险

| 场景 | 风险类型 | 概率 | 原因 |
|------|---------|------|------|
| 模型正常版本更新 | 误报 | 中 | 新版本可能改变输出风格 |
| 同家族不同规模 | 漏报 | 中 | GPT-4o vs GPT-4o-mini 区分精度有限 |
| 中转站随机化掺水 | 漏报 | 中高 | 按比例混合时统计信号被稀释 |
| 系统提示变更 | 误报 | 低 | 系统提示可能影响输出风格 |

### 5.3 UC Berkeley 论文的核心警告

> *"Our empirical analysis reveals that software-only methods are fundamentally unreliable: statistical tests on text outputs are query-intensive and fail against subtle substitutions."*
>
> — Cai et al., NeurIPS 2025 Workshop

这意味着：
- **纯文本被动方法不是银弹**，对细微替换（量化、小版本差异）存在根本性局限
- 但对于**跨家族替换**（最常见的作弊方式），准确率仍然很高 (95%+)
- 建议用户将本工具视为**辅助参考**而非**绝对判定**

---

## 六、开发计划

### 6.1 分阶段路线图

#### Phase 1: MVP (最小可行产品) — 预计 2 周

**目标**: 实现基础的跨家族模型替换检测

- [ ] 搭建透明代理框架（基于 FastAPI）
- [ ] 集成 lmscan 文本指纹提取
- [ ] 集成 llm-idiosyncrasies 模型家族分类器
- [ ] 实现元数据采集（system_fingerprint, model 字段等）
- [ ] 实现基础告警（控制台输出）
- [ ] 编写单元测试

**交付物**: 可运行的命令行工具，能检测 GPT↔Claude↔Gemini 等跨家族替换

#### Phase 2: 增强检测 — 预计 2 周

**目标**: 增加多信号融合和可视化

- [ ] 实现时序特征采集（TTFT, ITT）
- [ ] 实现基线管理和漂移检测
- [ ] 实现多信号融合决策引擎
- [ ] 开发 Web 仪表板（实时展示检测结果）
- [ ] 实现弹窗告警
- [ ] 支持 logprobs 采集（可选信号）

**交付物**: 带 Web UI 的完整检测系统

#### Phase 3: 生产化 — 预计 1-2 周

**目标**: 提升鲁棒性和用户体验

- [ ] 支持多种部署模式（本地代理、Docker、浏览器插件）
- [ ] 实现基线自动更新机制
- [ ] 优化误报率（动态阈值、历史平滑）
- [ ] 添加检测报告导出功能
- [ ] 性能优化（异步处理、缓存）
- [ ] 编写用户文档

**交付物**: 可分发的生产级工具

### 6.2 里程碑与验收标准

| 里程碑 | 验收标准 |
|--------|---------|
| M1: MVP | 能在 3 秒内完成单次响应的模型家族分类，准确率 >90% |
| M2: 增强版 | 跨家族替换检测准确率 >95%，误报率 <10% |
| M3: 生产版 | 支持 OpenAI/Claude/Gemini 三大协议，7×24 稳定运行 |

---

## 七、结论

### 7.1 可行性判定

| 维度 | 评估 | 说明 |
|------|------|------|
| **技术可行性** | ✅ **可行** | 跨家族替换检测有坚实的学术基础 (95%+ 准确率)，开源组件丰富 |
| **开发可行性** | ✅ **可行** | 核心开发量约 20-30 人天，有大量可复用的开源轮子 |
| **交付可行性** | ⚠️ **有条件可行** | 需明确以下前提（见下方） |

### 7.2 前提条件

1. **接受局限性**: 本工具无法检测量化降级（FP16→INT8），这是纯文本方法的根本性局限
2. **冷启动成本**: 首次使用需要先建立基线（建议至少 20-50 条正常响应）
3. **误报容忍**: 模型正常版本更新可能触发误报，需要人工确认机制
4. **部署方式**: 需要用户将 API base_url 指向本地代理（或安装浏览器插件）

### 7.3 最终建议

> **推荐开发**。虽然纯文本被动方法存在量化检测的盲区，但对于中转站最常见的作弊方式——**跨家族模型替换**（如声称 GPT-4 实际用 Claude/Gemini/开源模型）——检测精度很高 (95%+)。结合元数据信号和时序分析，可以构建一个实用的、低成本的持续监控系统。建议以 MVP 方式快速验证，再根据实际效果迭代。

---

## 八、参考文献

1. Sun et al., *"Idiosyncrasies in Large Language Models"*, CMU/Berkeley, arXiv:2502.12150, 2025
2. Fu et al., *"FDLLM: A Dedicated Detector for Black-Box LLMs Fingerprinting"*, arXiv:2501.16029, 2025
3. McGovern et al., *"Your Large Language Models Are Leaving Fingerprints"*, GenAIDetect 2025
4. Suzuki et al., *"Natural Fingerprints of Large Language Models"*, arXiv:2504.14871, 2025
5. Cai et al., *"Are You Getting What You Pay For? Auditing Model Substitution in LLM APIs"*, UC Berkeley, NeurIPS 2025 Workshop, arXiv:2504.04715
6. Chauvin et al., *"Log Probability Tracking of LLM APIs"*, ICLR 2026, arXiv:2512.03816
7. Chauvin et al., *"Token-Efficient Change Detection in LLM APIs (B3IT)"*, ICML 2026, arXiv:2602.11083
8. Alhazbi et al., *"LLMs Have Rhythm: Fingerprinting Large Language Models Using Inter-Token Times"*, IEEE OJCOMS 2025, arXiv:2502.20589
9. Pasquini et al., *"LLMmap: Fingerprinting for Large Language Models"*, USENIX Security 2025
10. Tsai et al., *"RoFL: Robust Fingerprinting of Language Models"*, Meta/Columbia, arXiv:2505.12682, 2025
11. Kirchenbauer et al., *"A Watermark for Large Language Models"*, ICML 2023
12. Gao et al., *"Model Equality Testing: Which Model Is This API Serving?"*, ICLR 2025
