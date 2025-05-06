from typing import Type
from model.config.model_config import ModelConfig, ModelProvider
from model.fine_tuning.base import BaseFineTuner
from model.fine_tuning.openai_tuner import OpenAIFineTuner

class FineTunerFactory:
    """Factory class for creating fine-tuners for different providers."""
    
    _providers: dict[ModelProvider, Type[BaseFineTuner]] = {
        ModelProvider.OPENAI: OpenAIFineTuner,
        # Add other providers here as they are implemented
    }
    
    @classmethod
    def create(cls, config: ModelConfig) -> BaseFineTuner:
        """Create a fine-tuner for the specified provider."""
        tuner_class = cls._providers.get(config.provider)
        if not tuner_class:
            raise ValueError(f"No fine-tuner implementation found for provider: {config.provider}")
        return tuner_class(config)
    
    @classmethod
    def register_provider(cls, provider: ModelProvider, tuner_class: Type[BaseFineTuner]) -> None:
        """Register a new fine-tuner implementation for a provider."""
        cls._providers[provider] = tuner_class 