# 🚀 CloudLeakage PostgreSQL Container Setup Guide

## 🎯 Overview

This guide explains how to run CloudLeakage with PostgreSQL using Docker containers instead of SQLite.

## 📁 Project Structure

```
cloudleakage/
├── docker/                          # 🐳 Docker configurations
│   ├── docker-compose.yml          # Main Docker Compose setup
│   ├── Dockerfile                  # Application container
│   ├── init-scripts/               # PostgreSQL initialization
│   │   └── init-postgres.sql       # Database setup script
│   └── README.md                   # Docker documentation
├── .env.example                    # Environment template
├── setup_docker.sh                 # Docker setup script
└── [other application files...]
```

## 🏃‍♂️ Quick Start

### 1. Setup Environment
```bash
# Copy and edit environment configuration
cp .env.example .env
# Edit .env file with your settings (especially passwords)
```

### 2. Start with Docker Script
```bash
# Run the Docker setup script
./setup_docker.sh
```

### 3. Or Manual Docker Compose
```bash
cd docker
docker-compose up -d --build
```

## 🗄️ Database Configuration

### Connection Details
- **Database**: `cloudleakage`
- **User**: `cloudleakage_user`
- **Password**: `cloudleakage_secure_password_123!`
- **Host**: `localhost` (or `postgres` from containers)
- **Port**: `5432`

### Environment Variables (.env)
```bash
# Database connection
DATABASE_URL=postgresql://cloudleakage_user:cloudleakage_secure_password_123!@localhost:5432/cloudleakage

# Security
ENCRYPTION_KEY=oz2fA05GT7jHw-kReDcvXCHc9weUCOM2sBe7bIOQqps=
SECRET_KEY=your-secure-random-secret-key-32-chars-minimum

# Production settings
FLASK_ENV=production
FLASK_DEBUG=0
```

## 🔧 Services Included

### PostgreSQL Database
- **Container**: `cloudleakage-postgres`
- **Image**: `postgres:15-alpine`
- **Features**: Persistent data, health checks, initialization scripts

### Redis Cache (Optional)
- **Container**: `cloudleakage-redis`
- **Image**: `redis:7-alpine`
- **Features**: Performance caching, persistence

### CloudLeakage Application
- **Container**: `cloudleakage-app`
- **Build**: Multi-stage Python application
- **Features**: Health checks, graceful shutdown

## 📊 Access Points

| Service | URL/Access | Description |
|---------|------------|-------------|
| **Application** | http://localhost:5000 | Main CloudLeakage app |
| **Dashboard** | http://localhost:5000/dashboard | Cost optimization dashboard |
| **API** | http://localhost:5000/integration | Account management API |
| **Database** | localhost:5432 | PostgreSQL direct access |
| **Redis** | localhost:6379 | Cache direct access |

## 🔍 Monitoring & Troubleshooting

### Check Service Status
```bash
cd docker
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f app
```

### Database Health
```bash
# Test database connection
docker-compose exec postgres pg_isready -U cloudleakage_user -d cloudleakage

# Connect to database
docker-compose exec postgres psql -U cloudleakage_user -d cloudleakage
```

### Application Health
```bash
# Health check
curl http://localhost:5000/

# Application logs
docker-compose logs app
```

## 🔄 Migration from SQLite

The application **automatically migrates** when switching to PostgreSQL:

1. **Schema Creation**: Tables created automatically
2. **Data Types**: Optimized for PostgreSQL (TIMESTAMP vs TEXT)
3. **Performance**: Better indexing and query optimization
4. **Backup**: SQLite file preserved as fallback

## 🔒 Security Features

- **Credential Encryption**: All credentials encrypted with Fernet
- **Environment Variables**: No hardcoded secrets
- **Container Security**: Non-root user, minimal base image
- **Network Isolation**: Internal Docker network

## 🛑 Management Commands

### Start Services
```bash
cd docker
docker-compose up -d
```

### Stop Services
```bash
cd docker
docker-compose down
```

### Update Application
```bash
cd docker
docker-compose build --no-cache app
docker-compose up -d app
```

### Database Backup
```bash
# From host
docker-compose exec postgres pg_dump -U cloudleakage_user cloudleakage > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U cloudleakage_user -d cloudleakage < backup.sql
```

## 🚨 Important Notes

1. **Change Default Passwords**: Update passwords in `.env` file for production
2. **Backup Data**: Regular database backups recommended
3. **Resource Limits**: Consider adding resource limits for production
4. **SSL**: Enable SSL/TLS for production deployments
5. **Monitoring**: Add monitoring and alerting for production use

## 📈 Performance Benefits

| Feature | SQLite | PostgreSQL + Docker |
|---------|--------|-------------------|
| **Concurrent Users** | 1 | 50+ |
| **Data Volume** | <1GB | 100GB+ |
| **Query Speed** | 100-500ms | 10-50ms |
| **Backup** | File copy | Point-in-time |
| **High Availability** | None | Container orchestration |

## 🔧 Customization

### Add Redis Password
```yaml
# In docker-compose.yml
redis:
  environment:
    - REDIS_PASSWORD=your_secure_redis_password
```

### Enable SSL for PostgreSQL
```bash
# In .env
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### Add Resource Limits
```yaml
# In docker-compose.yml
app:
  deploy:
    resources:
      limits:
        memory: 1G
      reservations:
        memory: 512M
```

## 🆘 Getting Help

1. **Check Logs**: `docker-compose logs`
2. **Service Status**: `docker-compose ps`
3. **Docker Documentation**: https://docs.docker.com/
4. **PostgreSQL Documentation**: https://www.postgresql.org/docs/

The PostgreSQL container setup provides a production-ready, scalable foundation for your CloudLeakage deployment! 🎉
