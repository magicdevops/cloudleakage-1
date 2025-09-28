"""
Snapshot Service for CloudLeakage
Handles EBS snapshot data retrieval and analysis using stored account credentials
"""

import boto3
import json
import logging
import time
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, BotoCoreError
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import backoff

logger = logging.getLogger(__name__)

class SnapshotService:
    def __init__(self, db_manager, cipher_suite):
        self.db = db_manager
        self.cipher_suite = cipher_suite
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
    
    def _get_boto3_session(self, account_id: str):
        """Create boto3 session using stored encrypted credentials"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT encrypted_credentials, provider, access_type, role_arn, account_info
            FROM cloud_accounts 
            WHERE id = ? AND status = 'connected'
        ''', (account_id,))
        
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Account {account_id} not found or not connected")
        
        encrypted_creds, provider, access_type, role_arn, account_info = result
        
        if provider != 'aws':
            raise ValueError(f"Account {account_id} is not an AWS account")
        
        # Decrypt credentials
        if encrypted_creds:
            try:
                decrypted_data = self.cipher_suite.decrypt(encrypted_creds.encode())
                credentials = json.loads(decrypted_data.decode())
                
                if access_type == 'accesskey':
                    # Handle both possible key formats
                    access_key = credentials.get('access_key_id') or credentials.get('accessKeyId')
                    secret_key = credentials.get('secret_access_key') or credentials.get('secretAccessKey')
                    
                    if not access_key or not secret_key:
                        logger.error(f"Missing credentials in decrypted data: {list(credentials.keys())}")
                        raise ValueError(f"Invalid credential format for account {account_id}")
                    
                    return boto3.Session(
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=credentials.get('region', 'us-east-1')
                    )
            except Exception as e:
                logger.error(f"Failed to decrypt credentials for account {account_id}: {e}")
                raise ValueError(f"Failed to decrypt credentials: {str(e)}")
                
        elif access_type == 'iam' and role_arn:
            # For IAM role, assume the role
            sts_client = boto3.client('sts')
            assumed_role = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName='cloudleakage-snapshot-session'
            )
            return boto3.Session(
                aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                aws_session_token=assumed_role['Credentials']['SessionToken'],
                region_name=json.loads(account_info).get('region', 'us-east-1')
            )
        
        raise ValueError(f"Unable to create session for account {account_id}")
    
    def get_snapshots(self, account_id: str, region: str = None, use_cache: bool = True) -> List[Dict]:
        """Fetch EBS snapshots with caching and optimization"""
        cache_key = f"snapshots_{account_id}_{region or 'all'}"
        
        # Check cache first
        if use_cache and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                logger.info(f"Returning cached snapshot data for account {account_id}")
                return cached_data['snapshots']
        
        # Fetch fresh data
        snapshots = self._fetch_snapshots_optimized(account_id, region)
        
        # Cache the results
        self.cache[cache_key] = {
            'snapshots': snapshots,
            'timestamp': time.time()
        }
        
        return snapshots
    
    def _fetch_snapshots_optimized(self, account_id: str, region: str = None) -> List[Dict]:
        """Fetch snapshots from AWS with parallel region processing"""
        session = self._get_boto3_session(account_id)
        
        # Define regions to check
        if region:
            regions = [region]
        else:
            # Get available regions
            ec2_client = session.client('ec2', region_name='us-east-1')
            try:
                regions_response = ec2_client.describe_regions()
                regions = [r['RegionName'] for r in regions_response['Regions']]
            except Exception as e:
                logger.warning(f"Could not get regions list: {e}")
                regions = ['us-east-1', 'us-west-2', 'eu-west-1']  # Fallback regions
        
        all_snapshots = []
        
        # Use ThreadPoolExecutor for parallel region processing
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_region = {
                executor.submit(self._fetch_region_snapshots, session, region_name): region_name 
                for region_name in regions
            }
            
            for future in as_completed(future_to_region):
                region_name = future_to_region[future]
                try:
                    snapshots = future.result()
                    all_snapshots.extend(snapshots)
                    logger.info(f"Fetched {len(snapshots)} snapshots from {region_name}")
                except Exception as e:
                    logger.error(f"Error fetching snapshots from {region_name}: {e}")
        
        return all_snapshots
    
    @backoff.on_exception(backoff.expo, (ClientError, BotoCoreError), max_tries=3)
    def _fetch_region_snapshots(self, session, region_name: str) -> List[Dict]:
        """Fetch snapshots from a specific region with retry logic"""
        try:
            ec2_client = session.client('ec2', region_name=region_name)
            
            # Get snapshots owned by the account
            response = ec2_client.describe_snapshots(OwnerIds=['self'])
            
            snapshots = []
            for snapshot in response['Snapshots']:
                snapshot_data = self._format_snapshot_data(snapshot, region_name)
                snapshots.append(snapshot_data)
            
            return snapshots
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                logger.warning(f"No permission to describe snapshots in {region_name}")
                return []
            else:
                logger.error(f"AWS error in {region_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error in {region_name}: {e}")
            raise
    
    def _format_snapshot_data(self, snapshot: Dict, region_name: str) -> Dict:
        """Format snapshot data for consistent API response"""
        snapshot_data = {
            'snapshotId': snapshot['SnapshotId'],
            'description': snapshot.get('Description', ''),
            'startTime': snapshot['StartTime'].isoformat(),
            'state': snapshot['State'],
            'progress': snapshot.get('Progress', ''),
            'volumeId': snapshot.get('VolumeId', ''),
            'volumeSize': snapshot.get('VolumeSize', 0),
            'encrypted': snapshot.get('Encrypted', False),
            'ownerId': snapshot['OwnerId'],
            'region': region_name,
            'tags': {tag['Key']: tag['Value'] for tag in snapshot.get('Tags', [])}
        }
        
        return snapshot_data
    
    def get_snapshot_analysis(self, snapshots: List[Dict]) -> Dict:
        """Analyze snapshots for dashboard metrics"""
        now = datetime.now()
        
        total_snapshots = len(snapshots)
        snapshots_by_volume = {}
        volumes_with_snapshots = set()
        snapshots_30_days = 0
        snapshots_60_days = 0
        snapshots_90_days = 0
        
        for snapshot in snapshots:
            volume_id = snapshot.get('volumeId', 'Unknown')
            
            # Count snapshots by volume
            if volume_id not in snapshots_by_volume:
                snapshots_by_volume[volume_id] = 0
            snapshots_by_volume[volume_id] += 1
            
            # Track volumes with snapshots
            if volume_id != 'Unknown':
                volumes_with_snapshots.add(volume_id)
            
            # Calculate age
            start_time = datetime.fromisoformat(snapshot['startTime'].replace('Z', '+00:00'))
            days_old = (now - start_time.replace(tzinfo=None)).days
            
            if days_old >= 90:
                snapshots_90_days += 1
            elif days_old >= 60:
                snapshots_60_days += 1
            elif days_old >= 30:
                snapshots_30_days += 1
        
        # Count big volume snapshots (>= 100 GB)
        big_volume_snapshots = 0
        for snapshot in snapshots:
            volume_size = snapshot.get('volumeSize', 0)
            if volume_size >= 100:  # 100 GB threshold
                big_volume_snapshots += 1

        return {
            'total_snapshots': total_snapshots,
            'snapshots_by_volume': snapshots_by_volume,
            'volumes_with_snapshots_count': len(volumes_with_snapshots),
            'snapshots_30_days': snapshots_30_days,
            'snapshots_60_days': snapshots_60_days,
            'snapshots_90_days': snapshots_90_days,
            'big_volume_snapshots': big_volume_snapshots
        }
    
    def get_big_volume_snapshots(self, account_id: str, region: str = None, size_threshold: int = 100) -> List[Dict]:
        """Get snapshots with large volume sizes for export"""
        snapshots = self.get_snapshots(account_id, region)
        big_volume_snapshots = []
        
        for snapshot in snapshots:
            volume_size = snapshot.get('volumeSize', 0)
            if volume_size >= size_threshold:
                # Calculate estimated storage cost (approximate $0.05 per GB per month)
                estimated_cost = volume_size * 0.05
                
                snapshot_info = {
                    'snapshotId': snapshot.get('snapshotId', 'Unknown'),
                    'volumeId': snapshot.get('volumeId', 'Unknown'),
                    'volumeSize': volume_size,
                    'description': snapshot.get('description', ''),
                    'startTime': snapshot.get('startTime', ''),
                    'state': snapshot.get('state', 'Unknown'),
                    'progress': snapshot.get('progress', ''),
                    'ownerId': snapshot.get('ownerId', 'Unknown'),
                    'encrypted': snapshot.get('encrypted', False),
                    'estimatedMonthlyCost': round(estimated_cost, 2),
                    'region': snapshot.get('region', region or 'Unknown')
                }
                big_volume_snapshots.append(snapshot_info)
        
        # Sort by volume size (largest first)
        big_volume_snapshots.sort(key=lambda x: x['volumeSize'], reverse=True)
        return big_volume_snapshots
    
    def get_volumes_without_snapshots(self, account_id: str, region: str = None) -> List[Dict]:
        """Get EBS volumes that don't have any snapshots"""
        session = self._get_boto3_session(account_id)
        
        # Get all volumes
        if region:
            regions = [region]
        else:
            ec2_client = session.client('ec2', region_name='us-east-1')
            try:
                regions_response = ec2_client.describe_regions()
                regions = [r['RegionName'] for r in regions_response['Regions']]
            except Exception:
                regions = ['us-east-1', 'us-west-2', 'eu-west-1']
        
        all_volumes = []
        snapshots = self.get_snapshots(account_id, region)
        volumes_with_snapshots = {s.get('volumeId') for s in snapshots if s.get('volumeId')}
        
        for region_name in regions:
            try:
                ec2_client = session.client('ec2', region_name=region_name)
                response = ec2_client.describe_volumes()
                
                for volume in response['Volumes']:
                    if volume['VolumeId'] not in volumes_with_snapshots:
                        volume_data = {
                            'volumeId': volume['VolumeId'],
                            'size': volume['Size'],
                            'state': volume['State'],
                            'volumeType': volume['VolumeType'],
                            'createTime': volume['CreateTime'].isoformat(),
                            'region': region_name,
                            'attachments': volume.get('Attachments', []),
                            'tags': {tag['Key']: tag['Value'] for tag in volume.get('Tags', [])}
                        }
                        all_volumes.append(volume_data)
                        
            except Exception as e:
                logger.error(f"Error fetching volumes from {region_name}: {e}")
        
        return all_volumes
    
    def store_snapshot_data(self, account_id: str, snapshots: List[Dict]):
        """Store snapshot data in database for historical tracking"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Create snapshots table if it doesn't exist
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
        
        # Insert or update snapshot data
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
        logger.info(f"Stored {len(snapshots)} snapshots for account {account_id}")
    
    def get_amis(self, account_id: str, region: str = None, use_cache: bool = True) -> List[Dict]:
        """Fetch AMIs with caching and optimization"""
        cache_key = f"amis_{account_id}_{region or 'all'}"
        
        # Check cache first
        if use_cache and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                logger.info(f"Returning cached AMI data for account {account_id}")
                return cached_data['amis']
        
        # Fetch fresh data
        amis = self._fetch_amis_optimized(account_id, region)
        
        # Cache the results
        self.cache[cache_key] = {
            'amis': amis,
            'timestamp': time.time()
        }
        
        return amis
    
    def _fetch_amis_optimized(self, account_id: str, region: str = None) -> List[Dict]:
        """Fetch AMIs from AWS with parallel region processing"""
        session = self._get_boto3_session(account_id)
        
        # Define regions to check
        if region:
            regions = [region]
        else:
            # Get available regions
            ec2_client = session.client('ec2', region_name='us-east-1')
            try:
                regions_response = ec2_client.describe_regions()
                regions = [r['RegionName'] for r in regions_response['Regions']]
            except Exception as e:
                logger.warning(f"Could not get regions list: {e}")
                regions = ['us-east-1', 'us-west-2', 'eu-west-1']  # Fallback regions
        
        all_amis = []
        
        # Use ThreadPoolExecutor for parallel region processing
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_region = {
                executor.submit(self._fetch_region_amis, session, region_name): region_name 
                for region_name in regions
            }
            
            for future in as_completed(future_to_region):
                region_name = future_to_region[future]
                try:
                    amis = future.result()
                    all_amis.extend(amis)
                    logger.info(f"Fetched {len(amis)} AMIs from {region_name}")
                except Exception as e:
                    logger.error(f"Error fetching AMIs from {region_name}: {e}")
        
        return all_amis
    
    @backoff.on_exception(backoff.expo, (ClientError, BotoCoreError), max_tries=3)
    def _fetch_region_amis(self, session, region_name: str) -> List[Dict]:
        """Fetch AMIs from a specific region with retry logic"""
        try:
            ec2_client = session.client('ec2', region_name=region_name)
            
            # Get AMIs owned by the account
            response = ec2_client.describe_images(Owners=['self'])
            
            amis = []
            for ami in response['Images']:
                ami_data = self._format_ami_data(ami, region_name)
                amis.append(ami_data)
            
            return amis
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                logger.warning(f"No permission to describe AMIs in {region_name}")
                return []
            else:
                logger.error(f"AWS error in {region_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error in {region_name}: {e}")
            raise
    
    def _format_ami_data(self, ami: Dict, region_name: str) -> Dict:
        """Format AMI data for consistent API response"""
        ami_data = {
            'imageId': ami['ImageId'],
            'name': ami.get('Name', ''),
            'description': ami.get('Description', ''),
            'ownerId': ami['OwnerId'],
            'state': ami['State'],
            'architecture': ami.get('Architecture', ''),
            'creationDate': ami['CreationDate'],
            'public': ami.get('Public', False),
            'platform': ami.get('Platform', 'linux'),
            'virtualizationType': ami.get('VirtualizationType', ''),
            'hypervisor': ami.get('Hypervisor', ''),
            'region': region_name,
            'tags': {tag['Key']: tag['Value'] for tag in ami.get('Tags', [])},
            'blockDeviceMappings': ami.get('BlockDeviceMappings', [])
        }
        
        return ami_data
    
    def get_ami_analysis(self, account_id: str, region: str = None) -> Dict:
        """Analyze AMIs for dashboard metrics"""
        amis = self.get_amis(account_id, region)
        now = datetime.now()
        
        total_amis = len(amis)
        owned_amis = 0
        shared_amis = 0
        public_amis = 0
        amis_30_days = 0
        amis_60_days = 0
        amis_90_days = 0
        unused_amis = 0
        
        # Get account info to determine ownership
        result = self.db.execute_query('SELECT account_info FROM cloud_accounts WHERE id = ?', (account_id,))
        account_owner_id = None
        if result and len(result) > 0 and result[0][0]:
            try:
                account_info = json.loads(result[0][0])
                account_owner_id = account_info.get('account_id')
            except:
                pass
        
        for ami in amis:
            # Count ownership
            if account_owner_id and ami.get('ownerId') == account_owner_id:
                owned_amis += 1
            else:
                shared_amis += 1
            
            # Count public AMIs
            if ami.get('public', False):
                public_amis += 1
            
            # Calculate age
            try:
                creation_date = datetime.fromisoformat(ami['creationDate'].replace('Z', '+00:00'))
                days_old = (now - creation_date.replace(tzinfo=None)).days
                
                if days_old >= 90:
                    amis_90_days += 1
                elif days_old >= 60:
                    amis_60_days += 1
                elif days_old >= 30:
                    amis_30_days += 1
            except Exception as e:
                logger.warning(f"Error parsing AMI creation date: {e}")
        
        # Estimate storage cost (rough calculation)
        estimated_cost = total_amis * 0.05  # Rough estimate: $0.05 per AMI per month
        
        return {
            'total_amis': total_amis,
            'owned_amis': owned_amis,
            'shared_amis': shared_amis,
            'public_amis': public_amis,
            'amis_30_days': amis_30_days,
            'amis_60_days': amis_60_days,
            'amis_90_days': amis_90_days,
            'unused_amis': unused_amis,  # This would need more complex logic to determine
            'estimated_storage_cost': estimated_cost
        }
