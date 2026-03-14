# 🚀 SDModels Backend - Startup Guide

## Quick Start (Development Mode)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Setup

The `.env` file has been created with development defaults. You can start immediately!

**Important**: For production, update these values in `.env`:
- `JWT_SECRET_KEY` - Use a strong random key
- `DATABASE_URL` - Your PostgreSQL connection string
- `S3_ACCESS_KEY` & `S3_SECRET_KEY` - Your S3/R2 credentials
- `STRIPE_SECRET_KEY` - Your Stripe API key
- `SMTP_*` - Your email server settings
- `ADMIN_PASSWORD` - Strong admin password

### 3. Test Application Loading

```bash
python test_startup.py
```

This will verify the application can load without errors.

### 4. Start Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **Health Check**: http://localhost:8000/health

---

## Database Setup (Optional for Development)

If you want to use a real database:

### 1. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

### 2. Create Database

```bash
# Create database
createdb sdmodels

# Or using psql
psql -U postgres
CREATE DATABASE sdmodels;
\q
```

#