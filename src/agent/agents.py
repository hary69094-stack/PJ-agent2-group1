"""Agents — PJ-AGENT-2 的五种记忆配置。

G1: NoMemoryAgent        — 无记忆基线
G2: ShortTermAgent       — 仅短期记忆（N=6 滑动窗口）
G3: LongTermAgent        — 完整长期记忆（选择写入 + 遗忘淘汰 + 去重）
G4A: NoForgettingAgent   — 消融：无遗忘（只存不删）
G4B: NoSelectionAgent    — 消融：无选择（全量写入）
"""

from typing import Dict, List
from .base import BaseAgent


# ═══════════════════════════════════════════════════════════════════════
# G1: 无记忆
# ═══════════════════════════════════════════════════════════════════════

class NoMemoryAgent(BaseAgent):
    """Agent G1: 没有任何记忆。每轮独立，无法回忆任何历史信息。"""

    def _build_system_prompt(self) -> str:
        return (
            "你是一个有帮助的助手。你**没有任何记忆**，无法记住之前的任何对话。\n"
            "请按照以下规则回复：\n"
            "- 每次回复都当作第一次和用户对话。\n"
            "- 不要假装记得之前说过的事情。\n"
            "- 如果用户说「你之前知道...」之类的话，诚实地说你不记得。"
        )

    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]


# ═══════════════════════════════════════════════════════════════════════
# G2: 仅短期记忆
# ═══════════════════════════════════════════════════════════════════════

class ShortTermAgent(BaseAgent):
    """Agent G2: 仅短期滑动窗口记忆（N=6）。超出窗口的信息永久遗忘。"""

    def _build_system_prompt(self) -> str:
        return (
            "你是一个有帮助的助手。你只能记住**最近几轮对话**，之前的对话你会完全遗忘。\n"
            "请按照以下规则回复：\n"
            "- 如果用户问及几轮前说过的事情而你记得，可以据实回答。\n"
            "- 如果用户问的事情超出了你能记住的范围，诚实地说你不记得。\n"
            "- 不要编造或假装记得你不知道的信息。"
        )

    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        window = self.memory.get_window()
        messages.extend(window)
        messages.append({"role": "user", "content": user_input})
        return messages


# ═══════════════════════════════════════════════════════════════════════
# G3: 完整长期记忆
# ═══════════════════════════════════════════════════════════════════════

class LongTermAgent(BaseAgent):
    """Agent G3: 完整选择性长期记忆。

    包含：规则层过滤 + 检索触发 + 三元组抽取 + 重要性打分 + 去重 + 容量淘汰。
    """

    def _build_system_prompt(self) -> str:
        return (
            "你是一个具备**选择性长期记忆**的智能助手。\n\n"
            "你的记忆机制模拟了人类的记忆特点：\n"
            "- 你会**有选择地记住**对话中的重要信息（姓名、偏好、计划等），\n"
            "  而不会记住所有无关的闲聊。\n"
            "- 你知道自己的记忆**可能不完整或过时**，\n"
            "  会以用户最新说法为准。\n\n"
            "回复规则：\n"
            "- 如果消息中包含 [长期记忆] 区段，使用其中的信息给出个性化和一致的回答。\n"
            "- 如果 [长期记忆] 与用户当前陈述矛盾，以用户最新说法为准。\n"
            "- 如果记忆中没有相关信息，诚实地说你不知道，不要编造。\n"
            "- 不要假装你记住了你没记住的东西。"
        )

    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]

        # 检索长期记忆并注入独立区段
        context = self.memory.retrieve_context(user_input)
        if context:
            messages.append({"role": "system", "content": context})

        # 追加短期窗口
        window = self.memory.get_window()
        messages.extend(window)

        # 当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def _after_respond(self, user_input: str, response: str) -> None:
        """每轮回复后异步写入长期记忆（通过记忆模块的 try_write_memory）。"""
        if hasattr(self.memory, "try_write_memory"):
            self.memory.try_write_memory(user_input, response)


# ═══════════════════════════════════════════════════════════════════════
# G4-A: 无遗忘消融（只存不删）
# ═══════════════════════════════════════════════════════════════════════

class NoForgettingAgent(LongTermAgent):
    """Agent G4-A: 关闭遗忘淘汰机制。所有写入的记忆永久保留。

    与 G3 的唯一区别：永不对长期记忆做淘汰删除。
    用于验证遗忘机制对记忆质量的影响。
    """

    def _build_system_prompt(self) -> str:
        return (
            "你是一个具备长期记忆的智能助手（遗忘功能已关闭）。\n"
            "你的记忆机制会保留所有写入的信息，不做淘汰。\n\n"
            "回复规则同长期记忆模式。"
        )


# ═══════════════════════════════════════════════════════════════════════
# G4-B: 无选择消融（全量写入 → 退化 RAG）
# ═══════════════════════════════════════════════════════════════════════

class NoSelectionAgent(LongTermAgent):
    """Agent G4-B: 关闭记忆选择机制。所有信息无差别写入长期记忆。

    与 G3 的唯一区别：规则层过滤被绕过，每轮对话的输入和回复
    都会被 LLM 抽取三元组并写入（过滤所有无关闲聊）。
    用于验证选择性写入对记忆质量的影响。
    """

    def _build_system_prompt(self) -> str:
        return (
            "你是一个具备长期记忆的智能助手（选择过滤已关闭，所有信息都会被尝试写入记忆）。\n"
            "这可能导致记忆库中包含更多噪音信息。\n\n"
            "回复规则同长期记忆模式。"
        )
