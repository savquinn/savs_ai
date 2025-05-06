from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ModelProvider(Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"

@dataclass
class ModelConfig:
    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 150
    system_prompt: Optional[str] = None

    def validate(self) -> None:
        """Validate the configuration."""
        if not self.model_name:
            raise ValueError("Model name is required")
        if self.provider == ModelProvider.OPENAI and not self.api_key:
            raise ValueError("API key is required for OpenAI models")
        if self.provider == ModelProvider.CLAUDE and not self.api_key:
            raise ValueError("API key is required for Claude models")
        if self.provider == ModelProvider.DEEPSEEK and not self.api_key:
            raise ValueError("API key is required for DeepSeek models") 