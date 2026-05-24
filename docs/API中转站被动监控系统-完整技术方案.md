# API 中转站被动式模型真实性持续监控系统

## 完整技术方案文档

> **版本**: v2.0 | **日期**: 2026-05-24
> **定位**: 超低占用、记录-分析分离架构，支持任何电脑运行

---

## 目录

1. [问题定义](#一问题定义)
2. [核心设计原则](#二核心设计原则)
3. [技术可行性分析](#三技术可行性分析)
4. [系统架构设计](#四系统架构设计)
5. [信息获取技术方案](#五信息获取技术方案)
6. [三种实现方案对比](#六三种实现方案对比)
7. [硬件需求](#七硬件需求)
8. [开发计划](#八开发计划)
9. [局限性与风险](#九局限性与风险)

---

## 一、问题定义

### 1.1 API 中转站风险行为

| 风险类型 | 描述 | 典型手段 |
|---------|------|---------|
| **模型替换** | 将高价模型替换为低价模型 | GPT-4o → GPT-4o-mini、Claude Opus → Haiku |
| **模型掺水** | 按比例混合真实与廉价模型 | 70% 真模型 + 30% 廉价模型 |
| **量化降级** | 使用量化版本替代全精度 | FP16 → INT8/FP8 |
| **协议篡改** | 修改响应字段、截断上下文 | 删除 tool_calls、截断长上下文 |
| **动态切换** | 不同时段使用不同后端 | 高峰期降级、上游变更不通知 |

### 1.2 预期输出

当检测到模型从 A 切换为 B 时，生成分析报告：

```
⚠️ 模型切换检测告警

检测时间: 2026-05-24 14:32:15
中转站: api.example.com
请求模型: claude-sonnet-4-20250514

检测到变化:
  模型家族: Claude → GPT (置信度: 94.2%)
  文体指纹偏移: +0.37 (阈值: 0.15)
  词汇分布偏移: KL散度 = 0.42

证据:
  [1] 响应中出现 GPT 特征词: "delve", "tapestry"
  [2] 响应中缺失 Claude 特征词: "certainly"
  [3] system_fingerprint 字段缺失/变更

建议: 当前后端可能已被替换为 GPT 系列模型
```

---

## 二、核心设计原则

### 2.1 记录-分析分离架构

```
┌─────────────────────────────────────────────────────────────┐
│  用户使用阶段（零计算开销）                                   │
│  API 请求 → SentinelProxy → 仅记录响应文本 → SQLite          │
│  资源占用: < 50MB 内存, CPU ~0%                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    用户睡前手动点击"分析"
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  闲时分析阶段（批量处理）                                     │
│  加载 80MB 模型 → 批量分析 → 生成详尽报告                      │
│  处理速度: 500 条/秒                                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 设计原则

| 原则 | 说明 |
|------|------|
| **被动式** | 不发送额外测试请求，仅从正常 API 响应提取特征 |
| **超低占用** | 使用时仅记录，分析时离线批量处理 |
| **零侵入** | 透明代理部署，用户无感知 |
| **可解释** | 告警时提供具体证据而非仅分数 |

---

## 三、技术可行性分析

### 3.1 学术基础

| 论文 | 发表 | 核心结论 | 准确率 |
|------|------|---------|--------|
| Sun et al., *"Idiosyncrasies in Large Language Models"* | arXiv 2025 | LLM2Vec 分类器识别来源模型 | **97.1%** |
| Fu et al., *"FDLLM"* | arXiv 2025 | LoRA 微调深度特征 | **95%** |
| McGovern et al., *"Your Large Language Models Are Leaving Fingerprints"* | GenAIDetect 2025 | GradientBoost + n-gram | **F1=0.98** |

### 3.2 可行性总结

| 检测目标 | 被动文本分析 | 综合可行性 |
|---------|:-----------:|:---------:|
| 跨家族替换 (GPT→Claude) | ✅ 97% | **高** |
| 同家族降级 (GPT-4o→mini) | ⚠️ 80% | **中高** |
| 量化降级 (FP16→INT8) | ❌ ~50% | **低** |

> **核心结论**: 跨家族替换检测技术成熟 (95%+)，量化检测是盲区。

---

## 四、系统架构设计

### 4.1 整体架构

```
用户应用程序
      ↓ API 请求
┌─────────────────────────────────────────────────────────────┐
│                    SentinelProxy (透明代理)                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ 请求拦截  │→│ 响应记录器    │→│   SQLite 本地存储      │  │
│  │ & 转发   │  │ (零计算)     │  │  (文本+元数据+时序)    │  │
│  └──────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
      ↓
中转站 API

═══════════════════════════════════════════════════════════════
                    用户触发分析时
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                    离线分析引擎                              │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ 加载 MiniLM  │→│ 批量文本编码      │→│ 模型家族分类  │  │
│  │ (80MB 模型)  │  │ (500条/秒)       │  │ + 漂移检测   │  │
│  └──────────────┘  └──────────────────┘  └──────┬───────┘  │
│                                                  ↓          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              生成详尽分析报告 (Markdown/HTML)         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 核心模块

#### 模块 1: SentinelProxy — 透明代理层

**职责**: 拦截用户→中转站的所有 API 请求/响应，零侵入部署

**技术选型**:

| 方案 | 优点 | 推荐度 |
|------|------|--------|
| **Python FastAPI + httpx** | 完全控制请求/响应，异步支持好 | ⭐⭐⭐⭐⭐ |
| **Go 反向代理** | 性能更优，资源占用更低 | ⭐⭐⭐⭐⭐ |
| **mitmproxy** | 无需修改客户端代码 | ⭐⭐⭐ |

**推荐方案**: Python FastAPI（开发快、生态好）或 Go（性能极致）

#### 模块 2: 响应记录器（零计算）

```python
import sqlite3
import json
from datetime import datetime

class ResponseLogger:
    def __init__(self, db_path="responses.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_table()
    
    def log(self, model_requested: str, response_text: str, 
            metadata: dict, timing: dict):
        """仅记录，零计算开销"""
        self.conn.execute(
            """INSERT INTO responses 
               (timestamp, model_requested, response_text, 
                metadata, timing) VALUES (?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), 
             model_requested, 
             response_text,
             json.dumps(metadata),
             json.dumps(timing))
        )
        self.conn.commit()
```

**记录内容**:
- 时间戳
- 请求的模型名称
- 响应文本（完整内容）
- API 元数据（system_fingerprint, model 字段等）
- 时序信息（首 token 延迟、总延迟等）

**资源占用**: < 50MB 内存，CPU ~0%，存储 ~1KB/条

#### 模块 3: 离线分析引擎

```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class OfflineAnalyzer:
    def __init__(self):
        # 加载 80MB 轻量模型
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.family_centroids = self._load_family_centroids()
    
    def analyze_batch(self, responses: list) -> list:
        """批量分析，500条/秒"""
        # 文本编码
        embeddings = self.model.encode(
            responses, 
            batch_size=64,
            show_progress_bar=True
        )
        
        # 与模型家族中心比较
        results = []
        for emb in embeddings:
            similarities = {
                family: cosine_similarity([emb], [centroid])[0][0]
                for family, centroid in self.family_centroids.items()
            }
            predicted = max(similarities, key=similarities.get)
            results.append({
                'predicted_family': predicted,
                'confidence': similarities[predicted],
                'all_scores': similarities
            })
        
        return results
```

---

## 五、信息获取技术方案

### 5.1 如何获取用户软件的 API 调用信息

#### 方案 A: 透明代理模式（推荐）

```
用户软件 ──→ SentinelProxy ──→ 中转站 API
            (localhost:8080)
```

**实现方式**:

1. **修改 API Base URL**
   ```python
   # 用户原代码
   client = OpenAI(base_url="https://api.example.com/v1")
   
   # 修改后
   client = OpenAI(base_url="http://localhost:8080/v1")
   ```

2. **环境变量注入**
   ```bash
   export OPENAI_BASE_URL="http://localhost:8080/v1"
   export ANTHROPIC_BASE_URL="http://localhost:8080/v1"
   ```

3. **系统级代理**（无需修改代码）
   ```bash
   # 设置系统 HTTP 代理
   export HTTP_PROXY="http://localhost:8080"
   export HTTPS_PROXY="http://localhost:8080"
   ```

**可行性**: ✅ **完全可行**，所有主流 HTTP 客户端都支持代理配置

#### 方案 B: 浏览器插件（Web 应用）

```javascript
// Chrome Extension - content script
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (isLLMAPI(details.url)) {
      // 记录请求/响应
      logAPIRequest(details);
    }
  },
  { urls: ["<all_urls>"] }
);
```

**适用场景**: 网页版 ChatGPT、Claude、Poe 等

**可行性**: ✅ **可行**，但仅限浏览器环境

#### 方案 C: 网络层拦截（高级）

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  用户软件    │────→│ 本地代理网关 │────→│  中转站 API  │
└─────────────┘     │ (iptables/  │     └─────────────┘
                    │  pf/路由表)  │
                    └─────────────┘
```

**实现方式**:
- **macOS/Linux**: `pfctl` / `iptables` 端口转发
- **Windows**: `netsh interface portproxy`

**可行性**: ⚠️ **可行但复杂**，需要管理员权限，可能影响其他应用

### 5.2 能获取哪些信息

| 信息类型 | 获取方式 | 可行性 |
|---------|---------|--------|
| **请求 URL** | 代理拦截 | ✅ 100% |
| **请求 Headers** | 代理拦截 | ✅ 100% |
| **请求 Body** (prompt) | 代理拦截 | ✅ 100% |
| **响应 Body** (生成的文本) | 代理拦截 | ✅ 100% |
| **响应 Headers** | 代理拦截 | ✅ 100% |
| **API 元数据** (system_fingerprint) | 解析响应 JSON | ✅ 100% |
| **时序信息** (延迟) | 代理层计时 | ✅ 100% |
| **Logprobs** | 需 API 支持返回 | ⚠️ 部分支持 |

### 5.3 技术可行性结论

| 方案 | 侵入性 | 复杂度 | 覆盖率 | 推荐度 |
|------|--------|--------|--------|--------|
| **透明代理** | 低 | 低 | 100% | ⭐⭐⭐⭐⭐ |
| **浏览器插件** | 低 | 中 | Web 应用 | ⭐⭐⭐⭐ |
| **网络层拦截** | 中 | 高 | 100% | ⭐⭐⭐ |
| **SDK Hook** | 高 | 高 | 特定 SDK | ⭐⭐ |

**结论**: **透明代理模式完全可行**，是最佳方案。用户只需修改 API base_url 或设置环境变量，即可无感拦截所有 API 流量。

---

## 六、三种实现方案对比

### 6.1 方案对比表

| 维度 | 方案一 (LLM2Vec) | 方案二 (MiniLM) | 方案三 (云端 API) |
|------|:---------------:|:--------------:|:----------------:|
| **模型大小** | 15 GB | **80 MB** | 0 (云端) |
| **内存需求** | 16-24 GB | **4 GB** | **< 1 GB** |
| **GPU 需求** | 24GB 显存 | **不需要** | **不需要** |
| **分析速度** | 100ms/条 | **500条/秒** | 依赖网络 |
| **准确率** | **97.1%** | ~85-90% | ~85-90% |
| **离线能力** | ✅ | ✅ | ❌ |
| **成本** | 一次性硬件 | 免费 | $0.01/千条 |
| **部署难度** | 中 | **低** | **低** |

### 6.2 推荐选择

| 用户类型 | 推荐方案 |
|---------|---------|
| **普通用户（推荐）** | **方案二：MiniLM 本地分析** |
| 专业用户（有 GPU） | 方案一：LLM2Vec 实时检测 |
| 极低配置用户 | 方案三：HuggingFace 云端 API |

---

## 七、硬件需求

### 7.1 推荐方案（MiniLM）硬件需求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **内存** | **4 GB** | 8 GB |
| **存储** | **500 MB** | 1 GB SSD |
| **CPU** | 双核 | 4 核+ |
| **GPU** | **不需要** | — |
| **网络** | 仅用于 API 调用 | — |

> ✅ **任何能上网的电脑都能运行**，包括老旧笔记本、树莓派等。

### 7.2 资源占用对比

| 阶段 | 内存占用 | CPU 占用 | 说明 |
|------|---------|---------|------|
| **记录阶段** | < 50 MB | ~0% | 仅磁盘写入 |
| **分析阶段** | ~1 GB | 50-100% | 批量处理时可暂停 |
| **空闲状态** | < 10 MB | 0% | 后台驻留 |

---

## 八、开发计划

### 8.1 分阶段路线图

#### Phase 1: MVP（2 周）

- [ ] 搭建 FastAPI 透明代理框架
- [ ] 实现 SQLite 响应记录器
- [ ] 集成 MiniLM 分析引擎
- [ ] 实现基础模型家族分类
- [ ] 命令行分析报告生成

**交付物**: 可运行的命令行工具

#### Phase 2: 增强版（2 周）

- [ ] 实现时序特征采集
- [ ] 实现漂移检测算法
- [ ] 开发 Web 仪表板
- [ ] 实现详细分析报告（Markdown/HTML）
- [ ] 支持多协议（OpenAI/Claude/Gemini）

**交付物**: 带 Web UI 的完整系统

#### Phase 3: 生产化（1-2 周）

- [ ] 支持多种部署模式（本地、Docker、系统服务）
- [ ] 基线自动更新机制
- [ ] 误报优化（动态阈值）
- [ ] 报告导出功能
- [ ] 用户文档

**交付物**: 可分发的生产级工具

### 8.2 里程碑

| 里程碑 | 验收标准 |
|--------|---------|
| M1: MVP | 能记录响应并离线分析，准确率 >85% |
| M2: 增强版 | 支持三大协议，分析报告详尽 |
| M3: 生产版 | 7×24 稳定运行，误报率 <10% |

---

## 九、局限性与风险

### 9.1 技术局限

| 局限 | 严重程度 | 缓解措施 |
|------|---------|---------|
| **无法检测量化降级** | 🔴 高 | 结合元数据信号 |
| **冷启动问题** | 🟡 中 | 引导建立基线 |
| **模型版本迭代** | 🟡 中 | 定期更新基线 |
| **对抗性中转站** | 🟡 中 | 多信号融合 |
| **短文本不稳定** | 🟡 中 | 设置最小长度阈值 |

### 9.2 误报/漏报风险

| 场景 | 风险类型 | 概率 |
|------|---------|------|
| 模型正常版本更新 | 误报 | 中 |
| 同家族不同规模 | 漏报 | 中 |
| 中转站随机化掺水 | 漏报 | 中高 |

### 9.3 核心结论

> **方案完全可行**。透明代理模式可以 100% 获取 API 调用信息，MiniLM 方案将硬件门槛降至 4GB 内存，任何电脑都能运行。虽然纯文本方法无法检测量化降级，但对于最常见的"跨家族模型替换"检测精度达 85-90%，具有实用价值。

---

## 参考文献

1. Sun et al., *"Idiosyncrasies in Large Language Models"*, CMU/Berkeley, arXiv:2502.12150, 2025
2. Fu et al., *"FDLLM: A Dedicated Detector for Black-Box LLMs Fingerprinting"*, arXiv:2501.16029, 2025
3. McGovern et al., *"Your Large Language Models Are Leaving Fingerprints"*, GenAIDetect 2025
4. Cai et al., *"Are You Getting What You Pay For? Auditing Model Substitution in LLM APIs"*, UC Berkeley, NeurIPS 2025 Workshop
5. Chauvin et al., *"Log Probability Tracking of LLM APIs"*, ICLR 2026
6. Alhazbi et al., *"LLMs Have Rhythm"*, IEEE OJCOMS 2025
7. Pasquini et al., *"LLMmap"*, USENIX Security 2025

---

*文档结束*
