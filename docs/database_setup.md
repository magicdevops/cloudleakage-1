# CloudLeakage Database Setup Guide

## 🗄️ Database Integration Overview

CloudLeakage now uses a robust database system for storing cloud account credentials and cost data. The system supports multiple database options with secure credential encryption.

## 📋 Database Options

### 1. SQLite (Default - Recommended for Development)
- **File**: `cloudleakage.db`
- **Pros**: Zero configuration, built-in Python support, perfect for development
- **Cons**: Single-user, not suitable for high-concurrency production

### 2. PostgreSQL (Recommended for Production)
- **Connection**: Set `DATABASE_URL` environment variable
- **Example**: `postgresql://user:password@localhost:5432/cloudleakage`
- **Pros**: ACID compliance, excellent performance, JSON support, multi-user
- **Cons**: Requires separate installation and configuration

### 3. MySQL/MariaDB (Alternative for Production)
- **Connection**: Set `DATABASE_URL` environment variable  
- **Example**: `mysql://user:password@localhost:3306/cloudleakage`
- **Pros**: Fast, widely supported, good for web applications
- **Cons**: Requires separate installation

## 🔧 Setup Instructions

### SQLite Setup (Default)
```bash
# No additional setup required
# Database file will be created automatically as 'cloudleakage.db'
python3 app.py
```

### PostgreSQL Setup
```bash
# 1. Install PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib libpq-dev

# 2. Create database and user
sudo -u postgres psql
CREATE DATABASE cloudleakage;
CREATE USER cloudleakage_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE cloudleakage TO cloudleakage_user;
\q

# 3. Install Python dependencies
pip install psycopg2-binary

# 4. Set environment variable
export DATABASE_URL="postgresql://cloudleakage_user:secure_password@localhost:5432/cloudleakage"

# 5. Run application
python3 app.py
```

### MySQL Setup
```bash
# 1. Install MySQL
sudo apt-get update
sudo apt-get install mysql-server libmysqlclient-dev

# 2. Create database and user
sudo mysql
CREATE DATABASE cloudleakage;
CREATE USER 'cloudleakage_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON cloudleakage.* TO 'cloudleakage_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 3. Install Python dependencies
pip install mysqlclient

# 4. Set environment variable
export DATABASE_URL="mysql://cloudleakage_user:secure_password@localhost:3306/cloudleakage"

# 5. Run application
python3 app.py
```

## 🏗️ Database Schema

### Tables Created Automatically

#### 1. `cloud_accounts`
Stores cloud provider account integrations:
- `id` (TEXT PRIMARY KEY) - Unique account identifier
- `display_name` (TEXT) - User-friendly account name
- `provider` (TEXT) - Cloud provider (aws, azure, gcp)
- `access_type` (TEXT) - Authentication method (accesskey, iam, cloudformation)
- `encrypted_credentials` (TEXT) - Encrypted access keys/secrets
- `role_arn` (TEXT) - IAM role ARN for role-based access
- `account_info` (JSON) - Account metadata (account ID, region, etc.)
- `status` (TEXT) - Connection status (connected, disconnected, error)
- `billing_enabled` (BOOLEAN) - Whether billing data collection is enabled
- `created_at`, `updated_at`, `last_sync` (DATETIME) - Timestamps

#### 2. `cost_data`
Stores AWS cost and usage data:
- `id` (INTEGER PRIMARY KEY) - Auto-incrementing ID
- `account_id` (TEXT) - Foreign key to cloud_accounts
- `date` (DATETIME) - Cost data date
- `service_name` (TEXT) - AWS service name
- `cost_amount` (TEXT) - Cost amount (stored as string for precision)
- `currency` (TEXT) - Currency code (default: USD)
- `usage_amount`, `usage_unit` - Usage metrics
- `region`, `availability_zone`, `instance_type` - Resource details
- `raw_data` (JSON) - Complete AWS API response

#### 3. `sync_history`
Tracks synchronization operations:
- `id` (INTEGER PRIMARY KEY) - Auto-incrementing ID
- `account_id` (TEXT) - Foreign key to cloud_accounts
- `sync_type` (TEXT) - Type of sync (cost_data, resources, billing)
- `status` (TEXT) - Sync status (success, error, in_progress)
- `records_processed`, `records_added`, `records_updated` - Metrics
- `error_message`, `error_details` - Error information
- `started_at`, `completed_at`, `duration_seconds` - Timing

## 🔐 Security Features

### Credential Encryption
- All sensitive credentials encrypted using `cryptography.fernet.Fernet`
- Encryption key generated automatically or set via `ENCRYPTION_KEY` environment variable
- Keys stored securely with proper database permissions

### Environment Variables
```bash
# Required for production
export ENCRYPTION_KEY="your-32-byte-base64-encoded-key"
export DATABASE_URL="your-database-connection-string"
export SECRET_KEY="your-flask-secret-key"

# Optional
export DATABASE_PATH="custom-sqlite-path.db"  # For SQLite only
```

### Best Practices
1. **Production**: Always set `ENCRYPTION_KEY` environment variable
2. **Database**: Use PostgreSQL or MySQL for production deployments
3. **Backups**: Regular database backups for credential recovery
4. **Access**: Restrict database access to application user only
5. **SSL**: Use SSL/TLS for database connections in production

## 📊 Usage Examples

### Adding Cloud Accounts
```python
# Via API endpoint
POST /integration/api/accounts
{
    "displayName": "Production AWS",
    "provider": "aws",
    "accessType": "accesskey",
    "accessKeyId": "AKIA...",
    "secretAccessKey": "...",
    "region": "us-east-1"
}
```

### Retrieving Cost Data
```python
# Via API endpoint
GET /integration/api/accounts/{account_id}/costs?start_date=2024-01-01&end_date=2024-01-31
```

### Database Service Usage
```python
from simple_database import init_database, CloudAccountService, CostDataService

# Initialize
db = init_database('cloudleakage.db')
account_service = CloudAccountService(db, cipher_suite)
cost_service = CostDataService(db)

# Create account
account_id = account_service.create_account(account_data)

# Store cost data
cost_service.store_cost_data(account_id, cost_data_list)
```

## 🔧 Maintenance

### Database Backup
```bash
# SQLite
cp cloudleakage.db cloudleakage_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump cloudleakage > cloudleakage_backup_$(date +%Y%m%d).sql

# MySQL
mysqldump cloudleakage > cloudleakage_backup_$(date +%Y%m%d).sql
```

### Database Migration
The application automatically creates tables on first run. For schema updates:
1. Backup existing database
2. Update application code
3. Restart application (tables will be updated automatically)

### Performance Optimization
- **Indexing**: Add indexes on frequently queried columns
- **Cleanup**: Regular cleanup of old cost data and sync history
- **Connection Pooling**: Use connection pooling for high-traffic deployments

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```
   sqlite3.OperationalError: unable to open database file
   ```
   **Solution**: Check file permissions and disk space

2. **Encryption Key Error**
   ```
   cryptography.fernet.InvalidToken
   ```
   **Solution**: Ensure consistent `ENCRYPTION_KEY` environment variable

3. **Missing Dependencies**
   ```
   ModuleNotFoundError: No module named 'psycopg2'
   ```
   **Solution**: Install database-specific Python packages

### Debug Mode
```bash
# Enable detailed logging
export FLASK_ENV=development
export FLASK_DEBUG=1
python3 app.py
```

## 📈 Monitoring

### Database Health Checks
- Monitor database file size growth
- Check connection pool usage
- Track sync operation success rates
- Monitor credential encryption/decryption performance

### Metrics to Track
- Number of connected accounts
- Cost data volume per account
- Sync frequency and duration
- Error rates and types

This database integration provides a robust, secure, and scalable foundation for storing cloud account credentials and cost data in your CloudLeakage application.
