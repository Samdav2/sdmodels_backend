# 🐳 Docker Deployment Guide

Complete guide for deploying SDModels backend using Docker and Docker Compose.

---

## 📋 Quick Start

### Development Environment

```bash
# 1. Clone repository
git clone https://github.com/yourusername/sdmodels-backend.git
cd sdmodels-backend

# 2. Copy environment file
cp .env.example .env

# 3. Edit environment variables
nano .env

# 4. Start services
docker-compose up -d

# 5. Run migrations
docker-compose exec backend alembic upgrade head

# 6. Create admin user
docker-compose exec backend python scripts/create_admin_user.py

# 7. Check status
docker-compose ps

# 8. View logs
docker-compose logs -f backend
```

### Production Environment

```bash
# 1. Build production image
docker build -t sdmodels-backend:latest .

# 2. Configure production environment
cp .env.example .env.production
nano .env.production

# 3. Start production services
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 5. Create admin user
docker-compose -f docker-compose.prod.yml exec backend python scripts/create_admin_user.py
```

---

## 🏗️ Architecture

### Services

1. **backend** - FastAPI application (Port 8000)
2. **postgres** - PostgreSQL database (Port 5432)
3. **redis** - Redis cache (Port 6379)
4. **nginx** - Reverse proxy (Ports 80, 443) - Production only
5. **adminer** - Database UI (Port 8080) - Development only

### Network

All services communicate through `sdmodels-network` bridge network.

### Volumes

- `postgres_data` - PostgreSQL data persistence
- `redis_data` - Redis data persistence

---

## 🔧 Configuration

### Environment Variables

Create `.env` file with the following variables:

```env
# Database
POSTGRES_DB=sdmodels
POSTGRES_USER=sdmodels_user
POSTGRES_PASSWORD=your_secure_password_here

# Redis
REDIS_PASSWORD=your_redis_password_here

# Application
SECRET_KEY=generate_with_openssl_rand_hex_32
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

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
AWS_BUCKET_NAME=sdmodels-storage

# Azure Blob (optional)
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_CONTAINER_NAME=sdmodels

# Stripe (optional)
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Generate Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate REDIS_PASSWORD
openssl rand -hex 16
```

---

## 🚀 Deployment Commands

### Development

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: Deletes data!)
docker-compose down -v

# Restart service
docker-compose restart backend

# View logs
docker-compose logs -f backend

# Execute command in container
docker-compose exec backend python scripts/create_admin_user.py

# Access container shell
docker-compose exec backend bash

# Rebuild and restart
docker-compose up -d --build
```

### Production

```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Stop production services
docker-compose -f docker-compose.prod.yml down

# View production logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale backend (multiple instances)
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

---

## 🗄️ Database Management

### Migrations

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Rollback one migration
docker-compose exec backend alembic downgrade -1

# View migration history
docker-compose exec backend alembic history

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### Backup & Restore

```bash
# Backup database
docker-compose exec postgres pg_dump -U sdmodels_user sdmodels > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
docker-compose exec -T postgres psql -U sdmodels_user sdmodels < backup.sql

# Backup with Docker volume
docker run --rm \
  -v sdmodels_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz /data
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U sdmodels_user -d sdmodels

# Using Adminer (Development)
docker-compose --profile tools up -d adminer
# Access: http://localhost:8080
# Server: postgres
# Username: sdmodels_user
# Password: (from .env)
# Database: sdmodels
```

---

## 📊 Monitoring & Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Since timestamp
docker-compose logs --since 2024-01-01T00:00:00 backend
```

### Health Checks

```bash
# Check service status
docker-compose ps

# Check backend health
curl http://localhost:8000/api/v1/health

# Check PostgreSQL
docker-compose exec postgres pg_isready -U sdmodels_user

# Check Redis
docker-compose exec redis redis-cli ping
```

### Resource Usage

```bash
# View resource usage
docker stats

# View specific container
docker stats sdmodels-backend
```

---

## 🔒 Security

### Production Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY (32+ characters)
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure firewall rules
- [ ] Limit database access
- [ ] Use secrets management (Docker Secrets, Vault)
- [ ] Enable Redis password authentication
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity
- [ ] Backup data regularly

### SSL Configuration

```bash
# Generate self-signed certificate (Development)
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem

# Use Let's Encrypt (Production)
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  certbot/certbot certonly \
  --standalone \
  -d api.sdmodels.com
```

---

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Check container status
docker-compose ps

# Inspect container
docker inspect sdmodels-backend

# Remove and recreate
docker-compose down
docker-compose up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U sdmodels_user -d sdmodels -c "SELECT 1;"

# Check DATABASE_URL format
docker-compose exec backend env | grep DATABASE_URL
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Host:Container
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker system
docker system prune -a

# Remove unused volumes
docker volume prune

# Remove specific volume (CAUTION: Deletes data!)
docker volume rm sdmodels_postgres_data
```

### Slow Performance

```bash
# Check resource usage
docker stats

# Increase resources in Docker Desktop
# Settings > Resources > Advanced

# Optimize PostgreSQL
docker-compose exec postgres psql -U sdmodels_user -d sdmodels
VACUUM ANALYZE;
```

---

## 🔄 Updates & Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build backend

# Restart with new image
docker-compose up -d backend

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Update Dependencies

```bash
# Update requirements.txt
# Then rebuild
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Database Maintenance

```bash
# Vacuum database
docker-compose exec postgres psql -U sdmodels_user -d sdmodels -c "VACUUM ANALYZE;"

# Reindex database
docker-compose exec postgres psql -U sdmodels_user -d sdmodels -c "REINDEX DATABASE sdmodels;"

# Check database size
docker-compose exec postgres psql -U sdmodels_user -d sdmodels -c "
SELECT pg_size_pretty(pg_database_size('sdmodels'));"
```

---

## 📈 Scaling

### Horizontal Scaling

```bash
# Run multiple backend instances
docker-compose up -d --scale backend=3

# Use load balancer (nginx)
# Configure upstream in nginx.conf
```

### Vertical Scaling

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## 🧪 Testing

### Run Tests in Container

```bash
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app

# Run specific test
docker-compose exec backend pytest tests/test_auth.py
```

### Test Email System

```bash
docker-compose exec backend python test_email_system.py
```

---

## 📚 Additional Resources

### Useful Commands

```bash
# View container IP
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' sdmodels-backend

# Copy files from container
docker cp sdmodels-backend:/app/logs ./logs

# Copy files to container
docker cp ./config.json sdmodels-backend:/app/config.json

# Export container as image
docker commit sdmodels-backend sdmodels-backend:backup

# Save image to file
docker save sdmodels-backend:latest > sdmodels-backend.tar

# Load image from file
docker load < sdmodels-backend.tar
```

### Docker Compose Profiles

```bash
# Start with tools (Adminer)
docker-compose --profile tools up -d

# Start without tools
docker-compose up -d
```

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] Secrets generated
- [ ] SSL certificates obtained
- [ ] Firewall rules configured
- [ ] Backup strategy planned

### Deployment
- [ ] Build production image
- [ ] Start services
- [ ] Run database migrations
- [ ] Create admin user
- [ ] Verify health checks
- [ ] Test API endpoints

### Post-Deployment
- [ ] Monitor logs
- [ ] Check resource usage
- [ ] Test email system
- [ ] Verify backups
- [ ] Document deployment

---

## 🆘 Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review troubleshooting section
3. Check GitHub issues
4. Contact support team

---

**Happy Deploying!** 🚀
