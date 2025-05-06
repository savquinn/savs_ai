import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from model.config.model_config import ModelConfig, ModelProvider
from model.fine_tuning.factory import FineTunerFactory

async def main():
    # Load environment variables
    load_dotenv()
    
    # Create model configuration
    config = ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-3.5-turbo",  # Use a base model that supports fine-tuning
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt="You are a helpful AI assistant.",
        temperature=0.7,
        max_tokens=150
    )
    
    # Create fine-tuner
    fine_tuner = FineTunerFactory.create(config)
    
    # Prepare training data
    data_path = Path("data/processed/fine_tuning/all_conversations.json")
    training_data = await fine_tuner.prepare_training_data(data_path)
    
    # Start fine-tuning
    job_id = await fine_tuner.start_fine_tuning(
        training_data=training_data,
        validation_data=None,  # Optional validation data
        hyperparameters={
            "n_epochs": 3,
            "batch_size": 4
        }
    )
    
    print(f"Started fine-tuning job with ID: {job_id}")
    
    # Monitor the job
    while True:
        status = await fine_tuner.check_fine_tuning_status(job_id)
        print(f"Job status: {status['status']}")
        
        if status['status'] in ['succeeded', 'failed']:
            break
        
        await asyncio.sleep(60)  # Check every minute
    
    if status['status'] == 'succeeded':
        model_id = await fine_tuner.get_fine_tuned_model(job_id)
        print(f"Fine-tuned model ID: {model_id}")
        
        # Test the model
        test_prompt = "Hey, how's it going?"
        response = await fine_tuner.test_fine_tuned_model(model_id, test_prompt)
        print(f"Test response: {response}")
    else:
        print(f"Fine-tuning failed: {status.get('error')}")

if __name__ == "__main__":
    asyncio.run(main()) 