"""Metrics — 多轮一致性与信息遗忘率计算。

PJ-AGENT-2 ADR 0009: 双口径遗忘率
- 遗忘率 B（全口径，主指标）：所有预设事实的丢失率
- 遗忘率 A（应记未记，分析用）：仅已确认写入的事实的丢失率
"""

from typing import Dict, List, Optional
from collections import defaultdict


def compute_consistency_from_checklist(
    per_turn_results: List[Dict],
) -> Dict:
    """从检核判定结果计算一致性指标。

    Args:
        per_turn_results: 每轮判定的累积列表，每项含:
            {"test_id": str, "turn": int, "results": [{"fact": str, "consistent": bool}, ...]}

    Returns:
        {
            "mean": float,          # 一致率均值
            "std": float,
            "total_checks": int,    # 总检核次数
            "passed": int,          # 通过数
            "failed": int,          # 失败数
            "rate": float,          # 通过率
            "per_test": [...],      # 每组对话的单独统计
        }
    """
    all_consistent = []
    per_test = defaultdict(lambda: {"total": 0, "passed": 0})

    for entry in per_turn_results:
        tid = entry["test_id"]
        for r in entry["results"]:
            all_consistent.append(1 if r["consistent"] else 0)
            per_test[tid]["total"] += 1
            if r["consistent"]:
                per_test[tid]["passed"] += 1

    n = len(all_consistent)
    if n == 0:
        return {"mean": 0, "std": 0, "rate": 0, "total_checks": 0,
                "passed": 0, "failed": 0, "per_test": []}

    passed = sum(all_consistent)
    failed = n - passed
    rate = passed / n
    mean = rate
    variance = sum((s - mean) ** 2 for s in all_consistent) / n
    std = variance ** 0.5

    per_test_list = [
        {
            "test_id": tid,
            "rate": d["passed"] / d["total"] if d["total"] else 0,
            "total": d["total"],
            "passed": d["passed"],
        }
        for tid, d in sorted(per_test.items())
    ]

    return {
        "mean": round(mean, 3),
        "std": round(std, 3),
        "rate": round(rate, 3),
        "total_checks": n,
        "passed": passed,
        "failed": failed,
        "per_test": per_test_list,
    }


def compute_forgetting_rate(
    per_fact_results: List[Dict],
    delta_bins: Optional[List[List[int]]] = None,
) -> Dict:
    """计算信息遗忘率（双口径）。

    Args:
        per_fact_results: List of {
            "test_id": str,
            "fact": str,
            "introduced_at_turn": int,
            "checked_at_turn": int,
            "delta": int,
            "consistent": bool,      # 全口径判定
            "was_written": bool,     # 是否已确认写入（用于遗忘率 A）
        }
        delta_bins: 可选的延迟分段

    Returns:
        {
            "forgetting_rate_b": float,  # 全口径遗忘率（主指标）
            "forgetting_rate_a": float,  # 应记未记遗忘率（分析用）
            "total_facts": int,
            "retained": int,
            "forgotten": int,
            "binned": {...},
        }
    """
    if delta_bins is None:
        delta_bins = [[5, 10], [11, 15], [16, 100]]

    total = len(per_fact_results)
    if total == 0:
        return {
            "forgetting_rate_b": 0, "forgetting_rate_a": 0,
            "total_facts": 0, "retained": 0, "forgotten": 0, "binned": {},
        }

    # 遗忘率 B（全口径）
    forgotten_b = sum(1 for r in per_fact_results if not r["consistent"])
    rate_b = forgotten_b / total

    # 遗忘率 A（仅已确认写入的）
    written = [r for r in per_fact_results if r.get("was_written", False)]
    if written:
        forgotten_a = sum(1 for r in written if not r["consistent"])
        rate_a = forgotten_a / len(written)
    else:
        rate_a = 0.0

    retained = total - forgotten_b

    # 按延迟分段
    binned = {}
    for low, high in delta_bins:
        bin_facts = [r for r in per_fact_results if low <= r.get("delta", 0) <= high]
        bin_total = len(bin_facts)
        bin_forgotten = sum(1 for r in bin_facts if not r["consistent"])
        bin_rate = bin_forgotten / bin_total if bin_total > 0 else 0.0
        binned[f"{low}-{high}"] = {
            "rate": round(bin_rate, 3),
            "total": bin_total,
            "forgotten": bin_forgotten,
        }

    return {
        "forgetting_rate_b": round(rate_b, 3),
        "forgetting_rate_a": round(rate_a, 3),
        "total_facts": total,
        "retained": retained,
        "forgotten": forgotten_b,
        "binned": binned,
    }


# ── 向后兼容 ──────────────────────────────────────────────────────────

def compute_consistency_scores(per_trigger_results):
    """向后兼容旧接口（1-5 分制 → 转换为一致率）。"""
    scores = [r.get("score", r.get("consistent", 0)) for r in per_trigger_results]
    n = len(scores)
    if n == 0:
        return {"mean": 0, "std": 0, "median": 0, "distribution": {},
                "per_test": [], "total_triggers": 0}
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    std = variance ** 0.5
    sorted_scores = sorted(scores)
    median = sorted_scores[n // 2]
    dist = defaultdict(int)
    for s in scores:
        dist[int(s)] += 1
    return {
        "mean": round(mean, 3),
        "std": round(std, 3),
        "median": median,
        "distribution": {int(k): v for k, v in sorted(dist.items())},
        "per_test": [],
        "total_triggers": n,
    }


def generate_comparison_table(results: Dict[str, Dict]) -> str:
    """生成五组对比的 Markdown 表格。

    Args:
        results: {"no_memory": {...}, "short_term": {...}, "long_term": {...},
                  "long_term_no_forgetting": {...}, "long_term_no_selection": {...}}
    """
    modes_order = [
        ("no_memory", "No Memory"),
        ("short_term", "Short-Term Only"),
        ("long_term", "Short+Long (Full)"),
        ("long_term_no_forgetting", "Long w/o Forgetting"),
        ("long_term_no_selection", "Long w/o Selection"),
    ]

    lines = [
        "| Metric | " + " | ".join(l for _, l in modes_order if _ in results) + " |",
        "|--------|" + "|".join(["--------" for _ in modes_order if _[0] in results]) + "|",
    ]

    # Consistency
    c_vals = []
    for mode, _ in modes_order:
        if mode in results:
            c = results[mode].get("consistency", {})
            rate = c.get("rate", c.get("mean", 0))
            c_vals.append(f"{rate:.3f}")
    lines.append(f"| Consistency Rate | {' | '.join(c_vals)} |")

    # Forgetting Rate B
    f_vals = []
    for mode, _ in modes_order:
        if mode in results:
            f = results[mode].get("forgetting", {})
            rate = f.get("forgetting_rate_b", f.get("overall_rate", 0))
            f_vals.append(f"{rate:.3f}")
    lines.append(f"| Forgetting Rate (B) | {' | '.join(f_vals)} |")

    # Forgetting Rate A (if available)
    fa_vals = []
    for mode, _ in modes_order:
        if mode in results:
            f = results[mode].get("forgetting", {})
            rate = f.get("forgetting_rate_a", None)
            if rate is not None:
                fa_vals.append(f"{rate:.3f}")
    if fa_vals and len(fa_vals) == len(c_vals):
        lines.append(f"| Forgetting Rate (A) | {' | '.join(fa_vals)} |")

    # Binned
    bins = ["5-10", "11-15", "16-100"]
    for b in bins:
        row = [f"| Forget Rate (Δ {b})"]
        for mode, _ in modes_order:
            if mode in results:
                f = results[mode].get("forgetting", {})
                bin_data = (f.get("binned", {}) or {}).get(b, {})
                row.append(f"{bin_data.get('rate', 0):.3f}")
        lines.append(" | ".join(row) + " |")

    return "\n".join(lines)
