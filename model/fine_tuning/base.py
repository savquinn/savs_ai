from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from model.config.model_config import ModelConfig

class BaseFineTuner(ABC):
    """Base class for fine-tuning models from different providers."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.config.validate()
    
    @abstractmethod
    async def prepare_training_data(self, data_path: Path) -> List[Dict[str, Any]]:
        """Prepare training data in the format required by the model provider."""
        pass
    
    @abstractmethod
    async def start_fine_tuning(
        self,
        training_data: List[Dict[str, Any]],
        validation_data: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> str:
        """Start the fine-tuning process and return the job ID."""
        pass
    
    @abstractmethod
    async def check_fine_tuning_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a fine-tuning job."""
        pass
    
    @abstractmethod
    async def get_fine_tuned_model(self, job_id: str) -> str:
        """Get the name/ID of the fine-tuned model."""
        pass
    
    @abstractmethod
    async def test_fine_tuned_model(self, model_id: str, test_prompt: str) -> str:
        """Test the fine-tuned model with a given prompt."""
        pass 