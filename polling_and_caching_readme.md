# CloudLeakage Polling & Caching Architecture

## 📋 Overview

CloudLeakage implements a sophisticated 3-tier data management system that combines real-time AWS API access, intelligent caching, and persistent database storage to provide optimal performance and reliability.

## 🏗️ Architecture Layers

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │───▶│   Memory Cache  │───▶│    Database     │───▶│    AWS API      │
│  Auto-refresh   │    │   (5min TTL)    │    │  (Persistent)   │    │  (Real-time)    │
│   (5 minutes)   │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Layer 1: Frontend Auto-Refresh
- **Interval**: 5 minutes
- **Purpose**: Keep dashboard data current
- **Implementation**: JavaScript `setInterval()`

### Layer 2: In-Memory Cache
- **TTL**: 5 minutes (300 seconds)
- **Purpose**: Reduce AWS API calls and improve response times
- **Scope**: Per account, per region, per service

### Layer 3: Database Storage
- **Purpose**: Historical tracking, offline access, analytics
- **Database**: SQLite with encrypted credentials
- **Tables**: EC2 instances, snapshots, AMIs, cost data

### Layer 4: AWS API
- **Purpose**: Source of truth for real-time data
- **Optimization**: Parallel region processing, retry logic
- **Error Handling**: Graceful fallback to cached/stored data

## 🔄 Polling Mechanisms

### 1. Automatic Frontend Polling

**Dashboard Cost Chart Auto-Refresh**
```javascript
// Auto-refresh data every 5 minutes
setInterval(function() {
    fetch('/api/cost-data')
        .then(response => response.json())
        .then(data => {
            costChart.data.labels = data.labels;
            costChart.data.datasets[0].data = data.data;
            costChart.update();
        });
}, 300000); // 5 minutes = 300,000ms
```

**Location**: `templates/cloudspend-dashboard.html`

### 2. Cache-First Data Retrieval

**EC2 Service Caching**
```python
def get_ec2_instances(self, account_id: str, region: str = None, use_cache: bool = True):
    cache_key = f"ec2_instances_{account_id}_{region or 'all'}"
    
    # Check cache first
    if use_cache and cache_key in self.cache:
        cached_data = self.cache[cache_key]
        if time.time() - cached_data['timestamp'] < self.cache_ttl:  # 5 minutes
            logger.info(f"Returning cached EC2 data for account {account_id}")
            return cached_data['instances']
    
    # Fetch fresh data if cache expired
    instances = self._fetch_ec2_instances_optimized(account_id, region)
    
    # Update cache
    self.cache[cache_key] = {
        'instances': instances,
        'timestamp': time.time()
    }
    
    return instances
```

**Location**: `ec2_service.py`

**Snapshot Service Caching**
```python
def get_snapshots(self, account_id: str, region: str = None, use_cache: bool = True):
    cache_key = f"snapshots_{account_id}_{region or 'all'}"
    
    # Check cache first
    if use_cache and cache_key in self.cache:
        cached_data = self.cache[cache_key]
        if time.time() - cached_data['timestamp'] < self.cache_ttl:  # 5 minutes
            return cached_data['snapshots']
    
    # Fetch and cache fresh data
    snapshots = self._fetch_snapshots_optimized(account_id, region)
    self.cache[cache_key] = {'snapshots': snapshots, 'timestamp': time.time()}
    
    return snapshots
```

**Location**: `snapshot_service.py`

**AMI Service Caching**
```python
def get_amis(self, account_id: str, region: str = None, use_cache: bool = True):
    cache_key = f"amis_{account_id}_{region or 'all'}"
    
    # Check cache first
    if use_cache and cache_key in self.cache:
        cached_data = self.cache[cache_key]
        if time.time() - cached_data['timestamp'] < self.cache_ttl:  # 5 minutes
            return cached_data['amis']
    
    # Fetch and cache fresh data
    amis = self._fetch_amis_optimized(account_id, region)
    self.cache[cache_key] = {'amis': amis, 'timestamp': time.time()}
    
    return amis
```

**Location**: `snapshot_service.py`

### 3. Manual Sync Endpoints

**Force EC2 Data Refresh**
```python
@app.route('/ec2/api/accounts/<account_id>/sync', methods=['POST'])
def sync_ec2_data(account_id):
    ec2_service = app.config['EC2_SERVICE']
    
    # Fetch fresh data (bypass cache)
    instances = ec2_service.get_ec2_instances(account_id, use_cache=False)
    
    # Store in database
    ec2_service.store_ec2_data(account_id, instances)
    
    return jsonify({
        'success': True,
        'message': f'Synced {len(instances)} EC2 instances'
    })
```

**Force Snapshot Data Refresh**
```python
@app.route('/snapshots/api/accounts/<account_id>/sync', methods=['POST'])
def sync_snapshot_data(account_id):
    snapshot_service = app.config['SNAPSHOT_SERVICE']
    
    # Fetch fresh data (bypass cache)
    snapshots = snapshot_service.get_snapshots(account_id, use_cache=False)
    
    # Store in database
    snapshot_service.store_snapshot_data(account_id, snapshots)
    
    return jsonify({
        'success': True,
        'snapshots_synced': len(snapshots)
    })
```

**Location**: `app.py`

## 💾 Database Storage Implementation

### EC2 Data Storage
```python
def store_ec2_data(self, account_id: str, instances: List[Dict]):
    """Store EC2 instance data in database for historical tracking"""
    conn = self.db.get_connection()
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ec2_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            instance_id TEXT NOT NULL,
            region TEXT NOT NULL,
            state TEXT NOT NULL,
            instance_type TEXT NOT NULL,
            launch_time TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_id, instance_id, region)
        )
    ''')
    
    # Insert or update instance data
    for instance in instances:
        cursor.execute('''
            INSERT OR REPLACE INTO ec2_instances 
            (account_id, instance_id, region, state, instance_type, launch_time, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_id,
            instance['instanceId'],
            instance['region'],
            instance['state'],
            instance['instanceType'],
            instance.get('launchTime'),
            json.dumps(instance.get('tags', {}))
        ))
    
    conn.commit()
```

### Snapshot Data Storage
```python
def store_snapshot_data(self, account_id: str, snapshots: List[Dict]):
    """Store snapshot data in database for historical tracking"""
    conn = self.db.get_connection()
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            volume_id TEXT,
            region TEXT NOT NULL,
            state TEXT NOT NULL,
            start_time TEXT NOT NULL,
            volume_size INTEGER,
            encrypted BOOLEAN,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_id, snapshot_id, region)
        )
    ''')
    
    # Insert snapshot data
    for snapshot in snapshots:
        cursor.execute('''
            INSERT OR REPLACE INTO snapshots 
            (account_id, snapshot_id, volume_id, region, state, start_time, volume_size, encrypted, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_id,
            snapshot['snapshotId'],
            snapshot.get('volumeId'),
            snapshot['region'],
            snapshot['state'],
            snapshot['startTime'],
            snapshot.get('volumeSize', 0),
            snapshot.get('encrypted', False),
            json.dumps(snapshot.get('tags', {}))
        ))
    
    conn.commit()
```

## ⚙️ Configuration

### Cache Settings
```python
class EC2Service:
    def __init__(self, db_manager, cipher_suite):
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes

class SnapshotService:
    def __init__(self, db_manager, cipher_suite):
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
```

### Frontend Polling Settings
```javascript
// Dashboard auto-refresh interval
const REFRESH_INTERVAL = 300000; // 5 minutes in milliseconds

setInterval(function() {
    // Refresh logic
}, REFRESH_INTERVAL);
```

## 🚀 Performance Optimizations

### 1. Parallel Region Processing
```python
# Use ThreadPoolExecutor for parallel region processing
with ThreadPoolExecutor(max_workers=5) as executor:
    future_to_region = {
        executor.submit(self._fetch_region_instances, session, region_name): region_name 
        for region_name in regions
    }
    
    for future in as_completed(future_to_region):
        region_name = future_to_region[future]
        try:
            instances = future.result()
            all_instances.extend(instances)
        except Exception as e:
            logger.error(f"Error fetching instances from {region_name}: {e}")
```

### 2. Exponential Backoff Retry
```python
@backoff.on_exception(backoff.expo, (ClientError, BotoCoreError), max_tries=3)
def _fetch_region_instances(self, session, region_name: str):
    # AWS API call with automatic retry on failure
```

### 3. Cache Management
```python
def clear_cache(self, account_id: str = None):
    """Clear cache for specific account or all accounts"""
    if account_id:
        keys_to_remove = [k for k in self.cache.keys() if account_id in k]
        for key in keys_to_remove:
            del self.cache[key]
    else:
        self.cache.clear()
```

## 📊 Data Flow Examples

### User Requests EC2 Data
1. **Frontend** → API request to `/ec2/api/accounts/{id}/instances`
2. **Cache Check** → If data exists and < 5 minutes old, return cached data
3. **AWS API** → If cache miss/expired, fetch from AWS across all regions in parallel
4. **Cache Update** → Store fresh data in memory cache with timestamp
5. **Database Store** → Optionally store in database for historical tracking
6. **Response** → Return data to frontend

### User Clicks Sync Button
1. **Frontend** → POST to `/ec2/api/accounts/{id}/sync`
2. **Force Refresh** → Bypass cache, fetch directly from AWS
3. **Database Store** → Store fresh data in database
4. **Cache Update** → Update memory cache
5. **Response** → Confirm sync completion

### Dashboard Auto-Refresh
1. **Timer** → JavaScript setInterval triggers every 5 minutes
2. **API Call** → Fetch `/api/cost-data`
3. **Cache/DB** → Return cached or stored data
4. **UI Update** → Update charts and metrics without page reload

## 🔧 Maintenance & Monitoring

### Cache Statistics
- Monitor cache hit/miss ratios
- Track API call frequency
- Monitor response times

### Database Maintenance
- Regular cleanup of old historical data
- Index optimization for query performance
- Backup and recovery procedures

### Error Handling
- Graceful degradation when AWS API is unavailable
- Fallback to cached/stored data
- Comprehensive logging for troubleshooting

## 🛠️ Implementation Checklist

- ✅ **In-Memory Caching**: 5-minute TTL implemented across all services
- ✅ **Database Storage**: Historical data storage for EC2, snapshots, AMIs
- ✅ **Frontend Polling**: Auto-refresh every 5 minutes
- ✅ **Manual Sync**: Force refresh endpoints for all services
- ✅ **Parallel Processing**: Multi-region AWS calls optimized
- ✅ **Error Handling**: Retry logic and graceful fallbacks
- ✅ **Cache Management**: Clear cache functionality
- ✅ **Performance Monitoring**: Logging and metrics

## 📝 Future Enhancements

1. **Background Jobs**: Scheduled data synchronization
2. **Cache Warming**: Pre-populate cache for frequently accessed data
3. **Real-time Updates**: WebSocket connections for live data
4. **Advanced Analytics**: Trend analysis and predictive insights
5. **Multi-level Caching**: Redis or Memcached for distributed caching

---

**Last Updated**: 2025-09-15  
**Version**: 1.0  
**Author**: CloudLeakage Development Team
