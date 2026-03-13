# 📦 SDModels Backend - Installation Guide

## Quick Install

### Option 1: Using the Install Script (Recommended)

```bash
# Make the script executable (if not already)
chmod +x install.sh

# Run the installation
./install.sh
```

### Option 2: Using Python Script Directly

```bash
python3 install_dependencies.py
```

### Option 3: Manual Installation

```bash
# Upgrade pip first
python3 -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

---

## Prerequisites

### Required
- **Python 3.8+** (Python 3.10+ recommended)
- **pip** (Python package manager)
- **PostgreSQL 12+** (for production)

### Optional
- **Redis** (for caching)
- **Virtual Environment** (recommended)

---

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd sdmodels_backend
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Using the install script
./install.sh

# OR manually
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

**Required Environment Variables:**
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/sdmodels

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@sdmodels.com
EMAILS_FROM_NAME=SDModels

# Frontend
FRONTEND_URL=http://localhost:3000

# Storage (Optional)
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_CONTAINER_NAME=sdmodels

# Payment (Optional)
STRIPE_SECRET_KEY=your-stripe-key
PAYSTACK_SECRET_KEY=your-paystack-key
```

### 5. Set Up Database

```bash
# Create database (PostgreSQL)
createdb sdmodels

# Run migrations
alembic upgrade head

# Create admin user (optional)
python scripts/create_admin_user.py
```

### 6. Start the Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 7. Verify Installation

Visit: http://localhost:8000/docs

You should see the FastAPI interactive documentation.

---

## Installed Packages

### Core Framework
- **fastapi** - Modern web framework
- **uvicorn** - ASGI server
- **python-multipart** - File upload support

### Database
- **sqlmodel** - SQL database ORM
- **sqlalchemy** - Database toolkit
- **asyncpg** - PostgreSQL async driver
- **alembic** - Database migrations
- **psycopg2-binary** - PostgreSQL adapter

### Authentication & Security
- **python-jose** - JWT tokens
- **pyjwt** - JSON Web Tokens
- **passlib** - Password hashing
- **cryptography** - Cryptographic recipes

### Configuration
- **pydantic** - Data validation
- **pydantic-settings** - Settings management
- **python-dotenv** - Environment variables

### Email System
- **jinja2** - Template engine
- **aiosmtplib** - Async SMTP client

### HTTP & APIs
- **httpx** - Async HTTP client
- **requests** - HTTP library

### Cloud Storage
- **boto3** - AWS SDK
- **azure-storage-blob** - Azure Blob Storage

### Payment Processing
- **stripe** - Stripe payment gateway

### Caching
- **redis** - Redis client

### Google OAuth
- **google-auth** - Google authentication
- **google-auth-oauthlib** - OAuth 2.0
- **google-auth-httplib2** - HTTP transport

### Utilities
- **python-dateutil** - Date utilities
- **pytz** - Timezone support

---

## Troubleshooting

### Issue: pip not found

```bash
# Install pip
python3 -m ensurepip --upgrade
```

### Issue: Permission denied

```bash
# Use --user flag
pip install --user -r requirements.txt

# OR use sudo (not recommended)
sudo pip install -r requirements.txt
```

### Issue: PostgreSQL connection error

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Check connection
psql -U postgres -c "SELECT version();"
```

### Issue: Module not found after installation

```bash
# Verify installation
pip list | grep fastapi

# Reinstall specific package
pip install --force-reinstall fastapi
```

### Issue: Conflicting dependencies

```bash
# Clear pip cache
pip cache purge

# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt
```

---

## Development Setup

### Install Development Dependencies

```bash
# Install with dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8 mypy
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Code Formatting

```bash
# Format code with black
black app/

# Check code style
flake8 app/

# Type checking
mypy app/
```

---

## Docker Installation (Alternative)

### Using Docker Compose

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Dockerfile

```bash
# Build image
docker build -t sdmodels-backend .

# Run container
docker run -p 8000:8000 --env-file .env sdmodels-backend
```

---

## Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Using Systemd Service

Create `/etc/systemd/system/sdmodels.service`:

```ini
[Unit]
Description=SDModels Backend API
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/sdmodels_backend
Environment="PATH=/var/www/sdmodels_backend/venv/bin"
ExecStart=/var/www/sdmodels_backend/venv/bin/gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable sdmodels
sudo systemctl start sdmodels
sudo systemctl status sdmodels
```

---

## Verification Checklist

After installation, verify:

- [ ] All dependencies installed: `pip list`
- [ ] Database connected: `alembic current`
- [ ] Server starts: `uvicorn app.main:app`
- [ ] API docs accessible: http://localhost:8000/docs
- [ ] Email system configured: Check `.env` SMTP settings
- [ ] Admin user created: `python scripts/create_admin_user.py`

---

## Getting Help

### Check Logs

```bash
# Application logs
tail -f logs/app.log

# Uvicorn logs
uvicorn app.main:app --log-level debug
```

### Common Commands

```bash
# Check Python version
python3 --version

# Check pip version
pip --version

# List installed packages
pip list

# Show package info
pip show fastapi

# Check for outdated packages
pip list --outdated
```

### Resources

- **Documentation**: See `README.md`
- **Email System**: See `EMAIL_SYSTEM_GUIDE.md`
- **API Docs**: http://localhost:8000/docs
- **Database Migrations**: `alembic --help`

---

## Next Steps

After successful installation:

1. ✅ Configure `.env` file
2. ✅ Set up database
3. ✅ Run migrations
4. ✅ Create admin user
5. ✅ Test email system
6. ✅ Start development server
7. ✅ Access API documentation

---

**Installation Complete!** 🎉

Your SDModels backend is now ready for development.
