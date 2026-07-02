# PJ-AGENT-2: 带选择性长期记忆的对话型 LLM Agent

复旦大学 人工智能导论课程项目。

## 项目简介

本项目实现了一个具备**选择性长期记忆**的对话 Agent，核心思路是模拟人类记忆的"选择写入 + 遗忘淘汰"机制，而非将全部对话历史无差别地写入记忆库。

Agent 支持五种记忆模式，用于对比实验：

| 模式 | 代号 | 说明 |
|------|------|------|
| no_memory | G1 | 无记忆基线，每轮独立 |
| short_term | G2 | 仅短期滑动窗口记忆（N=6） |
| long_term | G3 | 完整长期记忆（选择写入 + 遗忘淘汰 + 去重） |
| long_term_no_forgetting | G4A | 消融实验：关闭遗忘，只存不删 |
| long_term_no_selection | G4B | 消融实验：关闭选择，全量写入 |

### 记忆流水线

每轮对话经过四个阶段：

1. **规则层过滤**：长度 → 句式 → 信息密度，三道过滤决定是否写入记忆
2. **检索触发**：用户输入含召回信号词时查询长期记忆，同时每 N 轮兜底触发
3. **LLM 三元组抽取**：从对话中提取 `{主语, 关系, 宾语}` 结构化三元组，附带 1-5 重要性评分
4. **向量库管理**：基于 FAISS 做语义去重，容量满时淘汰低重要性条目

## 项目结构

```
├── 实验_主数据集.py          # 主实验入口，五组对比
├── config.yaml               # LLM、记忆、评估参数配置
├── requirements.txt          # Python 依赖
├── data/
│   ├── conversation_tests.jsonl   # 38 组多轮对话测试用例（四类分层）
│   └── generate_tests.py          # 测试用例生成脚本
└── src/
    ├── agent/                # Agent 五种记忆配置实现
    │   ├── base.py           # 抽象基类
    │   └── agents.py         # G1-G4B 五个子类
    ├── memory/               # 记忆系统核心
    │   ├── base.py           # 抽象记忆接口
    │   ├── no_memory.py      # 空记忆（G1）
    │   ├── short_term.py     # 滑动窗口短期记忆（G2）
    │   ├── long_term.py      # 选择性长期记忆（G3/G4）
    │   └── vector_store.py   # FAISS 三元组向量库
    ├── llm/                  # DeepSeek API 客户端
    ├── embedding/            # SentenceTransformer 编码器
    ├── evaluation/           # 自动判分 & 遗忘率指标
    │   ├── judge.py          # 确定性字符串匹配判定器
    │   └── metrics.py        # 双口径遗忘率计算
    ├── config/               # YAML 配置加载
    └── logger/               # 结构化 JSONL 日志
```

## 快速开始

### 环境要求

- Python 3.10+
- DeepSeek API Key

### 安装

```bash
pip install -r requirements.txt
```

### 配置

在环境变量中设置 DeepSeek API Key：

```bash
export DEEPSEEK_API_KEY="your-api-key"
```

其他参数（温度、窗口大小、向量库容量等）在 `config.yaml` 中调整。

### 运行

```bash
# 全部五组对比实验
python 实验_主数据集.py

# 仅运行一组
python 实验_主数据集.py --mode long_term

# 仅测试单条用例
python 实验_主数据集.py --test conv_001
```

结果输出到 `results/`，日志输出到 `data/agent_logs/`。

## 测试数据集

38 组中文多轮对话测试用例，分四类：

- **事实分散记忆**（12 组）：用户身份、偏好、健康等信息分散在多轮不同话题中
- **渐进更新/覆盖**（10 组）：同一信息经多次修正（如职业变更、年龄更正）
- **跨话题干扰**（8 组）：多话题交替切换，检测跨话题召回能力
- **负面样本**（8 组）：寒暄、知识查询等不应触发记忆写入的场景

## 评估指标

- **一致性率（Consistency Rate）**：检核轮中 Agent 回复与预设事实的匹配率
- **遗忘率 B（全口径）**：所有预设事实中未被正确回忆的比例（主指标）
- **遗忘率 A（应记未记）**：仅统计已确认识别并写入的事实的丢失率（分析用）
