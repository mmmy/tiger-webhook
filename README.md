# Tiger Brokers Trading System

A comprehensive Python-based options trading system for Tiger Brokers, designed to handle TradingView webhook signals and perform automated US options trading operations. This system provides a complete trading infrastructure with real-time position management, delta hedging, and advanced order execution strategies.

## 🎯 Project Status: **PRODUCTION READY**

This system has been completely refactored to use Tiger Brokers as the exclusive trading platform, providing seamless US options trading capabilities.

## 🏗️ Architecture

### Technology Stack
- **Web Framework**: FastAPI for high-performance API endpoints
- **Trading Platform**: Tiger Brokers API for US options trading
- **Type System**: Pydantic models for robust data validation
- **HTTP Client**: httpx for async HTTP operations
- **Database**: aiosqlite + SQLAlchemy (async SQLite)
- **Configuration**: YAML + Pydantic Settings
- **Authentication**: Tiger Brokers RSA key authentication

### Project Structure
```
tiger_trading_system/
├── src/                           # Main application package
│   └── deribit_webhook/           # Core application module (legacy name)
│       ├── api/                   # Tiger Brokers API clients
│       │   └── __init__.py        # API module initialization
│       ├── config/                # Configuration management
│       │   ├── config_loader.py   # Configuration loader
│       │   └── settings.py        # Application settings
│       ├── database/              # Database operations
│       │   ├── delta_manager.py   # Delta records management
│       │   └── types.py           # Database type definitions
│       ├── middleware/            # FastAPI middleware
│       │   ├── account_validation.py # Account validation middleware
│       │   ├── error_handler.py   # Error handling middleware
│       │   └── security.py        # Security middleware
│       ├── models/                # Pydantic type definitions
│       │   ├── auth_types.py      # Authentication types
│       │   ├── config_types.py    # Configuration types
│       │   ├── tiger_types.py     # Tiger Brokers API types
│       │   ├── trading_types.py   # Trading types
│       │   └── webhook_types.py   # Webhook types
│       ├── routes/                # API route handlers
│       │   ├── auth.py            # Authentication routes
│       │   ├── delta.py           # Delta management routes
│       │   ├── health.py          # Health check routes
│       │   ├── logs.py            # Logging routes
│       │   ├── positions.py       # Position management routes
│       │   ├── trading.py         # Trading routes
│       │   ├── webhook.py         # Webhook routes
│       │   └── wechat.py          # WeChat notification routes
│       ├── services/              # Business logic services
│       │   ├── auth_service.py    # Authentication service
│       │   ├── authentication_errors.py # Auth error handling
│       │   ├── background_tasks.py # Background task management
│       │   ├── tiger_client.py    # Main Tiger Brokers client
│       │   ├── trading_client_factory.py # Trading client factory
│       │   ├── option_service.py  # Option trading service
│       │   ├── option_trading_service.py # Advanced trading logic
│       │   ├── polling_manager.py # Position polling manager
│       │   ├── position_adjustment.py # Position adjustment logic
│       │   ├── progressive_limit_strategy.py # Progressive limit orders
│       │   └── wechat_notification.py # WeChat notifications
│       ├── utils/                 # Utility functions
│       │   ├── calculation_utils.py # Mathematical calculations
│       │   ├── logging_config.py  # Logging configuration
│       │   ├── price_utils.py     # Price calculation utilities
│       │   ├── response_utils.py  # API response utilities
│       │   ├── spread_calculation.py # Spread calculation engine
│       │   └── validation_utils.py # Input validation utilities
│       ├── app.py                 # FastAPI application factory
│       └── main.py                # Application entry point
├── public/                        # Static files and dashboard
│   ├── static/                    # Static assets (CSS, JS, images)
│   ├── delta-manager.html         # Delta management interface
│   ├── index.html                 # Main dashboard
│   └── logs.html                  # Logging interface
├── config/                        # Configuration files
│   ├── apikeys.example.yml        # API keys template
│   └── apikeys.yml                # Tiger Brokers API configuration
├── tests/                         # Test suite
│   ├── integration/               # Integration tests
│   ├── unit/                      # Unit tests
│   └── conftest.py                # Test configuration
├── docs/                          # Documentation
│   ├── 技术需求文档/              # Technical requirements (Chinese)
│   ├── API.md                     # API documentation
│   ├── CONFIGURATION.md           # Configuration guide
│   ├── DEPLOYMENT.md              # Deployment guide
│   └── LOGGING.md                 # Logging documentation
├── logs/                          # Application logs
├── data/                          # Database and data files
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration
├── Dockerfile                     # Docker configuration
├── docker-compose.yml             # Docker Compose setup
├── deploy.sh                      # Deployment script
├── Makefile                       # Build automation
└── nginx.conf                     # Nginx configuration
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip or conda

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd tiger_trading_system
pip install -r requirements.txt
pip install -e .
```

2. **Configure Tiger Brokers API:**
```bash
# Copy example configuration
cp config/apikeys.example.yml config/apikeys.yml

# Edit with your Tiger Brokers credentials
nano config/apikeys.yml

# Add your Tiger Brokers private key
cp your_tiger_private_key.pem keys/tiger_private_key.pem
```

3. **Set environment variables:**
```bash
# Copy example environment file
cp .env.example .env

# Edit environment settings
nano .env
```

4. **Run the service:**

**Linux/macOS:**
```bash
# Development mode with auto-reload
make dev

# Or directly with uvicorn (from project root)
uvicorn src.deribit_webhook.app:app --reload --host 0.0.0.0 --port 3001

# Or from src directory
cd src && uvicorn deribit_webhook.app:app --reload --host 0.0.0.0 --port 3001

# Production mode
make run

# Alternative: run with Python directly
cd src && python -m deribit_webhook.main
```

**Windows (PowerShell):**
```powershell
# Install dependencies
pip install -r requirements.txt

# Copy configuration files
copy .env.example .env
copy config\apikeys.example.yml config\apikeys.yml

# Development mode with auto-reload (from project root)
uvicorn src.deribit_webhook.app:app --reload --host 0.0.0.0 --port 3001

# Or from src directory
cd src
uvicorn deribit_webhook.app:app --reload --host 0.0.0.0 --port 3001

# Alternative: run with Python directly
cd src
python -m deribit_webhook.main
```

## 📊 Features

### 🐅 Tiger Brokers Integration
- **US Options Trading**: Complete support for US equity options
- **Real-time Market Data**: Live quotes and market information
- **Advanced Order Types**: Market, limit, and conditional orders
- **Portfolio Management**: Real-time position tracking and P&L
- **Risk Management**: Built-in position limits and risk controls

### ✅ Core Trading System
- TradingView webhook signal processing
- Automated US options trading with Tiger Brokers
- Position management and delta calculation
- Real-time position polling and monitoring
- Advanced order execution strategies

### ✅ Authentication & Security
- Tiger Brokers RSA key authentication
- Secure API communication
- Rate limiting and request throttling
- Webhook signature verification
- Account validation and authorization

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
docker build -t tiger-trading-system .

# Run container
docker run -p 3001:3001 -v $(pwd)/config:/app/config tiger-trading-system
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

# Tiger Brokers environment
USE_TEST_ENVIRONMENT=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/delta_records.db
```

### Tiger Brokers API Configuration
Edit `config/apikeys.yml`:
```yaml
accounts:
  - name: "tiger_main"
    enabled: true
    tiger_id: "your_tiger_id"
    private_key_path: "keys/tiger_private_key.pem"
    account: "your_account_number"
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

This system represents a complete evolution from a multi-broker trading platform to a specialized Tiger Brokers US options trading system, providing enhanced performance and simplified architecture.

---

**Status**: ✅ Production Ready
**Version**: 2.0.0
**Last Updated**: 2025-09-20
**Trading Platform**: Tiger Brokers (US Options)
