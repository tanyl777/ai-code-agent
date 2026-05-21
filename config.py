import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    model: str = "deepseek-v4-pro[1m]"
    temperature: float = 0.1
    max_tokens: int = 4096
    base_url: str = "https://api.deepseek.com/anthropic"
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "sk-21f342b1878349d99009ef5a6cc5cff4"))


@dataclass
class AgentConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    max_retries: int = 2
    max_code_length: int = 2000
    review_max_line_length: int = 100
    review_max_complexity: int = 10
    memory_file: str = "./session_memory.json"


DEFAULT_CONFIG = AgentConfig()
