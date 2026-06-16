"""Configuration loader — reads config.yaml into typed dataclasses.

PJ-AGENT-2: 选择性长期记忆 Agent 配置系统
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class LLMConfig:
    api_key_env: str = "DEEPSEEK_API_KEY"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature_agent: float = 0.7
    temperature_triple_extraction: float = 0.3
    temperature_judge: float = 0.0
    max_tokens: int = 1024
    max_tokens_triple_extraction: int = 512
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0

    @property
    def api_key(self) -> str:
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise ValueError(
                f"Environment variable '{self.api_key_env}' is not set. "
                f"Please set it before running: set {self.api_key_env}=your-key"
            )
        return key


@dataclass
class RuleFilterConfig:
    min_input_length: int = 5          # 长度过滤：<5 中文字符跳过
    info_density_min_entities: int = 1 # 信息密度：至少含1个命名实体


@dataclass
class MemoryConfig:
    short_term_window_size: int = 6
    long_term_capacity: int = 150
    embedding_model: str = "shibing624/text2vec-base-chinese-sentence"
    embedding_dim: int = 768
    top_k_retrieval: int = 5
    dedup_semantic_threshold: float = 0.90
    retrieval_auto_trigger_interval: int = 5
    importance_scale: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])


@dataclass
class ConsistencyEvalConfig:
    rubrics: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    judge_temperature: float = 0.0


@dataclass
class ForgettingEvalConfig:
    delta_bins: List[List[int]] = field(
        default_factory=lambda: [[5, 10], [11, 15], [16, 100]]
    )


@dataclass
class EvalConfig:
    consistency: ConsistencyEvalConfig = field(default_factory=ConsistencyEvalConfig)
    forgetting: ForgettingEvalConfig = field(default_factory=ForgettingEvalConfig)


@dataclass
class PathsConfig:
    test_file: str = "data/conversation_tests.jsonl"
    log_dir: str = "data/agent_logs"
    memory_store_dir: str = "memory_store"
    results_dir: str = "results"


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    rule_filter: RuleFilterConfig = field(default_factory=RuleFilterConfig)
    evaluation: EvalConfig = field(default_factory=EvalConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)


def _dict_to_dataclass(cls, d: dict):
    """Recursively convert a dict to a dataclass instance."""
    if d is None:
        return cls()
    # Map yaml keys with underscores to dataclass fields
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for key, value in d.items():
        if key in field_types:
            ftype = field_types[key]
            if hasattr(ftype, "__dataclass_fields__") and isinstance(value, dict):
                kwargs[key] = _dict_to_dataclass(ftype, value)
            else:
                kwargs[key] = value
        else:
            kwargs[key] = value
    return cls(**kwargs)


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from a YAML file and return a Config instance."""
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _dict_to_dataclass(Config, raw)
