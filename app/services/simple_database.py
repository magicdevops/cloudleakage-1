#!/usr/bin/env python3
"""
Simple SQLite Database for CloudLeakage - No external dependencies
"""

import sqlite3
import json
import uuid
import logging
import os
from datetime import datetime
from cryptography.fernet import Fernet
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager supporting SQLite and PostgreSQL"""
    
    def __init__(self, db_path='cloudleakage.db'):
        # Check for PostgreSQL connection string in environment
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url and database_url.startswith('postgresql://') and POSTGRES_AVAILABLE:
            self.db_type = 'postgresql'
            self.database_url = database_url
            logger.info("Using PostgreSQL database")
        else:
            self.db_type = 'sqlite'
            self.db_path = db_path
            logger.info(f"Using SQLite database: {db_path}")
        
        self.init_database()
    
    def get_connection(self):
        """Get database connection based on type"""
        if self.db_type == 'postgresql':
            return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
        else:
            return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Create cloud_accounts table
            if self.db_type == 'postgresql':
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cloud_accounts (
                        id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        access_type TEXT NOT NULL,
                        encrypted_credentials TEXT,
                        role_arn TEXT,
                        stack_name TEXT,
                        cf_role_arn TEXT,
                        account_info TEXT,
                        status TEXT DEFAULT 'connected',
                        billing_enabled INTEGER DEFAULT 1,
                        account_type TEXT DEFAULT 'organization',
                        export_name TEXT,
                        start_date TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        last_sync TIMESTAMP
                    )
                ''')
            else:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS cloud_accounts (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    access_type TEXT NOT NULL,
                    encrypted_credentials TEXT,
                    role_arn TEXT,
                    stack_name TEXT,
                    cf_role_arn TEXT,
                    account_info TEXT,
                    status TEXT DEFAULT 'connected',
                    billing_enabled INTEGER DEFAULT 1,
                    account_type TEXT DEFAULT 'organization',
                    export_name TEXT,
                    start_date TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    last_sync TEXT
                )
            ''')
            
            # Create cost_data table (only for SQLite)
            if self.db_type == 'sqlite':
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cost_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    granularity TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    cost_amount TEXT NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    usage_amount TEXT,
                    usage_unit TEXT,
                    region TEXT,
                    availability_zone TEXT,
                    instance_type TEXT,
                    raw_data TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (account_id) REFERENCES cloud_accounts (id)
                )
            ''')
            
            # Create sync_history table (only for SQLite)
            if self.db_type == 'sqlite':
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    sync_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    records_processed INTEGER DEFAULT 0,
                    records_added INTEGER DEFAULT 0,
                    records_updated INTEGER DEFAULT 0,
                    error_message TEXT,
                    error_details TEXT,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    duration_seconds REAL,
                    FOREIGN KEY (account_id) REFERENCES cloud_accounts (id)
                )
            ''')
            
            # Create ec2_instances table (only for SQLite)
            if self.db_type == 'sqlite':
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ec2_instances (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    instance_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    region TEXT NOT NULL,
                    availability_zone TEXT,
                    launch_time DATETIME,
                    platform TEXT,
                    vpc_id TEXT,
                    private_ip TEXT,
                    public_ip TEXT,
                    tags TEXT,
                    last_updated DATETIME NOT NULL,
                    raw_data TEXT,
                    UNIQUE(account_id, instance_id),
                    FOREIGN KEY (account_id) REFERENCES cloud_accounts (id)
                )
            ''')
            
            # Create additional PostgreSQL tables
            if self.db_type == 'postgresql':
                # Cost data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cost_data (
                        id SERIAL PRIMARY KEY,
                        account_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        granularity TEXT NOT NULL,
                        service_name TEXT NOT NULL,
                        cost_amount TEXT NOT NULL,
                        currency TEXT DEFAULT 'USD',
                        usage_amount TEXT,
                        usage_unit TEXT,
                        region TEXT,
                        availability_zone TEXT,
                        instance_type TEXT,
                        raw_data TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES cloud_accounts (id)
                    )
                ''')
                
                # Sync history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_history (
                        id SERIAL PRIMARY KEY,
                        account_id TEXT NOT NULL,
                        sync_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        records_processed INTEGER DEFAULT 0,
                        records_added INTEGER DEFAULT 0,
                        records_updated INTEGER DEFAULT 0,
                        error_message TEXT,
                        error_details TEXT,
                        started_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        duration_seconds REAL,
                        FOREIGN KEY (account_id) REFERENCES cloud_accounts (id)
                    )
                ''')
                
                # EC2 instances table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ec2_instances (
                        id SERIAL PRIMARY KEY,
                        account_id TEXT NOT NULL,
                        instance_id TEXT NOT NULL,
                        instance_type TEXT NOT NULL,
                        state TEXT NOT NULL,
                        region TEXT NOT NULL,
                        availability_zone TEXT,
                        launch_time TIMESTAMP,
                        platform TEXT,
                        vpc_id TEXT,
                        private_ip TEXT,
                        public_ip TEXT,
                        tags TEXT,
                        last_updated TIMESTAMP NOT NULL,
                        raw_data TEXT,
                        UNIQUE(account_id, instance_id),
                        FOREIGN KEY (account_id) REFERENCES cloud_accounts (id)
                    )
                ''')
                
                # Create indexes for PostgreSQL
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_cost_data_account_date ON cost_data(account_id, date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ec2_instances_account ON ec2_instances(account_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_history_account ON sync_history(account_id)')
            
            conn.commit()
            logger.info(f"Database tables created successfully ({self.db_type})")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if self.db_type == 'postgresql':
                conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Convert SQLite placeholders (?) to PostgreSQL placeholders (%s)
            if self.db_type == 'postgresql' and '?' in query:
                query = query.replace('?', '%s')
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            if self.db_type == 'postgresql':
                conn.rollback()
            logger.error(f"Database query error: {str(e)}")
            raise
        finally:
            conn.close()
    
    def create_account(self, account_data):
        """Create a new cloud account"""
        # Initialize cipher suite if not available
        if not hasattr(self, 'cipher_suite'):
            from cryptography.fernet import Fernet
            import os
            encryption_key = os.environ.get('ENCRYPTION_KEY', 'oz2fA05GT7jHw-kReDcvXCHc9weUCOM2sBe7bIOQqps=')
            self.cipher_suite = Fernet(encryption_key.encode())
        
        account_service = CloudAccountService(self, self.cipher_suite)
        return account_service.create_account(account_data)
    
    def get_all_accounts(self):
        """Get all cloud accounts"""
        # Initialize cipher suite if not available
        if not hasattr(self, 'cipher_suite'):
            from cryptography.fernet import Fernet
            import os
            encryption_key = os.environ.get('ENCRYPTION_KEY', 'oz2fA05GT7jHw-kReDcvXCHc9weUCOM2sBe7bIOQqps=')
            self.cipher_suite = Fernet(encryption_key.encode())
        
        account_service = CloudAccountService(self, self.cipher_suite)
        return account_service.get_all_accounts()

class CloudAccountService:
    """Service for managing cloud accounts"""
    
    def __init__(self, db, cipher_suite):
        self.db = db
        self.cipher_suite = cipher_suite
    
    def create_account(self, account_data):
        """Create a new cloud account"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # Encrypt credentials if provided
            encrypted_credentials = None
            if account_data.get('credentials'):
                credentials_json = json.dumps(account_data['credentials'])
                encrypted_credentials = self.cipher_suite.encrypt(credentials_json.encode()).decode()
            
            now = datetime.utcnow().isoformat()
            
            # Use appropriate placeholder based on database type
            placeholder = '%s' if self.db.db_type == 'postgresql' else '?'
            query = f'''
                INSERT INTO cloud_accounts (
                    id, display_name, provider, access_type, encrypted_credentials,
                    role_arn, stack_name, cf_role_arn, account_info, status,
                    billing_enabled, account_type, export_name, start_date,
                    created_at, updated_at
                ) VALUES ({", ".join([placeholder] * 16)})
            '''
            
            cursor.execute(query, (
                account_data['id'],
                account_data['displayName'],
                account_data['provider'],
                account_data['accessType'],
                encrypted_credentials,
                account_data.get('roleArn'),
                account_data.get('stackName'),
                account_data.get('cfRoleArn'),
                json.dumps(account_data.get('accountInfo', {})),
                account_data.get('status', 'connected'),
                1 if account_data.get('billing') == 'yes' else 0,
                account_data.get('accountType', 'organization'),
                account_data.get('exportName'),
                account_data.get('startDate'),
                now,
                now
            ))
            
            conn.commit()
            logger.info(f"Created cloud account: {account_data['displayName']}")
            
            return account_data['id']
            
        except Exception as e:
            if self.db.db_type == 'postgresql':
                conn.rollback()
            logger.error(f"Error creating cloud account: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _safe_json_loads(self, json_str):
        """Safely load JSON string, return empty dict if invalid"""
        if not json_str or not json_str.strip():
            return {}
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_all_accounts(self):
        """Get all cloud accounts"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cloud_accounts ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            accounts = []
            
            for row in rows:
                # PostgreSQL returns RealDictRow objects, handle both dict and RealDictRow
                if hasattr(row, '_asdict'):
                    account = row._asdict()
                elif hasattr(row, 'keys'):
                    account = dict(row)
                else:
                    account = dict(zip(columns, row))
                
                # Convert to expected format
                account_dict = {
                    'id': account['id'],
                    'displayName': account['display_name'],
                    'provider': account['provider'],
                    'accessType': account['access_type'],
                    'roleArn': account['role_arn'],
                    'accountInfo': self._safe_json_loads(account['account_info']),
                    'status': account['status'],
                    'createdAt': str(account['created_at']),
                    'lastSync': account.get('last_sync'),
                    'billingEnabled': bool(account['billing_enabled']),
                    'accountType': account['account_type'],
                    'exportName': account['export_name'],
                    'startDate': account['start_date']
                }
                accounts.append(account_dict)
            
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting cloud accounts: {str(e)}")
            raise
        finally:
            conn.close()
    
    def get_account_by_id(self, account_id):
        """Get account by ID"""
        try:
            result = self.db.execute_query('SELECT * FROM cloud_accounts WHERE id = ?', (account_id,))
            
            if not result:
                return None
            
            # Get column names for mapping
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM cloud_accounts LIMIT 0')  # Get column info without data
                columns = [desc[0] for desc in cursor.description]
            finally:
                conn.close()
            
            account = dict(zip(columns, result[0]))
            
            # Create a simple object with the needed attributes
            class AccountObj:
                def __init__(self, data):
                    self.id = data['id']
                    self.access_type = data['access_type']
                    self.provider = data['provider']
                    self.display_name = data['display_name']
                    self.encrypted_credentials = data['encrypted_credentials']
                    self.role_arn = data['role_arn']
            
            return AccountObj(account)
            
        except Exception as e:
            logger.error(f"Error getting account {account_id}: {str(e)}")
            raise
    
    def update_last_sync(self, account_id):
        """Update last sync timestamp"""
        try:
            now = datetime.utcnow().isoformat()
            
            self.db.execute_query('''
                UPDATE cloud_accounts 
                SET last_sync = ?, updated_at = ? 
                WHERE id = ?
            ''', (now, now, account_id))
            
            logger.info(f"Updated last sync for account: {account_id}")
            
        except Exception as e:
            logger.error(f"Error updating last sync: {str(e)}")
            raise
    
    def delete_account(self, account_id):
        """Delete account"""
        try:
            rowcount = self.db.execute_query('DELETE FROM cloud_accounts WHERE id = ?', (account_id,))
            
            if rowcount > 0:
                logger.info(f"Deleted cloud account: {account_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting account: {str(e)}")
            raise
    
    def get_decrypted_credentials(self, account_id):
        """Get decrypted credentials"""
        try:
            result = self.db.execute_query('SELECT encrypted_credentials FROM cloud_accounts WHERE id = ?', (account_id,))
            
            if not result or not result[0][0]:
                return None
            
            decrypted_data = self.cipher_suite.decrypt(result[0][0].encode())
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.error(f"Error decrypting credentials: {str(e)}")
            raise

class CostDataService:
    """Service for managing cost data"""
    
    def __init__(self, db):
        self.db = db
    
    def store_cost_data(self, account_id, cost_data_list):
        """Store cost data"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            for cost_item in cost_data_list:
                cursor.execute('''
                    INSERT INTO cost_data (
                        account_id, date, granularity, service_name, cost_amount,
                        currency, usage_amount, usage_unit, region, availability_zone,
                        instance_type, raw_data, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account_id,
                    cost_item['date'],
                    cost_item.get('granularity', 'DAILY'),
                    cost_item['service'],
                    str(cost_item['cost']),
                    cost_item.get('currency', 'USD'),
                    str(cost_item.get('usage', 0)) if cost_item.get('usage') else None,
                    cost_item.get('usage_unit'),
                    cost_item.get('region'),
                    cost_item.get('az'),
                    cost_item.get('instance_type'),
                    json.dumps(cost_item.get('raw_data')) if cost_item.get('raw_data') else None,
                    now,
                    now
                ))
            
            conn.commit()
            logger.info(f"Stored {len(cost_data_list)} cost records")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error storing cost data: {str(e)}")
            raise
        finally:
            conn.close()
    
    def get_cost_data(self, account_id, start_date=None, end_date=None, service_name=None):
        """Get cost data"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM cost_data WHERE account_id = ?'
            params = [account_id]
            
            if start_date:
                query += ' AND date >= ?'
                params.append(start_date)
            if end_date:
                query += ' AND date <= ?'
                params.append(end_date)
            if service_name:
                query += ' AND service_name = ?'
                params.append(service_name)
            
            query += ' ORDER BY date DESC'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            result = []
            
            for row in rows:
                record = dict(zip(columns, row))
                result.append({
                    'id': record['id'],
                    'date': record['date'],
                    'service': record['service_name'],
                    'cost': float(record['cost_amount']),
                    'currency': record['currency'],
                    'usage': float(record['usage_amount']) if record['usage_amount'] else None,
                    'usage_unit': record['usage_unit'],
                    'region': record['region'],
                    'raw_data': json.loads(record['raw_data']) if record['raw_data'] else None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting cost data: {str(e)}")
            raise
        finally:
            conn.close()

def init_database(db_path='cloudleakage.db'):
    """Initialize database and return services"""
    return SimpleDatabase(db_path)
