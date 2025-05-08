# iMessage Data Processing Pipeline

This project processes iMessage data from the chat.db file for training a personal chatbot. The pipeline handles incremental updates as new messages are synced to your Mac.

## Directory Structure

```
data/
├── raw/              # Raw data from chat.db
├── processed/        # Cleaned and processed data
├── training/         # Training and validation datasets
└── scripts/          # Processing scripts
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure your chat.db file is accessible at `~/Library/Messages/chat.db`

## Pipeline Steps

The pipeline consists of three main steps:

1. **Extract Raw Data** (`extract_raw.py`)
   - Copies new messages from chat.db to raw_messages.db
   - Tracks which messages have been processed
   - Handles incremental updates

2. **Clean Data** (`clean_data.py`)
   - Cleans and processes messages from raw_messages.db
   - Removes reactions, system messages, and media placeholders
   - Groups messages into conversations
   - Stores cleaned data in cleaned_messages.db

3. **Prepare Training Data** (`prepare_training.py`)
   - Creates training and validation datasets
   - Formats conversations for fine-tuning
   - Outputs JSONL files for training

## Usage

Run the pipeline steps in order:

```bash
# Extract new messages
python data/scripts/extract_raw.py

# Clean the messages
python data/scripts/clean_data.py

# Prepare training data
python data/scripts/prepare_training.py
```

You can run these steps periodically as new messages sync to your Mac. Each step tracks its progress and only processes new data.

## Output

The final training data will be in `data/training/`:
- `train.jsonl`: Training dataset
- `validation.jsonl`: Validation dataset
- `metadata.json`: Dataset statistics and creation info

## Notes

- The pipeline is designed to handle incremental updates
- Each step maintains its own progress tracking
- Data is stored in SQLite databases for efficient querying
- The cleaning step removes reactions, system messages, and media placeholders
- Training data is formatted for fine-tuning a personal chatbot
