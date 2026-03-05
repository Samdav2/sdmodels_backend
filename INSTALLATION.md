# 🚀 SDModels Backend - Installation Guide

Complete installation guide for the SDModels backend API.

---

## 📋 Prerequisites

### Required Software
- **Python**: 3.11 or higher
- **PostgreSQL**: 14 or higher
- **Redis**: 7.0 or higher (for caching)
- **Docker** (optional): For containerized deployment
- **Git**: For version control

### System Requirements
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: Minimum 10GB free space
- **OS**: Linux, macOS, or Windows with WSL2

---

## 🐳 Docker Installation (Recommended)

### 1. Prerequisites
```bash
# Install Docker and Docker Compose
# Linux
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS
brew install docker docker-compose

# Windows
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
```

### 2. Clone Repository
```bash
git clone https://github.com/yourusername/sdmodels-backend.git
cd sdmodels-backend
```

### 3. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 4. Build and Run
```bash
# Build Docker image
docker build -t sdmodels-backend .

# Run with Docker Compose (includes PostgreSQL and Redis)
docker-compose up -d

# Or run standalone
docker run -d \
  --name sdmodels-backend \
  -p 8000:8000 \
  --env-file .env \
  sdmodels-backend
```

### 5. Initialize Database
```bash
# Run migrations
docker exec sdmodels-backend alembic upgrade head

# Create admin user
docker exec -it sdmodels-backend python scripts/create_admin_user.py
```

### 6. Verify Installation
```bash
# Check logs
docker logs sdmodels-backend

# Test API
curl http://localhost:8000/api/v1/health
```

---

## 💻 Local Installation

### 1. Install Python Dependencies

#### Using pip
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### Using conda
```bash
# Create conda environment
conda create -n sdmodels python=3.11

# Activate environment
conda activate sdmodels

# Install dependencies
pip install -r requirements.txt
```

### 2. Install PostgreSQL

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### macOS
```bash
brew install postgresql@14
brew services start postgresql@14
```

#### Windows
Download and install from: https://www.postgresql.org/download/windows/

### 3. Install Redis

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### macOS
```bash
brew install redis
brew services start redis
```

#### Windows
Download from: https://github.com/microsoftarchive/redis/releases

### 4. Create Database
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE sdmodels;
CREATE USER sdmodels_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE sdmodels TO sdmodels_user;
\q
```

### 5. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

Required environment variables:
```env
# Database
DATABASE_URL=postgresql+asyncpg://sdmodels_user:your_secure_password@localhost:5432/sdmodels

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here-generate-with-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@sdmodels.com
EMAILS_FROM_NAME=SDModels

# Frontend
FRONTEND_URL=http://localhost:3000

# Storage (choose one)
# AWS S3
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
AWS_BUCKET_NAME=sdmodels-storage

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_CONTAINER_NAME=sdmodels

# Payment
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 6. Run Database Migrations
```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Run migrations
alembic upgrade head
```

### 7. Create Admin User
```bash
python scripts/create_admin_user.py
```

### 8. Start Development Server
```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the provided script
python -m uvicorn app.main:app --reload
```

### 9. Verify Installation
```bash
# Test API health
curl http://localhost:8000/api/v1/health

# View API documentation
open http://localhost:8000/docs
```

---

## 🔧 Configuration

### Environment Variables

#### Required
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key (generate with `openssl rand -hex 32`)
- `REDIS_URL` - Redis connection string

#### Optional
- `SMTP_*` - Email configuration
- `AWS_*` or `AZURE_*` - Cloud storage
- `STRIPE_*` - Payment processing
- `GOOGLE_*` - OAuth authentication

### Generate Secret Key
```bash
# Generate secure secret key
openssl rand -hex 32
```

### SMTP Configuration

#### Gmail
1. Enable 2-factor authentication
2. Generate app password: https://myaccount.google.com/apppasswords
3. Use app password in `SMTP_PASSWORD`

#### SendGrid
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

#### AWS SES
```env
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
```

---

## 🗄️ Database Setup

### Run Migrations
```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# View migration history
alembic history

# Create new migration
alembic revision --autogenerate -m "description"
```

### Initialize Data
```bash
# Create admin user
python scripts/create_admin_user.py

# Setup bounty system
python scripts/setup_bounty_tables.py

# Setup wallet system
python scripts/create_wallet_system.py

# Setup payment tables
python scripts/create_payment_tables.py
```

---

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_register_user
```

### Test Email System
```bash
python test_email_system.py
```

---

## 🚀 Production Deployment

### Using Docker

#### 1. Build Production Image
```bash
docker build -t sdmodels-backend:latest .
```

#### 2. Run with Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    image: sdmodels-backend:latest
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: sdmodels
      POSTGRES_USER: sdmodels_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Using Systemd (Linux)

#### 1. Create Service File
```bash
sudo nano /etc/systemd/system/sdmodels.service
```

```ini
[Unit]
Description=SDModels Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=sdmodels
WorkingDirectory=/opt/sdmodels-backend
Environment="PATH=/opt/sdmodels-backend/venv/bin"
ExecStart=/opt/sdmodels-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable sdmodels
sudo systemctl start sdmodels
sudo systemctl status sdmodels
```

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.sdmodels.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.sdmodels.com
```

---

## 🔍 Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -U sdmodels_user -d sdmodels

# Check DATABASE_URL format
# Correct: postgresql+asyncpg://user:pass@host:5432/dbname
```

### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

### Import Errors
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

### Migration Errors
```bash
# Reset migrations (CAUTION: Development only!)
alembic downgrade base
alembic upgrade head

# Or drop and recreate database
dropdb sdmodels
createdb sdmodels
alembic upgrade head
```

### Email Not Sending
```bash
# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print('SMTP connection successful!')
server.quit()
"
```

---

## 📚 Additional Resources

### Documentation
- API Documentation: http://localhost:8000/docs
- Email System: `EMAIL_SYSTEM_GUIDE.md`
- Architecture: `ARCHITECTURE_DIAGRAM.txt`

### Scripts
- `scripts/create_admin_user.py` - Create admin account
- `scripts/init_db.py` - Initialize database
- `test_email_system.py` - Test email functionality

### Support
- GitHub Issues: https://github.com/yourusername/sdmodels-backend/issues
- Documentation: https://docs.sdmodels.com

---

## ✅ Installation Checklist

- [ ] Python 3.11+ installed
- [ ] PostgreSQL 14+ installed and running
- [ ] Redis 7+ installed and running
- [ ] Virtual environment created
- [ ] Dependencies installed from requirements.txt
- [ ] Database created
- [ ] .env file configured
- [ ] Database migrations run
- [ ] Admin user created
- [ ] Development server starts successfully
- [ ] API health check passes
- [ ] Email system configured (optional)
- [ ] Cloud storage configured (optional)
- [ ] Payment gateway configured (optional)

---

**Installation Complete!** 🎉

Your SDModels backend is now ready for development or production use.

For questions or issues, please refer to the troubleshooting section or create an issue on GitHub.
