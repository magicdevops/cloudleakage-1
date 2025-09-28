# 🐳 Docker Setup for CloudLeakage (PostgreSQL Only)

This directory contains Docker configuration for running **only PostgreSQL** in a container, while running the CloudLeakage application on your host machine.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐
│   Host Machine  │    │  Docker Container │
│                 │    │                   │
│  CloudLeakage   │◄──►│   PostgreSQL     │
│  Application    │    │   Database       │
│                 │    │                   │
│  • Python/Flask │    │  • postgres:15   │
│  • Runs locally │    │  • Persistent    │
│  • Development  │    │  • Production    │
└─────────────────┘    └──────────────────┘
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Copy and edit environment configuration
cp ../.env.example ../.env
# Edit .env file with your settings
```

### 2. Start PostgreSQL Container
```bash
cd docker
docker-compose up -d postgres
```

### 3. Run Application Locally
```bash
# In the main project directory
python app.py
```

### 4. Access Application
- **Web Application**: http://localhost:5000
- **Dashboard**: http://localhost:5000/dashboard

## 🗄️ Database Access

### PostgreSQL Container
- **Container**: `cloudleakage-postgres`
- **Database**: `cloudleakage`
- **User**: `app_user`
- **Password**: `app_pass`
- **Port**: `5432`

### Connect to Database
```bash
# From host machine
psql -h localhost -p 5432 -U app_user -d cloudleakage

# From another container
docker-compose exec postgres psql -U app_user -d cloudleakage
```

## 🔧 Management Commands

### Start PostgreSQL
```bash
docker-compose up -d postgres
```

### Stop PostgreSQL
```bash
docker-compose down postgres
```

### View Logs
```bash
docker-compose logs -f postgres
```

### Restart Database
```bash
docker-compose restart postgres
```

## 📊 Optional: Redis Cache

To also run Redis for caching:

```bash
# Start both PostgreSQL and Redis
docker-compose --profile redis up -d

# Or start Redis separately
docker-compose up -d redis
```

## 🔍 Development Workflow

### Typical Development Session
```bash
# 1. Start database
cd docker && docker-compose up -d postgres

# 2. Run application locally (in another terminal)
cd .. && python app.py

# 3. Develop and test
# 4. View database logs if needed
docker-compose logs -f postgres

# 5. Stop database when done
docker-compose down
```

### Database Persistence
- Database files are stored in Docker volume: `docker_postgres_data`
- Data persists across container restarts
- Safe to stop/start containers

## 🔒 Security Notes

- Change default passwords in `.env` file for production
- Use strong, unique passwords
- Consider SSL/TLS for production connections
- Database is accessible on localhost:5432 from host machine

## 🚨 Troubleshooting

### PostgreSQL Connection Issues
1. Check if container is running: `docker-compose ps`
2. View logs: `docker-compose logs postgres`
3. Test connection: `docker-compose exec postgres pg_isready -U app_user -d cloudleakage`

### Port Conflicts
If port 5432 is already in use:
```bash
# Check what's using the port
netstat -tlnp | grep :5432

# Or use different port
docker-compose up -d postgres -p 5433:5432
```

### Permission Issues
```bash
# Fix Docker permissions if needed
sudo chown $USER:$USER /var/run/docker.sock
```

## 📈 Benefits of This Setup

✅ **Best of Both Worlds**: Containerized database + local development
✅ **Fast Development**: No container rebuild for code changes
✅ **Easy Debugging**: Direct access to application logs and debugger
✅ **Database Safety**: Persistent, backed up, containerized data
✅ **Resource Efficient**: Only database in container, app on host
