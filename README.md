# Savs.ai

A personal AI assistant fine-tuned on your iMessage conversations.

## Project Structure

```
savs_ai/
├── project_information/        # Project documentation
├── data/                       # Data processing pipeline
├── model/                      # Model training and fine-tuning
├── server/                     # Backend server
├── client/                     # Frontend
├── feedback/                   # RLHF system
├── utils/                      # Shared utilities
├── tests/                      # Test suite
└── docs/                       # Documentation
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
- Copy `.env.example` to `.env`
- Fill in the required environment variables

4. Set up pre-commit hooks:
```bash
pre-commit install
```

## Development

- Data processing scripts are in `data/scripts/`
- Model training code is in `model/`
- Server code is in `server/`
- Client code is in `client/`

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Static type checking

These tools run automatically on each commit. You can also run them manually:

```bash
# Format code
black .
isort .

# Run linters
flake8
mypy .
```

## Testing

Run tests with:
```bash
python -m pytest tests/
```

## Documentation

See `docs/` for detailed documentation about the project.
