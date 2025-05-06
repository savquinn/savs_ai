import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import openai
from openai import AsyncOpenAI

from model.fine_tuning.base import BaseFineTuner
from model.config.model_config import ModelConfig, ModelProvider

class OpenAIFineTuner(BaseFineTuner):
    """Fine-tuning implementation for OpenAI models."""
    
    def __init__(self, config: ModelConfig):
        if config.provider != ModelProvider.OPENAI:
            raise ValueError("OpenAIFineTuner requires OpenAI provider")
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=config.api_key)
    
    async def prepare_training_data(self, data_path: Path) -> List[Dict[str, Any]]:
        """Prepare training data in OpenAI's format."""
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        formatted_data = []
        for conversation in data:
            messages = []
            for msg in conversation['messages']:
                role = 'assistant' if msg['role'] == 'savs' else 'user'
                messages.append({
                    'role': role,
                    'content': msg['content']
                })
            
            formatted_data.append({
                'messages': messages
            })
        
        return formatted_data
    
    async def start_fine_tuning(
        self,
        training_data: List[Dict[str, Any]],
        validation_data: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> str:
        """Start fine-tuning with OpenAI."""
        # Create training file
        training_file = await self.client.files.create(
            file=json.dumps(training_data).encode('utf-8'),
            purpose="fine-tune"
        )
        
        # Create validation file if provided
        validation_file = None
        if validation_data:
            validation_file = await self.client.files.create(
                file=json.dumps(validation_data).encode('utf-8'),
                purpose="fine-tune"
            )
        
        # Start fine-tuning job
        fine_tuning_job = await self.client.fine_tuning.jobs.create(
            training_file=training_file.id,
            validation_file=validation_file.id if validation_file else None,
            model=self.config.model_name,
            **kwargs
        )
        
        return fine_tuning_job.id
    
    async def check_fine_tuning_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of an OpenAI fine-tuning job."""
        job = await self.client.fine_tuning.jobs.retrieve(job_id)
        return {
            'status': job.status,
            'model': job.fine_tuned_model,
            'created_at': job.created_at,
            'finished_at': job.finished_at,
            'error': job.error
        }
    
    async def get_fine_tuned_model(self, job_id: str) -> str:
        """Get the name of the fine-tuned model."""
        job = await self.client.fine_tuning.jobs.retrieve(job_id)
        if not job.fine_tuned_model:
            raise ValueError("Fine-tuning job is not complete")
        return job.fine_tuned_model
    
    async def test_fine_tuned_model(self, model_id: str, test_prompt: str) -> str:
        """Test the fine-tuned model with a given prompt."""
        response = await self.client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": self.config.system_prompt or ""},
                {"role": "user", "content": test_prompt}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return response.choices[0].message.content 