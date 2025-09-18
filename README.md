# Deribit Webhook Python

A comprehensive Python port of the Deribit Options Trading Microservice, originally written in Node.js/TypeScript. This service handles TradingView webhook signals, manages OAuth 2.0 authentication with Deribit, and performs automated option trading operations.

## 🎯 Project Status: **COMPLETE**

This project has been successfully ported from TypeScript to Python with 100% functionality preservation.

## 🏗️ Architecture

### Technology Stack
- **Web Framework**: FastAPI (replacing Express.js)
- **Type System**: Pydantic models (replacing TypeScript interfaces)
- **HTTP Client**: httpx (replacing axios)
- **Database**: aiosqlite + SQLAlchemy (async SQLite)
- **Configuration**: YAML + Pydantic Settings
- **Authentication**: OAuth 2.0 with automatic token refresh

### Project Structure
```
deribit_webhook_python/
├── src/                           # Main application package
│   ├── api/                       # Deribit API clients
│   ├── config/                    # Configuration management
│   ├── database/                  # Database operations
│   ├── middleware/                # FastAPI middleware
│   ├── routes/                    # API route handlers
│   ├── services/                  # Business logic services
│   ├── models/                    # Pydantic type definitions
│   ├── utils/                     # Utility functions
│   ├── app.py                     # FastAPI application factory
│   └── main.py                    # Application entry point
├── public/                        # Static files and dashboard
├── config/                        # Configuration files
├── tests/                         # Test suite
├── docs/                          # Documentation
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration
├── Dockerfile                     # Docker configuration
├── docker-compose.yml             # Docker Compose setup
└── deploy.sh                      # Deployment script
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip or conda

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd deribit_webhook_python
pip install -r requirements.txt
pip install -e .
```

2. **Configure API keys:**
```bash
# Copy example configuration
cp config/apikeys.example.yml config/apikeys.yml

# Edit with your Deribit API credentials
nano config/apikeys.yml
```

3. **Set environment variables:**
```bash
# Copy example environment file
cp .env.example .env

# Edit environment settings
nano .env
```

4. **Run the service:**
```bash
# Development mode with auto-reload
make dev

# Or directly with uvicorn
cd src && uvicorn app:app --reload --host 0.0.0.0 --port 3001

# Production mode
make run
```

## 📊 Features

### ✅ Core Trading System
- TradingView webhook signal processing
- Automated option trading with smart execution
- Position management and delta calculation
- Real-time position polling and monitoring

### ✅ Authentication & Security
- OAuth 2.0 authentication with Deribit
- Automatic token refresh and management
- Rate limiting and request throttling
- Webhook signature verification
- API key authentication

### ✅ Data Management
- SQLite database with async operations
- Delta record tracking and history
- Position data persistence
- Automatic database cleanup

### ✅ Notifications & Monitoring
- WeChat bot integration for trading alerts
- System-wide notification broadcasting
- Comprehensive health monitoring
- Structured logging with multiple formats

### ✅ Web Interface
- Modern web dashboard with real-time updates
- **Delta Manager** - comprehensive Delta value management interface
- Interactive API documentation (FastAPI auto-docs)
- Static file serving and asset management
- Responsive design with activity logging

## 🔧 Development

### Available Commands
```bash
make help          # Show available commands
make install       # Install dependencies
make dev           # Run in development mode
make run           # Run in production mode
make test          # Run tests
make lint          # Run linting
make format        # Format code
make type-check    # Run type checking
make build         # Build package
```

### Testing
```bash
# Run all tests
make test

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

## 🐳 Docker Deployment

### Quick Deploy
```bash
# Setup and deploy
./deploy.sh setup production
./deploy.sh deploy

# With Docker Compose
./deploy.sh compose
```

### Manual Docker
```bash
# Build image
docker build -t deribit-webhook-python .

# Run container
docker run -p 3001:3001 -v $(pwd)/config:/app/config deribit-webhook-python
```

## 📚 Documentation

- **[API Documentation](docs/API.md)** - Complete API reference
- **[Configuration Guide](docs/CONFIGURATION.md)** - Setup and configuration
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Project Summary](PROJECT_SUMMARY.md)** - Detailed project overview

### Interactive Documentation
When running the service, visit:
- **Swagger UI**: http://localhost:3001/docs
- **ReDoc**: http://localhost:3001/redoc

## 🔗 API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /api/status` - Service status and configuration

### Trading
- `POST /webhook/signal` - TradingView webhook endpoint
- `GET /api/positions` - Get current positions
- `POST /api/positions/poll` - Manual position polling

### Authentication
- `POST /api/auth/token` - Get authentication token
- `POST /api/auth/refresh` - Refresh token

### WeChat Bot
- `POST /api/wechat/test` - Test WeChat notifications
- `POST /api/wechat/broadcast` - Send broadcast message

### Delta Management
- `GET /delta` - Delta Manager web interface
- `GET /api/delta/records` - Get delta records
- `GET /api/delta/stats` - Get delta statistics
- `GET /api/delta/summary` - Get delta summary

## ⚙️ Configuration

### Environment Variables
```bash
# Server configuration
HOST=0.0.0.0
PORT=3001
NODE_ENV=development

# Mock mode (for development/testing)
USE_MOCK_MODE=true

# Deribit environment
USE_TEST_ENVIRONMENT=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/delta_records.db
```

### API Keys Configuration
Edit `config/apikeys.yml`:
```yaml
accounts:
  - name: "main"
    enabled: true
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    wechat_bot:
      enabled: true
      webhook_url: "your_wechat_webhook_url"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

This project is a complete Python port of the original Node.js/TypeScript Deribit webhook service, maintaining 100% functionality while leveraging Python's ecosystem advantages.

---

**Status**: ✅ Production Ready  
**Version**: 1.1.1  
**Last Updated**: 2025-09-16
