# SDModels Backend API

Complete FastAPI backend for SDModels - A premium 3D models marketplace platform.

## 🏗️ Architecture

This project follows a clean layered architecture:

```
app/
├── api/                    # API Layer (Routes & Endpoints)
│   └── v1/
│       ├── endpoints/      # API endpoint handlers
│       └── router.py       # Main API router
├── services/               # Service Layer (Business Logic)
├── repositories/           # Repository Layer (Data Access)
├── models/                 # Database Models (SQLModel)
├── schemas/                # Pydantic Schemas (Request/Response)
├── core/                   # Core functionality
│   ├── config.py          # Configuration
│   ├── security.py        # Authentication & Security
│   └── dependencies.py    # FastAPI dependencies
├── db/                     # Database configuration
│   └── session.py         # Database session management
└── templates/              # Email templates
    └── emails/            # HTML email templates
```

## 🚀 Features

### Core Features
- ✅ User Authentication (JWT + OAuth)
- ✅ User Management & Profiles
- ✅ 3D Model Upload & Management
- ✅ Marketplace & Transactions
- ✅ Shopping Cart & Checkout
- ✅ Community System
- ✅ Support Ticket System
- ✅ Admin Dashboard
- ✅ Email Notifications

### Technical Features
- Async/Await with AsyncIO
- PostgreSQL with SQLModel ORM
- Redis for caching
- S3/CloudFlare R2 for file storage
- Stripe payment integration
- JWT authentication
- OAuth 2.0 (Google, GitHub, Discord)
- Email templates (HTML)
- API documentation (Swagger/ReDoc)

## 📋 Requirements

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- S3-compatible storage (AWS S3 or CloudFlare R2)

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd sdmodels-backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Setup database

```bash
# Create PostgreSQL database
createdb sdmodels

# Run migrations (if using Alembic)
alembic upgrade head
```

### 6. Run the application

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📚 API Documentation

Once the server is running, access the API documentation at:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 🔑 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password
- `POST /api/v1/auth/verify-email` - Verify email
- `POST /api/v1/auth/refresh` - Refresh access token

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update profile
- `GET /api/v1/users/{user_id}` - Get user profile
- `POST /api/v1/users/{user_id}/follow` - Follow user
- `DELETE /api/v1/users/{user_id}/follow` - Unfollow user

### Models
- `POST /api/v1/models` - Upload model
- `GET /api/v1/models` - List models (with filters)
- `GET /api/v1/models/{model_id}` - Get model details
- `PUT /api/v1/models/{model_id}` - Update model
- `DELETE /api/v1/models/{model_id}` - Delete model
- `POST /api/v1/models/{model_id}/like` - Like model
- `POST /api/v1/models/{model_id}/comments` - Add comment

### Communities
- `POST /api/v1/communities` - Create community
- `GET /api/v1/communities` - List communities
- `GET /api/v1/communities/{id}` - Get community
- `POST /api/v1/communities/{id}/join` - Join community
- `POST /api/v1/communities/{id}/posts` - Create post
- `GET /api/v1/communities/{id}/posts` - Get posts

### Transactions
- `POST /api/v1/transactions/cart` - Add to cart
- `GET /api/v1/transactions/cart` - Get cart
- `POST /api/v1/transactions/checkout` - Checkout
- `GET /api/v1/transactions/purchases` - Get purchases
- `GET /api/v1/transactions/purchases/{model_id}/download` - Download model

### Support
- `POST /api/v1/support/tickets` - Create ticket
- `GET /api/v1/support/tickets` - Get tickets
- `POST /api/v1/support/tickets/{id}/messages` - Send message

### Admin
- `GET /api/v1/admin/stats` - Dashboard stats
- `GET /api/v1/admin/users` - Manage users
- `GET /api/v1/admin/models` - Moderate models
- `PUT /api/v1/admin/models/{id}/approve` - Approve model
- `GET /api/v1/admin/reports` - View reports

## 🗄️ Database Models

### Core Models
- **User** - User accounts
- **UserProfile** - Extended user info
- **AdminUser** - Admin roles
- **Model** - 3D models
- **Transaction** - Payments
- **Purchase** - User purchases
- **Cart** - Shopping cart

### Community Models
- **Community** - Community groups
- **CommunityMember** - Memberships
- **CommunityPost** - Posts
- **PostReaction** - Reactions
- **PostComment** - Comments

### Support Models
- **SupportTicket** - Support tickets
- **SupportMessage** - Ticket messages

## 📧 Email Templates

Professional HTML email templates included:
- Welcome email
- Email verification
- Password reset
- Model approved
- Purchase confirmation
- New sale notification

All templates match the frontend design with dark theme and modern styling.

## 🔒 Security

- JWT token authentication
- Password hashing with bcrypt
- OAuth 2.0 integration
- CORS configuration
- Rate limiting (recommended)
- Input validation
- SQL injection prevention

## 🚀 Deployment

### Using Docker

```bash
# Build image
docker build -t sdmodels-api .

# Run container
docker run -p 8000:8000 --env-file .env sdmodels-api
```

### Using Docker Compose

```bash
docker-compose up -d
```

### Manual Deployment

1. Setup PostgreSQL and Redis
2. Configure environment variables
3. Run database migrations
4. Start application with production server
5. Setup reverse proxy (Nginx)
6. Configure SSL certificate

## 📊 Monitoring

Recommended monitoring tools:
- **Sentry** - Error tracking
- **DataDog** - Performance monitoring
- **Prometheus** - Metrics
- **Grafana** - Dashboards

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📝 Environment Variables

See `.env.example` for all required environment variables.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET_KEY` - JWT signing key
- `STRIPE_SECRET_KEY` - Stripe API key
- `S3_BUCKET_NAME` - S3 bucket for file storage

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support, email support@sdmodels.com or join our Discord community.

## 🎯 Roadmap

- [ ] WebSocket support for real-time features
- [ ] GraphQL API
- [ ] Advanced analytics
- [ ] AI-powered model recommendations
- [ ] Blockchain integration for NFTs
- [ ] Mobile app API optimization

---

**Built with ❤️ by the SDModels Team**
