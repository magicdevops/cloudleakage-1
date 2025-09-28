"""
EC2 Service for CloudLeakage
Handles EC2 instance data retrieval and analysis using stored account credentials
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

class EC2Service:
    def __init__(self, db_manager, cipher_suite):
        self.db = db_manager
        self.cipher_suite = cipher_suite
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
    
    def _get_boto3_session(self, account_id: str):
        """Create boto3 session using stored encrypted credentials"""
        # Use the database manager's execute_query method which handles PostgreSQL placeholders
        result = self.db.execute_query('''
            SELECT encrypted_credentials, provider, access_type, role_arn, account_info
            FROM cloud_accounts 
            WHERE id = ? AND status = 'connected'
        ''', (account_id,))
        
        if not result:
            raise ValueError(f"Account {account_id} not found or not connected")
        
        # Handle both tuple and dict-like results from PostgreSQL
        row = result[0]
        if hasattr(row, 'keys'):  # RealDictRow or dict-like
            encrypted_creds = row['encrypted_credentials']
            provider = row['provider']
            access_type = row['access_type']
            role_arn = row['role_arn']
            account_info = row['account_info']
        else:  # Tuple
            encrypted_creds, provider, access_type, role_arn, account_info = row
        
        if provider != 'aws':
            raise ValueError(f"Account {account_id} is not an AWS account (provider: {provider})")
        
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
                RoleSessionName='cloudleakage-session'
            )
            return boto3.Session(
                aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                aws_session_token=assumed_role['Credentials']['SessionToken'],
                region_name=json.loads(account_info).get('region', 'us-east-1')
            )
        
        raise ValueError(f"Unable to create session for account {account_id}")
    
    def get_ec2_instances(self, account_id: str, region: str = None, use_cache: bool = True) -> List[Dict]:
        """Fetch EC2 instances with caching and optimization"""
        cache_key = f"ec2_instances_{account_id}_{region or 'all'}"
        
        # Check cache first
        if use_cache and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                logger.info(f"Returning cached EC2 data for account {account_id}")
                return cached_data['instances']
        
        # Fetch fresh data
        instances = self._fetch_ec2_instances_optimized(account_id, region)
        
        # Cache the results
        self.cache[cache_key] = {
            'instances': instances,
            'timestamp': time.time()
        }
        
        return instances
    
    def _fetch_ec2_instances_optimized(self, account_id: str, region: str = None) -> List[Dict]:
        """Optimized EC2 instance fetching with parallel processing"""
        try:
            session = self._get_boto3_session(account_id)
            
            # Determine regions to query
            if region:
                regions = [region]
            else:
                # Prioritize common regions first for better user experience
                priority_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
                all_regions = self._get_all_regions(session)
                regions = priority_regions + [r for r in all_regions if r not in priority_regions]
            
            all_instances = []
            
            # Use ThreadPoolExecutor for parallel region processing
            with ThreadPoolExecutor(max_workers=min(5, len(regions))) as executor:
                future_to_region = {
                    executor.submit(self._get_region_instances_safe, session, region_name): region_name 
                    for region_name in regions
                }
                
                for future in as_completed(future_to_region):
                    region_name = future_to_region[future]
                    try:
                        instances = future.result(timeout=30)
                        all_instances.extend(instances)
                        logger.info(f"Collected {len(instances)} instances from {region_name}")
                    except Exception as e:
                        logger.error(f"Failed to get instances from {region_name}: {e}")
                        continue
            
            logger.info(f"Total instances collected: {len(all_instances)}")
            return all_instances
            
        except Exception as e:
            logger.error(f"Error fetching EC2 instances for account {account_id}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _get_all_regions(self, session) -> List[str]:
        """Get list of all available AWS regions"""
        try:
            ec2_client = session.client('ec2', region_name='us-east-1')
            response = ec2_client.describe_regions()
            return [r['RegionName'] for r in response['Regions']]
        except Exception as e:
            logger.warning(f"Failed to get regions, using default set: {e}")
            return ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1', 'ap-northeast-1']
    
    @backoff.on_exception(backoff.expo, 
                         (ClientError, BotoCoreError), 
                         max_tries=3,
                         max_time=60)
    def _get_region_instances_safe(self, session, region_name: str) -> List[Dict]:
        """Safely fetch instances from a single region with retry logic"""
        try:
            ec2_client = session.client('ec2', region_name=region_name)
            instances = []
            
            # Use paginator to handle large numbers of instances
            paginator = ec2_client.get_paginator('describe_instances')
            
            for page in paginator.paginate():
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        instance_data = self._normalize_instance_data(instance, region_name)
                        instances.append(instance_data)
            
            return instances
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                logger.warning(f"No access to region {region_name}: {error_code}")
                return []
            elif error_code in ['RequestLimitExceeded', 'Throttling']:
                logger.warning(f"Rate limited in region {region_name}, retrying...")
                raise  # Let backoff handle the retry
            else:
                logger.error(f"Error in region {region_name}: {e}")
                return []
        except Exception as e:
            logger.error(f"Unexpected error in region {region_name}: {e}")
            return []
    
    def _normalize_instance_data(self, instance: Dict, region_name: str) -> Dict:
        """Extract and normalize instance data"""
        instance_data = {
            'instanceId': instance['InstanceId'],
            'instanceType': instance['InstanceType'],
            'state': instance['State']['Name'],
            'region': region_name,
            'availabilityZone': instance['Placement']['AvailabilityZone'],
            'launchTime': instance['LaunchTime'].isoformat(),
            'platform': instance.get('Platform', 'linux'),
            'architecture': instance.get('Architecture', 'x86_64'),
            'vpcId': instance.get('VpcId'),
            'subnetId': instance.get('SubnetId'),
            'privateIpAddress': instance.get('PrivateIpAddress'),
            'publicIpAddress': instance.get('PublicIpAddress'),
            'keyName': instance.get('KeyName'),
            'securityGroups': [sg['GroupName'] for sg in instance.get('SecurityGroups', [])],
            'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])},
            'monitoring': instance.get('Monitoring', {}).get('State', 'disabled'),
            'ebsOptimized': instance.get('EbsOptimized', False),
            'rootDeviceType': instance.get('RootDeviceType'),
            'virtualizationType': instance.get('VirtualizationType'),
            'hypervisor': instance.get('Hypervisor')
        }
        
        # Add storage information
        storage_info = []
        for bdm in instance.get('BlockDeviceMappings', []):
            if 'Ebs' in bdm:
                storage_info.append({
                    'deviceName': bdm['DeviceName'],
                    'volumeId': bdm['Ebs']['VolumeId'],
                    'status': bdm['Ebs']['Status'],
                    'deleteOnTermination': bdm['Ebs']['DeleteOnTermination']
                })
        instance_data['storage'] = storage_info
        
        return instance_data
    
    def get_ec2_pricing(self, account_id: str, instance_type: str, region: str) -> Dict:
        """Get EC2 pricing information for instance type in region"""
        try:
            session = self._get_boto3_session(account_id)
            
            # Pricing API is only available in us-east-1
            pricing_client = session.client('pricing', region_name='us-east-1')
            
            response = pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operating-system', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'}
                ]
            )
            
            if response['PriceList']:
                price_data = json.loads(response['PriceList'][0])
                terms = price_data['terms']['OnDemand']
                
                for term_key in terms:
                    price_dimensions = terms[term_key]['priceDimensions']
                    for pd_key in price_dimensions:
                        price_per_hour = price_dimensions[pd_key]['pricePerUnit']['USD']
                        return {
                            'instanceType': instance_type,
                            'region': region,
                            'pricePerHour': float(price_per_hour),
                            'pricePerMonth': float(price_per_hour) * 24 * 30,
                            'currency': 'USD'
                        }
            
            return {'instanceType': instance_type, 'region': region, 'pricePerHour': 0.0}
            
        except Exception as e:
            logger.warning(f"Could not fetch pricing for {instance_type} in {region}: {e}")
            return {'instanceType': instance_type, 'region': region, 'pricePerHour': 0.0}
    
    def _get_location_name(self, region: str) -> str:
        """Convert AWS region code to location name for pricing API"""
        region_mapping = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'Europe (Ireland)',
            'eu-west-2': 'Europe (London)',
            'eu-central-1': 'Europe (Frankfurt)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
        }
        return region_mapping.get(region, region)
    
    def get_stopped_instances_by_duration(self, instances: List[Dict]) -> Dict:
        """Calculate stopped instances by different time periods"""
        now = datetime.now()
        
        stopped_30_days = 0
        stopped_60_days = 0
        stopped_90_days = 0
        
        for instance in instances:
            if instance.get('state') == 'stopped':
                # For stopped instances, we need to check when they were last stopped
                # Since we don't have stop time in the basic instance data, we'll use launch time as approximation
                # In a real implementation, you'd want to get the state transition history
                launch_time = datetime.fromisoformat(instance['launchTime'].replace('Z', '+00:00'))
                days_since_launch = (now - launch_time.replace(tzinfo=None)).days
                
                # This is a simplified calculation - in reality you'd want to track actual stop time
                if days_since_launch >= 90:
                    stopped_90_days += 1
                elif days_since_launch >= 60:
                    stopped_60_days += 1
                elif days_since_launch >= 30:
                    stopped_30_days += 1
        
        return {
            'stopped_30_days': stopped_30_days,
            'stopped_60_days': stopped_60_days,
            'stopped_90_days': stopped_90_days
        }

    def get_ec2_utilization(self, account_id: str, instance_id: str, days: int = 7) -> Dict:
        """Get CloudWatch metrics for EC2 instance utilization"""
        try:
            session = self._get_boto3_session(account_id)
            
            # Get instance region first
            ec2_client = session.client('ec2')
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            
            if not response['Reservations']:
                raise ValueError(f"Instance {instance_id} not found")
            
            instance = response['Reservations'][0]['Instances'][0]
            region = instance['Placement']['AvailabilityZone'][:-1]  # Remove AZ letter
            
            cloudwatch = session.client('cloudwatch', region_name=region)
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Get CPU utilization
            cpu_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=['Average', 'Maximum']
            )
            
            # Get network metrics
            network_in_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            network_out_response = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            return {
                'instanceId': instance_id,
                'period': f"{days} days",
                'cpuUtilization': {
                    'datapoints': sorted(cpu_response['Datapoints'], key=lambda x: x['Timestamp']),
                    'averageCpu': sum(dp['Average'] for dp in cpu_response['Datapoints']) / len(cpu_response['Datapoints']) if cpu_response['Datapoints'] else 0,
                    'maxCpu': max(dp['Maximum'] for dp in cpu_response['Datapoints']) if cpu_response['Datapoints'] else 0
                },
                'networkIn': {
                    'datapoints': sorted(network_in_response['Datapoints'], key=lambda x: x['Timestamp']),
                    'totalBytes': sum(dp['Sum'] for dp in network_in_response['Datapoints'])
                },
                'networkOut': {
                    'datapoints': sorted(network_out_response['Datapoints'], key=lambda x: x['Timestamp']),
                    'totalBytes': sum(dp['Sum'] for dp in network_out_response['Datapoints'])
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching utilization for instance {instance_id}: {e}")
            raise
    
    def clear_cache(self, account_id: str = None):
        """Clear cache for specific account or all accounts"""
        if account_id:
            keys_to_remove = [k for k in self.cache.keys() if account_id in k]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()
        logger.info(f"Cache cleared for account: {account_id or 'all'}")
    
    def get_optimization_recommendations(self, account_id: str) -> List[Dict]:
        """Generate EC2 optimization recommendations"""
        try:
            instances = self.get_ec2_instances(account_id, use_cache=True)
            recommendations = []
            
            for instance in instances:
                if instance['state'] != 'running':
                    continue
                
                # Get utilization data for recommendations
                try:
                    utilization = self.get_ec2_utilization(account_id, instance['instanceId'])
                    avg_cpu = utilization['cpuUtilization']['averageCpu']
                    
                    # Low utilization recommendation
                    if avg_cpu < 10:
                        recommendations.append({
                            'type': 'underutilized',
                            'severity': 'high',
                            'instanceId': instance['instanceId'],
                            'instanceType': instance['instanceType'],
                            'region': instance['region'],
                            'avgCpuUtilization': avg_cpu,
                            'recommendation': 'Consider downsizing or stopping this instance',
                            'potentialSavings': 'Up to 50-75% cost reduction',
                            'action': 'downsize_or_stop'
                        })
                    elif avg_cpu < 25:
                        recommendations.append({
                            'type': 'underutilized',
                            'severity': 'medium',
                            'instanceId': instance['instanceId'],
                            'instanceType': instance['instanceType'],
                            'region': instance['region'],
                            'avgCpuUtilization': avg_cpu,
                            'recommendation': 'Consider downsizing to a smaller instance type',
                            'potentialSavings': 'Up to 25-50% cost reduction',
                            'action': 'downsize'
                        })
                    
                    # High utilization recommendation
                    elif avg_cpu > 80:
                        recommendations.append({
                            'type': 'overutilized',
                            'severity': 'medium',
                            'instanceId': instance['instanceId'],
                            'instanceType': instance['instanceType'],
                            'region': instance['region'],
                            'avgCpuUtilization': avg_cpu,
                            'recommendation': 'Consider upgrading to a larger instance type',
                            'potentialSavings': 'Improved performance and user experience',
                            'action': 'upsize'
                        })
                        
                except Exception as e:
                    logger.warning(f"Could not get utilization for {instance['instanceId']}: {e}")
                    continue
                
                # Check for old generation instances
                if any(old_gen in instance['instanceType'] for old_gen in ['t2.', 'm4.', 'c4.', 'r4.']):
                    recommendations.append({
                        'type': 'outdated',
                        'severity': 'low',
                        'instanceId': instance['instanceId'],
                        'instanceType': instance['instanceType'],
                        'region': instance['region'],
                        'recommendation': 'Upgrade to newer generation instance type for better performance/cost',
                        'potentialSavings': 'Up to 20% cost reduction with better performance',
                        'action': 'upgrade_generation'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for account {account_id}: {e}")
            return []
    
    def store_ec2_data(self, account_id: str, instances: List[Dict]):
        """Store EC2 instance data in database for historical tracking"""
        try:
            for instance in instances:
                # Use database-agnostic upsert approach
                if self.db.db_type == 'postgresql':
                    # PostgreSQL uses ON CONFLICT
                    query = '''
                        INSERT INTO ec2_instances 
                        (account_id, instance_id, instance_type, state, region, 
                         availability_zone, launch_time, platform, vpc_id, 
                         private_ip, public_ip, tags, last_updated, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (account_id, instance_id) 
                        DO UPDATE SET 
                            instance_type = EXCLUDED.instance_type,
                            state = EXCLUDED.state,
                            region = EXCLUDED.region,
                            availability_zone = EXCLUDED.availability_zone,
                            launch_time = EXCLUDED.launch_time,
                            platform = EXCLUDED.platform,
                            vpc_id = EXCLUDED.vpc_id,
                            private_ip = EXCLUDED.private_ip,
                            public_ip = EXCLUDED.public_ip,
                            tags = EXCLUDED.tags,
                            last_updated = EXCLUDED.last_updated,
                            raw_data = EXCLUDED.raw_data
                    '''
                else:
                    # SQLite uses INSERT OR REPLACE
                    query = '''
                        INSERT OR REPLACE INTO ec2_instances 
                        (account_id, instance_id, instance_type, state, region, 
                         availability_zone, launch_time, platform, vpc_id, 
                         private_ip, public_ip, tags, last_updated, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    '''
                
                self.db.execute_query(query, (
                    account_id,
                    instance['instanceId'],
                    instance['instanceType'],
                    instance['state'],
                    instance['region'],
                    instance['availabilityZone'],
                    instance['launchTime'],
                    instance['platform'],
                    instance.get('vpcId'),
                    instance.get('privateIpAddress'),
                    instance.get('publicIpAddress'),
                    json.dumps(instance['tags']),
                    datetime.utcnow().isoformat(),
                    json.dumps(instance)
                ))
            
            logger.info(f"Stored {len(instances)} EC2 instances for account {account_id}")
            
        except Exception as e:
            logger.error(f"Error storing EC2 data: {e}")
            raise
