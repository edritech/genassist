# GenAssist

GenAssist is an AI-powered platform for managing and leveraging various AI workflows, with a focus on conversation management, analytics, and agent-based interactions.

## Overview

GenAssist provides a comprehensive solution for building, managing, and deploying AI agents with the following key features:

- **User Management**: Authentication, authorization, role-based access control, and API key management
- **AI Agents**: Configure and manage agents with various LLM providers and tools
- **Knowledge Base**: Document management with RAG (Retrieval-Augmented Generation) configuration
- **Analytics**: Performance metrics, conversation analysis, and KPI tracking
- **Conversation Management**: Transcript viewing, conversation analysis, and sentiment analysis
- **Audit Logging**: System activity tracking and change history

## Architecture

### Frontend
- Built with React, TypeScript, Vite, and Tailwind CSS
- Uses shadcn-ui for accessible UI components
- Follows a well-structured component architecture

### Backend
- Python-based API built with FastAPI
- SQLAlchemy ORM with PostgreSQL database
- Follows layered architecture with dependency injection

## Getting Started

### Prerequisites

- Git
- Docker and Docker Compose
- Node.js and npm (for local development)
- Python 3.10+ (for local development)

### Clone the Repository with Submodules

```bash
# Clone the repository
git clone https://github.com/RitechSolutions/genassist
cd genassist

# Build and run the docker containers:
OPENAI_API_KEY=<YOUR_KEY_HERE> HUGGINGFACE_TOKEN=<YOUR_HF_KEY_HERE> docker compose up --build
```

## Local Development

### Frontend

```bash
cd frontend
```
Follow Readme.md for frontend project

Access the frontend app at: http://localhost:8080
User: admin
Password: genadmin

### Backend

```bash
cd backend
```

Create a `.env` file in the root directory of backend similar to .env.example:

Follow Readme.md for backend project

Access the backend API: http://localhost:8000/api
Access API documentation: http://localhost:8000/docs
Celery jobs: http://localhost:5555  (user:user1 password: password1)

## Integration Options

GenAssist provides multiple integration options:

### React Integration

```bash
cd plugins/react
npm install genassist-chat-react

```

## Testing

```bash
# Backend Tests
cd backend
python -m pytest tests/

# Run tests with coverage
coverage run --source=app -m pytest -v tests && coverage report -m

# Detailed coverage report
python -m pytest tests/ -v --cov=app --cov-report=html
```

## License

[BSL]
