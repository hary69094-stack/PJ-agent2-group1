"""LongTermMemory — 选择性长期记忆系统。

组合 ShortTermMemory（滑动窗口）+ TripleVectorStore（三元组向量库），
实现：规则层过滤 → 检索触发 → LLM 三元组抽取 + 重要性打分 → 去重 → 容量淘汰。
"""

import re
from typing import Dict, List, Optional, Tuple
from .base import MemoryStore
from .short_term import ShortTermMemory
from .vector_store import TripleVectorStore
from ..llm.deepseek_client import DeepSeekClient


# ── 规则层: 召回信号词 ────────────────────────────────────────────────
_RECALL_SIGNALS = [
    "还记得", "上次", "之前提到", "之前说过", "你记得",
    "告诉过我", "我说过", "我的", "我记得", "提醒",
    "以前", "回顾", "整理一下", "总结一下", "你还记得",
    "回忆", "记不记得", "之前问了", "之前问过",
]


# ── 规则层: 信息传递信号模板 ──────────────────────────────────────────
_INFO_SIGNAL_PATTERNS = [
    # 我是/我在/我来自 陈述句
    r"我是[^\s，。？！]{2,20}",
    r"我在[^\s，。？！]{2,30}",
    r"我来自[^\s，。？！]{2,20}",
    # 偏好表达
    r"(喜欢|不喜欢|讨厌|热爱|习惯|经常|偶尔|从不|计划|打算|准备|决定)",
    # 包含数字/日期
    r"\d{1,2}[月岁号日点个]",
    r"\d{4}年",
    # 包含命名实体特征词
    r"(叫|是|在|去|住|工作在?|学习|毕业于|就读于)",
    # 改口/修正
    r"(不对|错了|改正|其实是|应该说|不是.{1,5}是|纠正)",
]


class LongTermMemory(MemoryStore):
    """选择性长期记忆系统。

    每轮对话流水线:
      1. 规则层过滤 — 决定该轮是否需要记忆写入
      2. 检索触发 — 决定是否查询长期记忆
      3. Prompt 组装 — 将检索到的三元组格式化为独立记忆区段
      4. 异步记忆写入 — LLM 抽取三元组 + 打分 → 去重 → 写入 → 容量淘汰

    支持三种变体:
      - "full":         完整模式（选择 + 遗忘 + 去重）
      - "no_forgetting": 消融 G4-A：关闭遗忘（不淘汰）
      - "no_selection": 消融 G4-B：关闭选择（所有轮次无差别写入）
    """

    def __init__(
        self,
        short_term: ShortTermMemory,
        triple_store: TripleVectorStore,
        llm_client: DeepSeekClient,
        variant: str = "full",
        retrieval_auto_interval: int = 5,
        min_input_length: int = 5,
        min_entities: int = 1,
    ):
        self.short_term = short_term
        self.triple_store = triple_store
        self.llm = llm_client
        self.variant = variant
        self.retrieval_auto_interval = retrieval_auto_interval
        self.min_input_length = min_input_length
        self.min_entities = min_entities

        self.turn_count = 0
        self._last_auto_retrieval_turn = -1

        # 累积待写入文本（用户输入 + Agent 回复），由外部在调用 respond 后触发写入
        self._pending_user_input: Optional[str] = None
        self._pending_response: Optional[str] = None
        self._pending_should_write: bool = False

    # ═══════════════════════════════════════════════════════════════════
    # MemoryStore 接口
    # ═══════════════════════════════════════════════════════════════════

    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """存储一轮对话（短期记忆 + 标记潜在写入）。"""
        self.short_term.add_turn(role, content, metadata)
        self.turn_count += 1

    def retrieve_context(self, query: str) -> str:
        """检索长期记忆并格式化为独立记忆区段。

        Returns:
            格式化的 [长期记忆] 区段字符串，无匹配时返回空字符串。
        """
        if not self._should_retrieve(query):
            return ""

        triples = self.triple_store.search(query)
        if not triples:
            return ""

        return self._format_memory_section(triples)

    def get_window(self) -> List[Dict[str, str]]:
        return self.short_term.get_window()

    def reset(self) -> None:
        self.short_term.reset()
        self.triple_store.reset()
        self.turn_count = 0
        self._last_auto_retrieval_turn = -1
        self._pending_user_input = None
        self._pending_response = None
        self._pending_should_write = False

    def snapshot(self) -> Dict:
        return {
            "type": "long_term",
            "variant": self.variant,
            "short_term": self.short_term.snapshot(),
            "triple_store": self.triple_store.snapshot(),
        }

    def save(self, directory: str) -> None:
        self.triple_store.save(directory)

    def load(self, directory: str) -> bool:
        return self.triple_store.load(directory)

    # ═══════════════════════════════════════════════════════════════════
    # 规则层过滤
    # ═══════════════════════════════════════════════════════════════════

    def should_write(self, user_input: str) -> bool:
        """三步规则过滤：长度 → 句式 → 信息密度。

        Returns:
            True 表示该输入应进入记忆写入流程。
        """
        # 消融 G4-B：无选择 → 全部写入
        if self.variant == "no_selection":
            return True

        # Step 1: 长度过滤
        if len(user_input.strip()) < self.min_input_length:
            return False

        # Step 2: 句式过滤 — 检测信息传递信号
        has_signal = False
        for pattern in _INFO_SIGNAL_PATTERNS:
            if re.search(pattern, user_input):
                has_signal = True
                break
        if not has_signal:
            return False

        # Step 3: 信息密度过滤 — 含命名实体或数字
        # 简单启发式：检测含中文姓名模式、地名、机构名、或数字
        has_info_content = bool(
            re.search(r"[一二三四五六七八九十百千万亿\d]+", user_input) or  # 含数字
            re.search(r"[^\s]{2,4}(?:大学|公司|医院|城市|省|市|区)", user_input) or  # 机构/地名
            re.search(r"(?:过敏|喜欢|讨厌|在|是|来自|工作|学习|毕业)", user_input)  # 关键谓词
        )
        if not has_info_content:
            return False

        return True

    # ═══════════════════════════════════════════════════════════════════
    # 检索触发
    # ═══════════════════════════════════════════════════════════════════

    def _should_retrieve(self, query: str) -> bool:
        """判断是否需要查询长期记忆。

        主触发：用户输入含召回信号词
        兜底触发：距上次自动检索 >= retrieval_auto_interval 轮
        """
        # 库为空则不需要检索
        if self.triple_store._index.ntotal == 0:
            return False

        # 主触发：召回信号词
        query_lower = query.lower()
        for signal in _RECALL_SIGNALS:
            if signal in query_lower:
                self._last_auto_retrieval_turn = self.turn_count
                return True

        # 兜底触发：每 N 轮自动检索
        if self.turn_count - self._last_auto_retrieval_turn >= self.retrieval_auto_interval:
            self._last_auto_retrieval_turn = self.turn_count
            return True

        return False

    # ═══════════════════════════════════════════════════════════════════
    # 记忆写入（由 Agent respond 后调用）
    # ═══════════════════════════════════════════════════════════════════

    def try_write_memory(self, user_input: str, response: str) -> List[Dict]:
        """尝试从当前轮对话中抽取三元组并写入长期记忆。

        Args:
            user_input: 用户输入
            response: Agent 回复

        Returns:
            本次写入的三元组列表（可能为空）
        """
        if not self.should_write(user_input):
            return []

        # 调用 LLM 抽取三元组 + 重要性打分
        triples = self._extract_triples(user_input, response)
        if not triples:
            return []

        written = []
        for t in triples:
            doc_id = self.triple_store.add_triple(
                subject=t["subject"],
                relation=t["relation"],
                obj=t["object"],
                importance=t["importance"],
                source_turn=self.turn_count,
            )
            if doc_id is not None:
                t["doc_id"] = doc_id
                written.append(t)

        # 消融 G4-A：无遗忘 → 不触发淘汰
        if self.variant != "no_forgetting":
            self.triple_store.ensure_capacity()

        return written

    # ═══════════════════════════════════════════════════════════════════
    # LLM 三元组抽取
    # ═══════════════════════════════════════════════════════════════════

    _TRIPLE_EXTRACTION_PROMPT = """你是一个记忆提取器。从以下对话中提取值得长期记住的关键信息，转化为结构化三元组。

每个三元组格式：{主语} | {关系} | {宾语}

提取规则：
- 主语通常是"用户"（指代对话中的用户）
- 关系用简洁的动词或名词短语（如：家乡、职业、喜好、计划、过敏、学习等）
- 宾语是具体的信息值
- 只提取事实性、有价值的信息，忽略寒暄、闲聊、一次性问题
- 每条三元组附重要性评分（1-5）：
  5 = 核心身份/安全信息（姓名、过敏、密码等）
  4 = 重要偏好/计划
  3 = 一般个人信息
  2 = 临时偏好或计划
  1 = 可能有用但不关键

输出格式：严格的 JSON 数组，每个元素为 {"subject": "...", "relation": "...", "object": "...", "importance": 1-5}
仅输出 JSON 数组，不要其他文本。如果没有值得记忆的信息，输出空数组 []。"""

    def _extract_triples(self, user_input: str, response: str) -> List[Dict]:
        """调用 LLM 从对话中提取结构化三元组。

        Args:
            user_input: 用户输入
            response: Agent 回复（用于上下文理解）

        Returns:
            三元组列表 [{"subject":..., "relation":..., "object":..., "importance":...}, ...]
        """
        prompt = (
            f"=== 用户输入 ===\n{user_input}\n\n"
            f"=== 助手回复 ===\n{response}\n\n"
            f"请提取值得长期记忆的三元组。"
        )

        messages = [
            {"role": "system", "content": self._TRIPLE_EXTRACTION_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            import json
            raw = self.llm.chat(
                messages,
                temperature=0.3,
                max_tokens=512,
            )
            return self._parse_triple_json(raw)
        except Exception:
            return []

    @staticmethod
    def _parse_triple_json(raw: str) -> List[Dict]:
        """从 LLM 原始输出中解析三元组 JSON。"""
        import json
        raw = raw.strip()
        # 找到 JSON 数组边界
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            data = json.loads(raw[start:end + 1])
            if not isinstance(data, list):
                return []
            # 验证字段
            result = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                if all(k in item for k in ("subject", "relation", "object", "importance")):
                    imp = int(item["importance"])
                    item["importance"] = max(1, min(5, imp))  # clamp 1-5
                    result.append(item)
            return result
        except (json.JSONDecodeError, ValueError):
            return []

    # ═══════════════════════════════════════════════════════════════════
    # 记忆格式化
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _format_memory_section(triples: List[Dict]) -> str:
        """将检索到的三元组格式化为独立记忆区段。

        格式：
        [长期记忆]
        以下是你从历史对话中记住的关于用户的信息。如果这些信息与用户的最新陈述矛盾，
        以用户最新说法为准。
        - 用户 | 家乡 | 成都 (重要性: 4)
        - 用户 | 职业 | 软件工程师 (重要性: 5)
        ...
        """
        lines = [
            "[长期记忆]",
            "以下是你从历史对话中记住的关于用户的信息。如果这些信息与用户的最新陈述矛盾，",
            "以用户最新说法为准。",
            "",
        ]
        for t in triples:
            imp_stars = "★" * t["importance"]
            lines.append(f"- {t['subject']} | {t['relation']} | {t['object']} ({imp_stars})")

        # 加遗忘提醒
        lines.append("")
        lines.append("（注意：上述记忆可能已过时或存在矛盾，请以用户当前陈述为准。）")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════
    # 向后兼容: FAISS 访问
    # ═══════════════════════════════════════════════════════════════════
    @property
    def faiss(self):
        """向后兼容旧代码的 faiss 属性。"""
        return self.triple_store
