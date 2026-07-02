# PJ-AGENT-2: 带长期记忆的对话型 LLM Agent

## 项目简介

本项目实现了一个具备选择性长期记忆的对话型 Agent——模拟人类「有选择性地记忆与遗忘」的特点。基于 DeepSeek API 实现对话交互，FAISS 向量库存储结构化三元组记忆，比较五种记忆配置下的多轮对话表现。code文件夹内为最新最终版的实验代码。

## 核心创新

现有的大多数「记忆 Agent」本质上是 RAG（将所有历史全量存入向量库后检索）。本项目实现的是**选择性记忆**：Agent 通过规则层过滤 + LLM 精判，主动判断「什么值得记住」，并通过重要性衰减机制主动淘汰冗余记忆。

## 技术要求

- Python 3.8+
- DeepSeek API Key（设置环境变量 `DEEPSEEK_API_KEY`）

## 安装

```bash
cd Project_AGENT_2_GroupXX
pip install -r requirements.txt

# Windows
set DEEPSEEK_API_KEY=sk-your-key-here

# Linux/Mac
export DEEPSEEK_API_KEY=sk-your-key-here
```

## 运行

### 生成测试集（首次运行前）
```bash
python data/generate_tests.py
```

### 完整评估（五种模式，38 组测试）
```bash
python run.py
```

### 仅运行一种模式
```bash
python run.py --mode long_term
python run.py --mode long_term_no_forgetting
python run.py --mode long_term_no_selection
python run.py --mode short_term
python run.py --mode no_memory
```

### 调试单个测试
```bash
python run.py --mode long_term --test conv_001 --skip-eval
python run.py --debug
```

## 五种 Agent 模式

| 模式 | 参数 | 说明 |
|------|------|------|
| 无记忆 (G1) | `no_memory` | 每轮独立，无法回忆任何历史 |
| 仅短期 (G2) | `short_term` | N=6 滑动窗口，超出遗忘 |
| 完整长期 (G3) | `long_term` | 选择写入 + 遗忘淘汰 + 去重 |
| 无遗忘 (G4A) | `long_term_no_forgetting` | 只存不删（消融：验证遗忘机制价值） |
| 无选择 (G4B) | `long_term_no_selection` | 全量写入（消融：验证选择机制价值 → 退化 RAG） |

## 评估指标

 **多轮一致性**：检核问题 × 可接受答案字符串匹配判定
 信息遗忘率（双口径）：
   遗忘率 B（全口径，主指标）：所有预设事实的丢失率
  -遗忘率 A（分析用）：仅已确认写入的事实的丢失率

## 项目结构

```
Project_AGENT_2_GroupXX/
├── config.yaml                  # 集中配置
├── run.py                       # 主入口
├── requirements.txt
├── README.md
├── CONTEXT.md                   # 术语表
├── docs/adr/                    # 架构决策记录
├── src/
│   ├── config/loader.py         # 配置加载
│   ├── llm/deepseek_client.py   # DeepSeek API
│   ├── embedding/encoder.py     # text2vec 封装
│   ├── memory/
│   │   ├── base.py              # MemoryStore 抽象
│   │   ├── no_memory.py         # 空记忆
│   │   ├── short_term.py        # 滑动窗口
│   │   ├── vector_store.py      # 三元组向量库
│   │   └── long_term.py         # 选择性长期记忆
│   ├── agent/
│   │   ├── base.py              # BaseAgent
│   │   └── agents.py            # 五种 Agent
│   ├── evaluation/
│   │   ├── judge.py             # 自动化判定
│   │   └── metrics.py           # 指标计算
│   └── logger/agent_logger.py   # 日志
├── data/
│   ├── generate_tests.py        # 测试生成
│   └── conversation_tests.jsonl # 38 组测试
├── memory_store/
└── results/
```

## 复现步骤

1. 安装依赖: `pip install -r requirements.txt`
2. 设置 API Key
3. 生成测试集: `python data/generate_tests.py`
4. 运行完整评估: `python run.py`
5. 查看结果: `results/eval_summary.json`

