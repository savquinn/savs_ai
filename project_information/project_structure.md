savs_ai/
├── project_information/        # Existing folder with project docs
├── data/                       # Data processing pipeline
│   ├── raw/                    # Raw chat.db files
│   ├── processed/              # Processed conversation data
│   └── scripts/                # Scripts for data extraction/processing
├── model/                      # Model training and fine-tuning code
│   ├── config/                 # Training configuration
│   ├── checkpoints/            # Save model checkpoints
│   └── evaluation/             # Model evaluation scripts
├── server/                     # Backend server for hosting
│   ├── api/                    # API endpoints
│   ├── auth/                   # Authentication system
│   └── database/               # Server database for user data & feedback
├── client/                     # Frontend (if applicable)
│   ├── web/                    # Web interface
│   └── mobile/                 # Mobile app (if needed)
├── feedback/                   # RLHF system
│   ├── collection/             # Feedback collection logic
│   └── training/               # Scripts to incorporate feedback
├── utils/                      # Shared utilities
├── tests/                      # Test suite
├── docs/                       # Documentation
├── .env                        # Environment variables (not in git)
├── .gitignore                  # Git ignore file
├── requirements.txt            # Python dependencies
└── README.md                   # Project readme