"""BaseAgent — 抽象 Agent 基类，所有记忆配置共享此接口。

PJ-AGENT-2: 选择性长期记忆 Agent
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from ..llm.deepseek_client import DeepSeekClient
from ..memory.base import MemoryStore


class BaseAgent(ABC):
    """抽象对话 Agent。

    子类实现 _build_system_prompt() 和 _build_messages()
    来提供不同的记忆配置。
    """

    def __init__(
        self,
        llm_client: DeepSeekClient,
        memory: MemoryStore,
        agent_mode: str,
        agent_temperature: float = 0.7,
    ):
        self.llm = llm_client
        self.memory = memory
        self.agent_mode = agent_mode
        self.agent_temperature = agent_temperature
        self.system_prompt = self._build_system_prompt()
        self.turn_count = 0

    # ── 子类合约 ──────────────────────────────────────────────────────

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """返回此记忆配置的 system prompt。"""
        ...

    @abstractmethod
    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        """组装 LLM 调用的完整消息列表。

        典型结构:
            [system_prompt] + [可选 retrieved_context] + [window] + [current_user]
        """
        ...

    # ── 核心循环 ──────────────────────────────────────────────────────

    def respond(self, user_input: str) -> str:
        """处理用户消息并返回 Agent 回复。

        完整流程:
          1. 组装消息列表（由子类决定）
          2. 调用 LLM 生成回复
          3. 存储用户输入和回复到短期记忆
          4. 【可选】触发长期记忆写入（由子类覆写 _after_respond）
          5. 返回回复文本
        """
        messages = self._build_messages(user_input)
        response = self.llm.chat(
            messages,
            temperature=self.agent_temperature,
        )

        # 记录本轮对话到短期记忆
        self.memory.add_turn("user", user_input)
        self.memory.add_turn("assistant", response)
        self.turn_count += 1

        # 子类可选的写入后处理（长期记忆写入）
        self._after_respond(user_input, response)

        return response

    def _after_respond(self, user_input: str, response: str) -> None:
        """子类可覆写此方法以在每次回复后执行额外操作（如长期记忆写入）。"""
        pass

    # ── 工具方法 ──────────────────────────────────────────────────────

    def get_log_data(self, user_input: str, response: str, latency_ms: float) -> Dict:
        """返回本轮的结构化日志数据。"""
        snapshot = self.memory.snapshot() if hasattr(self.memory, "snapshot") else {}
        return {
            "agent_mode": self.agent_mode,
            "turn": self.turn_count,
            "user_input": user_input,
            "llm_response": response,
            "latency_ms": latency_ms,
            "memory_snapshot": snapshot,
        }

    def reset(self) -> None:
        """重置 Agent 状态（新对话开始）。"""
        self.memory.reset()
        self.turn_count = 0
