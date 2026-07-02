#!/usr/bin/env python
"""
实验一：主数据集实验（自有38组测试 + 五种Agent模式）

实验组:
  G1: no_memory                  — 无记忆基线
  G2: short_term                 — 仅短期 N=6
  G3: long_term                  — 完整长期记忆（选择写入 + 遗忘淘汰 + 去重）
  G4A: long_term_no_forgetting   — 消融：无遗忘（只存不删）
  G4B: long_term_no_selection    — 消融：无选择（全量写入）

数据集: data/conversation_tests.jsonl (38组，四类分层)
配置:   config.yaml
输出:   results/ (eval_summary.json + comparison_table.md)

用法:
    python 实验_主数据集.py                          # 全部 5 组
    python 实验_主数据集.py --mode long_term         # 仅一组
    python 实验_主数据集.py --test conv_001          # 单个测试
    python 实验_主数据集.py --mode long_term --test conv_001
"""

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from typing import Dict, List, Optional

import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
os.environ["PYTHONHASHSEED"] = str(SEED)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from src.config.loader import load_config, Config
from src.llm.deepseek_client import DeepSeekClient
from src.embedding.encoder import EmbeddingEncoder
from src.memory.no_memory import NoMemory
from src.memory.short_term import ShortTermMemory
from src.memory.vector_store import TripleVectorStore
from src.memory.long_term import LongTermMemory
from src.agent.agents import (
    NoMemoryAgent,
    ShortTermAgent,
    LongTermAgent,
    NoForgettingAgent,
    NoSelectionAgent,
)
from src.evaluation.judge import AutomatedJudge
from src.evaluation.metrics import (
    compute_consistency_from_checklist,
    compute_forgetting_rate,
    generate_comparison_table,
)
from src.logger.agent_logger import AgentLogger


# ═══════════════════════════════════════════════════════════════════════
# Agent 工厂
# ═══════════════════════════════════════════════════════════════════════

def create_agent(mode: str, config: Config, llm_client: DeepSeekClient) -> tuple:
    window_size = config.memory.short_term_window_size
    capacity = config.memory.long_term_capacity
    embed_model = config.memory.embedding_model
    top_k = config.memory.top_k_retrieval
    dedup_thr = config.memory.dedup_semantic_threshold
    auto_intv = config.memory.retrieval_auto_trigger_interval
    min_len = config.rule_filter.min_input_length
    min_ent = config.rule_filter.info_density_min_entities

    if mode == "no_memory":
        memory = NoMemory()
        agent = NoMemoryAgent(llm_client=llm_client, memory=memory, agent_mode="no_memory",
                              agent_temperature=config.llm.temperature_agent)
    elif mode == "short_term":
        memory = ShortTermMemory(window_size=window_size)
        agent = ShortTermAgent(llm_client=llm_client, memory=memory, agent_mode="short_term",
                               agent_temperature=config.llm.temperature_agent)
    elif mode in ("long_term", "long_term_no_forgetting", "long_term_no_selection"):
        encoder = EmbeddingEncoder(model_name=embed_model)
        short_term = ShortTermMemory(window_size=window_size)
        triple_store = TripleVectorStore(encoder=encoder, top_k=top_k, capacity=capacity,
                                         dedup_threshold=dedup_thr)
        variant_map = {
            "long_term": "full",
            "long_term_no_forgetting": "no_forgetting",
            "long_term_no_selection": "no_selection",
        }
        memory = LongTermMemory(short_term=short_term, triple_store=triple_store,
                                llm_client=llm_client, variant=variant_map[mode],
                                retrieval_auto_interval=auto_intv,
                                min_input_length=min_len, min_entities=min_ent)
        agent_cls_map = {
            "long_term": LongTermAgent,
            "long_term_no_forgetting": NoForgettingAgent,
            "long_term_no_selection": NoSelectionAgent,
        }
        agent = agent_cls_map[mode](llm_client=llm_client, memory=memory, agent_mode=mode,
                                    agent_temperature=config.llm.temperature_agent)
    else:
        raise ValueError(f"Unknown mode: {mode}")
    return agent, memory


# ═══════════════════════════════════════════════════════════════════════
# 对话运行器
# ═══════════════════════════════════════════════════════════════════════

def run_conversation(agent, test_case: Dict, logger: AgentLogger, mode: str) -> List[Dict]:
    agent.reset()
    test_id = test_case["test_id"]
    turn_logs = []

    for turn_data in test_case["turns"]:
        turn_num = turn_data["turn"]
        user_input = turn_data["user"]

        t0 = time.time()
        response = agent.respond(user_input)
        latency_ms = (time.time() - t0) * 1000

        log_data = agent.get_log_data(user_input, response, latency_ms)

        retrieved = ""
        if hasattr(agent.memory, "retrieve_context"):
            retrieved = agent.memory.retrieve_context(user_input)

        logger.log_turn(
            test_id=test_id, agent_mode=mode, turn=turn_num,
            user_input=user_input, llm_response=response,
            latency_ms=latency_ms,
            memory_snapshot=log_data.get("memory_snapshot", {}),
            retrieved_context=retrieved,
        )

        turn_logs.append({
            "test_id": test_id, "turn": turn_num,
            "user": user_input, "response": response,
            "latency_ms": latency_ms, "retrieved_context": retrieved,
            "checklist": turn_data.get("checklist", []),
            "expected_facts_introduced": turn_data.get("expected_facts_introduced", []),
        })

    return turn_logs


# ═══════════════════════════════════════════════════════════════════════
# 评估运行器
# ═══════════════════════════════════════════════════════════════════════

def evaluate_conversation(turn_logs: List[Dict], judge: AutomatedJudge,
                          logger: AgentLogger, mode: str):
    checklist_results = []
    retention_results = []

    for log in turn_logs:
        checklist = log.get("checklist", [])
        if not checklist:
            continue

        results = judge.evaluate_turn(agent_response=log["response"], checklist=checklist)
        for i, r in enumerate(results):
            r["test_id"] = log["test_id"]
            r["turn"] = log["turn"]
            logger.log_evaluation(log["test_id"], log["turn"], f"check_{i}", r)

        checklist_results.append({
            "test_id": log["test_id"], "turn": log["turn"], "results": results,
        })

        for r in results:
            retention_results.append({
                "test_id": log["test_id"], "fact": r["fact"],
                "introduced_at_turn": 1, "checked_at_turn": log["turn"],
                "delta": log["turn"] - 1, "consistent": r["consistent"],
                "was_written": True,
            })

    return checklist_results, retention_results


# ═══════════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════════

def run_evaluation(config: Config, mode_filter: Optional[str] = None,
                   test_filter: Optional[str] = None, skip_eval: bool = False):
    print("=" * 60)
    print("  实验一：主数据集实验 — 自有38组测试")
    print("=" * 60)
    print(f"  配置: config.yaml")
    print(f"  数据集: data/conversation_tests.jsonl")
    print()

    # 加载测试集
    test_path = os.path.join(PROJECT_DIR, config.paths.test_file)
    if not os.path.exists(test_path):
        print(f"[ERROR] 测试集不存在: {test_path}")
        print("  请先运行: python data/generate_tests.py")
        sys.exit(1)

    with open(test_path, "r", encoding="utf-8") as f:
        all_test_cases = [json.loads(line) for line in f if line.strip()]

    if test_filter:
        all_test_cases = [tc for tc in all_test_cases if tc["test_id"] == test_filter]
        if not all_test_cases:
            print(f"[ERROR] 未找到测试: '{test_filter}'")
            sys.exit(1)

    print(f"[INFO] 加载 {len(all_test_cases)} 条测试用例")

    cat_counts = Counter(tc["category"] for tc in all_test_cases)
    for cat, cnt in sorted(cat_counts.items()):
        print(f"  - {cat}: {cnt}")
    print()

    # 确定运行模式
    ALL_MODES = ["no_memory", "short_term", "long_term",
                 "long_term_no_forgetting", "long_term_no_selection"]
    modes_to_run = [mode_filter] if mode_filter else ALL_MODES

    # 创建 LLM 客户端
    agent_llm = DeepSeekClient(
        api_key=config.llm.api_key, base_url=config.llm.base_url,
        model=config.llm.model, temperature=config.llm.temperature_agent,
        max_tokens=config.llm.max_tokens, max_retries=config.llm.max_retries,
        retry_backoff_seconds=config.llm.retry_backoff_seconds,
    )

    judge = AutomatedJudge() if not skip_eval else None
    all_results = {}

    for mode in modes_to_run:
        print(f"{'─' * 40}")
        print(f"[MODE] {mode}")
        print(f"{'─' * 40}")

        agent, memory = create_agent(mode, config, agent_llm)
        print(f"[INFO] Agent: {agent.__class__.__name__}")

        log_file = os.path.join(PROJECT_DIR, config.paths.log_dir, f"{mode}.jsonl")
        if os.path.exists(log_file):
            os.remove(log_file)
        logger = AgentLogger(log_file)

        all_checklist = []
        all_retention = []
        total_latency = 0.0
        total_turns = 0

        for tc_idx, test_case in enumerate(all_test_cases, 1):
            test_id = test_case["test_id"]
            print(f"  [{tc_idx}/{len(all_test_cases)}] {test_id}: "
                  f"{test_case['title']} ... ", end="", flush=True)

            try:
                turn_logs = run_conversation(agent, test_case, logger, mode)
                total_turns += len(turn_logs)
                total_latency += sum(tl["latency_ms"] for tl in turn_logs)

                if not skip_eval:
                    c_results, r_results = evaluate_conversation(
                        turn_logs, judge, logger, mode)
                    all_checklist.extend(c_results)
                    all_retention.extend(r_results)

                print("OK")

            except Exception as e:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()

            time.sleep(0.5)

        # 保存记忆状态
        if mode.startswith("long_term"):
            store_dir = os.path.join(PROJECT_DIR, config.paths.memory_store_dir)
            memory.save(store_dir)
            print(f"[INFO] Memory store saved to {store_dir}")

        # 计算指标
        if not skip_eval and all_checklist:
            c_metrics = compute_consistency_from_checklist(all_checklist)
            f_metrics = compute_forgetting_rate(
                per_fact_results=all_retention,
                delta_bins=config.evaluation.forgetting.delta_bins,
            )
        else:
            c_metrics = {"rate": 0, "total_checks": 0, "passed": 0, "failed": 0}
            f_metrics = {"forgetting_rate_b": 0, "forgetting_rate_a": 0, "total_facts": 0}

        all_results[mode] = {
            "consistency": c_metrics,
            "forgetting": f_metrics,
            "total_turns": total_turns,
            "avg_latency_ms": round(total_latency / total_turns, 1) if total_turns else 0,
        }

        print(f"  Consistency rate: {c_metrics.get('rate', 0):.3f}")
        print(f"  Forgetting rate B: {f_metrics.get('forgetting_rate_b', 0):.3f}")
        print(f"  Avg latency:       {all_results[mode]['avg_latency_ms']:.1f} ms")
        print()

    # 生成对比表
    if len(modes_to_run) > 1 and not skip_eval:
        print("=" * 60)
        print("  五组对比结果")
        print("=" * 60)
        print()
        table = generate_comparison_table(all_results)
        print(table)
        print()

        results_dir = os.path.join(PROJECT_DIR, config.paths.results_dir)
        os.makedirs(results_dir, exist_ok=True)

        results_path = os.path.join(results_dir, "eval_summary.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Results saved to {results_path}")

        table_path = os.path.join(results_dir, "comparison_table.md")
        with open(table_path, "w", encoding="utf-8") as f:
            f.write("# 实验一：主数据集 — 五组对比结果\n\n")
            f.write(f"测试用例数: {len(all_test_cases)}\n\n")
            f.write(table)
            f.write("\n")
        print(f"[INFO] Comparison table saved to {table_path}")

    print()
    print("[DONE] 实验一完成")
    return all_results


def main():
    parser = argparse.ArgumentParser(description="实验一：主数据集实验")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--mode", choices=[
        "no_memory", "short_term", "long_term",
        "long_term_no_forgetting", "long_term_no_selection",
    ])
    parser.add_argument("--test", help="Run single test case")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation")
    args = parser.parse_args()

    config = load_config(args.config)
    print(f"[INFO] Configuration loaded from {args.config}")

    try:
        _ = config.llm.api_key
        print(f"[INFO] API key found: {config.llm.api_key_env}")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    run_evaluation(config=config, mode_filter=args.mode,
                   test_filter=args.test, skip_eval=args.skip_eval)


if __name__ == "__main__":
    main()
