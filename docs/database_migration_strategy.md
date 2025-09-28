# CloudLeakage Database Migration & Scaling Strategy

## 🎯 Current State Analysis

### Current Implementation
- **Database**: SQLite with custom `DatabaseManager` class
- **Tables**: 4 core tables (cloud_accounts, cost_data, sync_history, ec2_instances)
- **Security**: Fernet encryption for credentials
- **Status**: Development-ready, NOT production-ready

### Current Schema Strengths
✅ Well-designed table structure
✅ Proper foreign key relationships
✅ Encrypted credential storage
✅ Comprehensive sync tracking
✅ JSON support for flexible data

## 🚀 Recommended Migration Path

### Phase 1: Immediate Production Readiness (1-2 days)

#### 1.1 Database Migration to PostgreSQL
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib libpq-dev

# Create production database
sudo -u postgres createdb cloudleakage_prod
sudo -u postgres createuser -P cloudleakage_user

# Grant permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cloudleakage_prod TO cloudleakage_user;"
```

#### 1.2 Update Database Manager
```python
# Add to app/services/database_manager.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

class ProductionDatabaseManager:
    def __init__(self):
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///cloudleakage.db')
        
        if database_url.startswith('postgresql'):
            # PostgreSQL with connection pooling
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        else:
            # SQLite fallback
            self.engine = create_engine(database_url)
```

#### 1.3 Data Migration Script
```python
# Create migration script: migrate_to_production.py
import sqlite3
import psycopg2
from app.services.simple_database import DatabaseManager

def migrate_sqlite_to_postgresql():
    # Export from SQLite
    sqlite_db = DatabaseManager('cloudleakage.db')
    
    # Import to PostgreSQL
    pg_conn = psycopg2.connect(os.environ['DATABASE_URL'])
    
    # Migrate each table with data preservation
    migrate_accounts(sqlite_db, pg_conn)
    migrate_cost_data(sqlite_db, pg_conn)
    migrate_sync_history(sqlite_db, pg_conn)
    migrate_ec2_instances(sqlite_db, pg_conn)
```

### Phase 2: Performance Optimization (3-5 days)

#### 2.1 Database Indexing Strategy
```sql
-- Critical indexes for performance
CREATE INDEX idx_cost_data_account_date ON cost_data(account_id, date);
CREATE INDEX idx_cost_data_service ON cost_data(service_name);
CREATE INDEX idx_ec2_instances_account ON ec2_instances(account_id);
CREATE INDEX idx_sync_history_account_type ON sync_history(account_id, sync_type);
CREATE INDEX idx_cloud_accounts_status ON cloud_accounts(status);

-- Composite indexes for common queries
CREATE INDEX idx_cost_data_composite ON cost_data(account_id, date, service_name);
CREATE INDEX idx_ec2_state_region ON ec2_instances(state, region);
```

#### 2.2 Query Optimization
```python
# Add to services for optimized queries
class OptimizedCostService:
    def get_monthly_costs(self, account_id, start_date, end_date):
        """Optimized monthly cost aggregation"""
        query = """
        SELECT 
            DATE_TRUNC('month', date::date) as month,
            service_name,
            SUM(cost_amount::numeric) as total_cost
        FROM cost_data 
        WHERE account_id = %s 
        AND date BETWEEN %s AND %s
        GROUP BY month, service_name
        ORDER BY month DESC, total_cost DESC
        """
        return self.execute_query(query, [account_id, start_date, end_date])
```

#### 2.3 Connection Pool Management
```python
# Enhanced connection management
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

class DatabaseManager:
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = self.engine.connect()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

### Phase 3: Advanced Scaling (1-2 weeks)

#### 3.1 Read Replicas Setup
```yaml
# docker-compose.yml for database cluster
version: '3.8'
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: cloudleakage
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: replica_pass
    
  postgres-replica:
    image: postgres:15
    environment:
      PGUSER: postgres
      POSTGRES_PASSWORD: replica_pass
    command: |
      bash -c "
      until pg_basebackup --pgdata=/var/lib/postgresql/data -R --slot=replication_slot --host=postgres-primary --port=5432
      do
      echo 'Waiting for primary to connect...'
      sleep 1s
      done
      echo 'Backup done, starting replica...'
      chmod 0700 /var/lib/postgresql/data
      postgres
      "
```

#### 3.2 Data Partitioning Strategy
```sql
-- Partition cost_data by date for better performance
CREATE TABLE cost_data_2024 PARTITION OF cost_data
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE cost_data_2025 PARTITION OF cost_data
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Auto-partition creation function
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE);
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS cost_data_%s PARTITION OF cost_data
                    FOR VALUES FROM (%L) TO (%L)',
                   to_char(start_date, 'YYYY_MM'),
                   start_date,
                   end_date);
END;
$$ LANGUAGE plpgsql;
```

#### 3.3 Caching Layer Integration
```python
# Redis caching for frequently accessed data
import redis
import json
from datetime import timedelta

class CachedDatabaseManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=6379,
            decode_responses=True
        )
        self.cache_ttl = 300  # 5 minutes
    
    def get_cached_cost_data(self, account_id, cache_key):
        """Get cost data with Redis caching"""
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fetch from database
        data = self.fetch_cost_data(account_id)
        
        # Cache result
        self.redis_client.setex(
            cache_key, 
            self.cache_ttl, 
            json.dumps(data, default=str)
        )
        return data
```

## 📊 Scaling Recommendations by Usage

### Small Scale (1-10 accounts, <1GB data)
- **Database**: PostgreSQL single instance
- **Caching**: Application-level caching (current implementation)
- **Backup**: Daily pg_dump
- **Monitoring**: Basic health checks

### Medium Scale (10-100 accounts, 1-50GB data)
- **Database**: PostgreSQL with read replica
- **Caching**: Redis cluster
- **Backup**: Continuous WAL archiving
- **Monitoring**: Prometheus + Grafana
- **Partitioning**: Monthly partitions for cost_data

### Large Scale (100+ accounts, 50GB+ data)
- **Database**: PostgreSQL cluster with multiple replicas
- **Caching**: Redis Cluster with sharding
- **Backup**: Point-in-time recovery
- **Monitoring**: Full observability stack
- **Partitioning**: Weekly partitions + automated cleanup
- **CDN**: CloudFront for static assets

## 🔧 Implementation Priority

### Week 1: Critical Production Setup
1. ✅ PostgreSQL migration
2. ✅ Connection pooling
3. ✅ Basic indexing
4. ✅ Backup strategy

### Week 2: Performance Optimization
1. ✅ Advanced indexing
2. ✅ Query optimization
3. ✅ Redis caching
4. ✅ Monitoring setup

### Week 3: Scaling Features
1. ✅ Read replicas
2. ✅ Data partitioning
3. ✅ Automated cleanup
4. ✅ Load testing

## 🚨 Migration Risks & Mitigation

### Risk 1: Data Loss During Migration
**Mitigation**: 
- Complete backup before migration
- Test migration on copy first
- Rollback plan with original SQLite

### Risk 2: Performance Degradation
**Mitigation**:
- Gradual migration with A/B testing
- Performance monitoring during migration
- Rollback triggers if performance drops >20%

### Risk 3: Credential Encryption Issues
**Mitigation**:
- Verify encryption key consistency
- Test credential decryption before migration
- Backup encrypted credentials separately

## 📈 Expected Performance Improvements

| Metric | Current (SQLite) | PostgreSQL | PostgreSQL + Optimization |
|--------|------------------|------------|---------------------------|
| Concurrent Users | 1 | 50+ | 200+ |
| Query Response | 100-500ms | 10-50ms | 5-20ms |
| Data Volume | <1GB | 100GB+ | 1TB+ |
| Backup Time | Minutes | Seconds | Continuous |
| High Availability | None | 99.9% | 99.99% |

This migration strategy provides a clear path from development to enterprise-scale production deployment.
