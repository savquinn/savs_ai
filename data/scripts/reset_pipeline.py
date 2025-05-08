import os
import sqlite3
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_pipeline_databases():
    """
    Reset the pipeline databases by removing the raw and cleaned message databases.
    This allows you to start the pipeline from scratch.
    """
    # Define database paths
    raw_db = "data/raw/raw_messages.db"
    cleaned_db = "data/processed/cleaned_messages.db"
    
    # Remove raw database if it exists
    if os.path.exists(raw_db):
        logger.info(f"Removing raw database: {raw_db}")
        os.remove(raw_db)
        logger.info("✓ Raw database removed")
    else:
        logger.info("No raw database found")
    
    # Remove cleaned database if it exists
    if os.path.exists(cleaned_db):
        logger.info(f"Removing cleaned database: {cleaned_db}")
        os.remove(cleaned_db)
        logger.info("✓ Cleaned database removed")
    else:
        logger.info("No cleaned database found")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(raw_db), exist_ok=True)
    os.makedirs(os.path.dirname(cleaned_db), exist_ok=True)
    
    logger.info("Pipeline databases have been reset. You can now run the pipeline from scratch.")

if __name__ == "__main__":
    reset_pipeline_databases() 