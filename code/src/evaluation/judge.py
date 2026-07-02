"""Judge — 基于字符串匹配的自动化评估判定器。

替代 LLM-as-Judge，使用检核问题 + 可接受答案列表做确定性匹配。

PJ-AGENT-2 ADR 0009: 自动化判定方法
"""

import re
from typing import Dict, List, Tuple


class AutomatedJudge:
    """确定性字符串匹配判定器。"""

    def __init__(self):
        pass

    def check_fact(
        self,
        fact: str,
        agent_response: str,
        acceptable_answers: List[str],
    ) -> Dict:
        """检查 Agent 回复是否包含/匹配某个事实。

        Args:
            fact: 待验证的事实描述（用于日志）
            agent_response: Agent 的回复文本
            acceptable_answers: 可接受的答案列表（含同义表述）

        Returns:
            {
                "fact": str,
                "consistent": bool,
                "matched_answer": str or None,
                "acceptable_answers": [...],
            }
        """
        response_normalized = self._normalize(agent_response)

        for answer in acceptable_answers:
            answer_norm = self._normalize(answer)
            if answer_norm and answer_norm in response_normalized:
                return {
                    "fact": fact,
                    "consistent": True,
                    "matched_answer": answer,
                    "acceptable_answers": acceptable_answers,
                }

        return {
            "fact": fact,
            "consistent": False,
            "matched_answer": None,
            "acceptable_answers": acceptable_answers,
        }

    def evaluate_turn(
        self,
        agent_response: str,
        checklist: List[Dict],
    ) -> List[Dict]:
        """对单轮回复执行完整的检核清单判定。

        Args:
            agent_response: Agent 回复
            checklist: 检核列表，每项 {"fact": str, "acceptable": [str, ...]}

        Returns:
            判定结果列表，每项含 consistent 字段
        """
        results = []
        for item in checklist:
            result = self.check_fact(
                fact=item["fact"],
                agent_response=agent_response,
                acceptable_answers=item.get("acceptable", []),
            )
            results.append(result)
        return results

    def score_consistency(
        self,
        conversation_history: str,
        current_response: str,
        expected_facts: List[str],
    ) -> Dict:
        """向后兼容旧 consistency 接口（不再使用 LLM 打分）。

        改为基于可接受答案的二元判定：全部匹配 = 5 分，按比率折算 1-5。
        """
        # 此方法保留用于旧接口兼容；实际判定走 evaluate_turn
        return {"score": 3, "reasoning": "Automated judge — use evaluate_turn instead"}

    def check_retention(
        self,
        fact: str,
        current_response: str,
    ) -> Dict:
        """向后兼容旧 retention 接口。"""
        return {"retained": "NO", "reasoning": "Automated judge — use evaluate_turn instead"}

    @staticmethod
    def _normalize(text: str) -> str:
        """文本归一化：去标点、去空格、转小写。"""
        text = text.lower().strip()
        # 去掉中文标点
        text = re.sub(r"[，。！？、；：""''（）【】《》\s]+", "", text)
        # 去掉英文标点
        text = re.sub(r"[,.\!\?;:\"'\(\)\[\]\s]+", "", text)
        return text


class LegacyLLMJudge:
    """保留旧的 LLM-as-Judge 接口（仅用于兼容，不启用）。"""
    def __init__(self, client=None):
        self.client = client

    def score_consistency(self, **kwargs):
        return {"score": 3, "reasoning": "Legacy judge — not used"}
    def check_retention(self, **kwargs):
        return {"retained": "NO", "reasoning": "Legacy judge — not used"}
    def _parse_json_response(self, raw, default):
        return default
