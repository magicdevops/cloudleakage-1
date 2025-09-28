#!/usr/bin/env python3
"""
AWS Cost Optimization Tool - Main Flask Application
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from app.services.account_manager import AccountManager, test_aws_credentials, perform_account_sync
from app.services.ec2_service import EC2Service
from app.services.snapshot_service import SnapshotService
from app.services.simple_database import DatabaseManager
import uuid
# from app.services.terraform_analyzer import TerraformAnalyzer  # Commented out due to missing google dependency

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_account_id():
    """Generate a unique account ID"""
    return str(uuid.uuid4())

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, template_folder='app/templates', static_folder='static')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Initialize encryption key for credential storage
    encryption_key = os.environ.get('ENCRYPTION_KEY')
    if not encryption_key:
        # Use a fixed key for development to maintain persistence
        # In production, set ENCRYPTION_KEY environment variable
        encryption_key = "oz2fA05GT7jHw-kReDcvXCHc9weUCOM2sBe7bIOQqps="
        logger.warning("Using default encryption key. Set ENCRYPTION_KEY environment variable in production.")
    
    app.config['ENCRYPTION_KEY'] = encryption_key
    app.config['CIPHER_SUITE'] = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
    
    # Initialize database
    database_path = os.environ.get('DATABASE_PATH', 'cloudleakage.db')
    db_manager = DatabaseManager(database_path)
    
    # Initialize services
    account_manager = AccountManager(app.config['CIPHER_SUITE'])
    ec2_service = EC2Service(db_manager, app.config['CIPHER_SUITE'])
    snapshot_service = SnapshotService(db_manager, app.config['CIPHER_SUITE'])
    
    # Store services in app config for access in routes
    app.config['ACCOUNT_MANAGER'] = account_manager
    app.config['EC2_SERVICE'] = ec2_service
    app.config['SNAPSHOT_SERVICE'] = snapshot_service
    app.config['DB_MANAGER'] = db_manager
    
    # Main dashboard route
    @app.route('/')
    @app.route('/dashboard')
    def dashboard():
        """Main dashboard with cost metrics and recommendations"""
        try:
            # Sample data for demonstration
            dashboard_data = {
                'current_month_cost': 2847.32,
                'last_month_cost': 3156.78,
                'cost_change': -9.8,
                'total_resources': 127,
                'active_alarms': 3,
                'recommendations_count': 8,
                'cost_trend': [2100, 2300, 2500, 2700, 2847],
                'top_services': [
                    {'name': 'EC2', 'cost': 1247.89, 'percentage': 43.8},
                    {'name': 'RDS', 'cost': 623.45, 'percentage': 21.9},
                    {'name': 'S3', 'cost': 345.67, 'percentage': 12.1},
                    {'name': 'Lambda', 'cost': 234.56, 'percentage': 8.2},
                    {'name': 'Others', 'cost': 395.75, 'percentage': 13.9}
                ],
                'recommendations': [
                    {
                        'title': 'Resize Underutilized EC2 Instances',
                        'description': '3 instances running at <20% CPU utilization',
                        'potential_savings': 234.50,
                        'priority': 'high'
                    },
                    {
                        'title': 'Delete Unused EBS Volumes',
                        'description': '5 unattached volumes consuming storage',
                        'potential_savings': 156.30,
                        'priority': 'medium'
                    },
                    {
                        'title': 'Optimize S3 Storage Classes',
                        'description': 'Move infrequently accessed data to IA',
                        'potential_savings': 89.20,
                        'priority': 'low'
                    }
                ]
            }
            return render_template('pages/dashboard.html', data=dashboard_data)
        except Exception as e:
            logger.error(f"Error loading dashboard: {str(e)}")
            return render_template('pages/dashboard.html', data={})

    # Business Units
    @app.route('/business-units')
    def business_units():
        """Business units management page"""
        return render_template('business_units/index.html')

    # Budgets
    @app.route('/budgets')
    def budgets():
        """Budget management page"""
        return render_template('layouts/base.html', title='Budgets')

    # Reports
    @app.route('/reports')
    def reports():
        """Reports page"""
        return render_template('layouts/base.html', title='Reports')

    # Integration routes
    @app.route('/integration')
    @app.route('/integration/accounts')
    def integration_accounts():
        """Account integration management"""
        return render_template('integration/accounts.html')

    @app.route('/integration/wizard')
    def integration_wizard():
        """Account integration wizard"""
        return render_template('integration/wizard.html')

    @app.route('/integration/api/policy/generate', methods=['POST'])
    def generate_policy():
        """Generate IAM policy for AWS integration"""
        try:
            data = request.get_json()
            provider = data.get('provider', 'aws')
            
            if provider == 'aws':
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "ce:GetCostAndUsage",
                                "ce:GetDimensionValues",
                                "ce:GetReservationCoverage",
                                "ce:GetReservationPurchaseRecommendation",
                                "ce:GetReservationUtilization",
                                "ce:GetSavingsPlansUtilization",
                                "ce:ListCostCategoryDefinitions",
                                "organizations:ListAccounts",
                                "organizations:ListCreateAccountStatus",
                                "organizations:DescribeOrganization",
                                "budgets:ViewBudget"
                            ],
                            "Resource": "*"
                        }
                    ]
                }
                
                return jsonify({
                    'success': True,
                    'policy_json': policy
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unsupported provider'
                }), 400
                
        except Exception as e:
            logger.error(f"Error generating policy: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    @app.route('/integration/api/accounts', methods=['POST'])
    def create_account_integration():
        """Create a new account integration"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['displayName', 'provider', 'accessType']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }), 400
            
            # Validate access type specific fields
            access_type = data.get('accessType')
            if access_type == 'accesskey':
                if not data.get('accessKeyId') or not data.get('secretAccessKey'):
                    return jsonify({
                        'success': False,
                        'error': 'Access Key ID and Secret Access Key are required for access key authentication'
                    }), 400
                
                # Test AWS credentials before storing
                test_result = test_aws_credentials(
                    data.get('accessKeyId'),
                    data.get('secretAccessKey'),
                    data.get('region', 'us-east-1')
                )
                
                if not test_result['valid']:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid AWS credentials: {test_result["error"]}'
                    }), 400
                
                # Store account integration in database
                account_data = {
                    'id': generate_account_id(),
                    'displayName': data.get('displayName'),
                    'provider': data.get('provider'),
                    'accessType': access_type,
                    'credentials': {
                        'accessKeyId': data.get('accessKeyId'),
                        'secretAccessKey': data.get('secretAccessKey'),
                        'region': data.get('region', 'us-east-1')
                    },
                    'status': 'connected',
                    'accountInfo': test_result.get('accountInfo', {}),
                    'billing': data.get('billing', 'yes'),
                    'accountType': data.get('accountType', 'organization'),
                    'exportName': data.get('exportName'),
                    'startDate': data.get('startDate')
                }
                
                # Save using database service
                account_id = app.config['ACCOUNT_MANAGER'].create_account(account_data)
                
                return jsonify({
                    'success': True,
                    'accountId': account_id,
                    'message': 'Account integration created successfully'
                })
            
            elif access_type == 'iam':
                if not data.get('roleArn'):
                    return jsonify({
                        'success': False,
                        'error': 'Role ARN is required for IAM role authentication'
                    }), 400
                
                # Test IAM role access
                test_result = test_iam_role(data.get('roleArn'))
                
                if not test_result['valid']:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid IAM role: {test_result["error"]}'
                    }), 400
                
                # Store IAM role integration
                account_data = {
                    'id': generate_account_id(),
                    'displayName': data.get('displayName'),
                    'provider': data.get('provider'),
                    'accessType': access_type,
                    'roleArn': data.get('roleArn'),
                    'status': 'connected',
                    'accountInfo': test_result.get('accountInfo', {}),
                    'billing': data.get('billing', 'yes'),
                    'accountType': data.get('accountType', 'organization'),
                    'exportName': data.get('exportName'),
                    'startDate': data.get('startDate')
                }
                
                account_id = app.config['ACCOUNT_MANAGER'].create_account(account_data)
                
                return jsonify({
                    'success': True,
                    'accountId': account_id,
                    'message': 'Account integration created successfully'
                })
            
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unsupported access type'
                }), 400
                
        except Exception as e:
            logger.error(f"Error creating account integration: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/integration/api/accounts', methods=['GET'])
    def list_account_integrations():
        """List all account integrations"""
        try:
            accounts = app.config['ACCOUNT_MANAGER'].get_all_accounts()
            
            return jsonify({
                'success': True,
                'accounts': accounts
            })
        except Exception as e:
            logger.error(f"Error listing account integrations: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/integration/api/accounts/<account_id>/sync', methods=['POST'])
    def sync_account_data(account_id):
        """Trigger data sync for a specific account"""
        try:
            account = app.config['ACCOUNT_MANAGER'].get_account_by_id(account_id)
            
            if not account:
                return jsonify({
                    'success': False,
                    'error': 'Account not found'
                }), 404
            
            # Convert account dict for compatibility
            account_dict = {
                'id': account['id'],
                'accessType': account['accessType'],
                'provider': account['provider']
            }
            
            # Perform sync
            sync_result = perform_account_sync(account_dict)
            
            if sync_result['success']:
                # Update last sync time in database
                app.config['ACCOUNT_MANAGER'].update_last_sync(account_id)
                
                return jsonify({
                    'success': True,
                    'message': 'Account sync completed successfully',
                    'syncData': sync_result.get('data', {})
                })
            else:
                return jsonify({
                    'success': False,
                    'error': sync_result.get('error', 'Sync failed')
                }), 500
                
        except Exception as e:
            logger.error(f"Error syncing account data: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    @app.route('/integration/api/accounts/<account_id>', methods=['DELETE'])
    def delete_account_integration(account_id):
        """Delete an account integration"""
        try:
            success = app.config['ACCOUNT_MANAGER'].delete_account(account_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Account integration deleted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Account not found or could not be deleted'
                }), 404
                
        except Exception as e:
            logger.error(f"Error deleting account integration: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    # Sync Management
    @app.route('/sync-management')
    def sync_management():
        """Data synchronization management"""
        return render_template('sync_management/dashboard.html')

    # API endpoints
    @app.route('/api/cost-data')
    def api_cost_data():
        """API endpoint for cost data"""
        return jsonify({
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'data': [2100, 2300, 2500, 2700, 2847]
        })

    @app.route('/api/recommendations')
    def api_recommendations():
        """API endpoint for recommendations"""
        recommendations = [
            {
                'id': 1,
                'title': 'Resize Underutilized EC2 Instances',
                'description': '3 instances running at <20% CPU utilization',
                'potential_savings': 234.50,
                'priority': 'high',
                'category': 'compute'
            },
            {
                'id': 2,
                'title': 'Delete Unused EBS Volumes',
                'description': '5 unattached volumes consuming storage',
                'potential_savings': 156.30,
                'priority': 'medium',
                'category': 'storage'
            }
        ]
        return jsonify(recommendations)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    # EC2 Dashboard Routes
    @app.route('/ec2')
    @app.route('/ec2/dashboard')
    def ec2_dashboard():
        """EC2 instances dashboard"""
        return render_template('aws/ec2/dashboard.html')
    
    @app.route('/ec2/api/accounts/<account_id>/instances')
    def get_ec2_instances(account_id):
        """API endpoint to get EC2 instances for an account"""
        try:
            ec2_service = app.config['EC2_SERVICE']
            region = request.args.get('region')
            
            instances = ec2_service.get_ec2_instances(account_id, region)
            
            return jsonify({
                'success': True,
                'instances': instances,
                'count': len(instances)
            })
            
        except Exception as e:
            logger.error(f"Error fetching EC2 instances: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/ec2/api/accounts/<account_id>/instances/<instance_id>/utilization')
    def get_instance_utilization(account_id, instance_id):
        """API endpoint to get instance utilization metrics"""
        try:
            ec2_service = app.config['EC2_SERVICE']
            days = int(request.args.get('days', 7))
            
            utilization = ec2_service.get_ec2_utilization(account_id, instance_id, days)
            
            return jsonify({
                'success': True,
                'utilization': utilization
            })
            
        except Exception as e:
            logger.error(f"Error fetching utilization: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/ec2/api/accounts/<account_id>/recommendations')
    def get_ec2_recommendations(account_id):
        """API endpoint to get EC2 optimization recommendations"""
        try:
            ec2_service = app.config['EC2_SERVICE']
            
            recommendations = ec2_service.get_optimization_recommendations(account_id)
            
            return jsonify({
                'success': True,
                'recommendations': recommendations
            })
        
        except Exception as e:
            logger.error(f"Error getting recommendations for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/ec2/api/accounts/<account_id>/stopped-duration')
    def get_stopped_instances_duration(account_id):
        """API endpoint to get stopped instances by duration"""
        try:
            ec2_service = app.config['EC2_SERVICE']
            region = request.args.get('region')
            
            # Get all instances first
            instances = ec2_service.get_ec2_instances(account_id, region)
            
            # Calculate stopped instances by duration
            duration_data = ec2_service.get_stopped_instances_by_duration(instances)
            
            return jsonify({
                'success': True,
                'duration_data': duration_data
            })
        
        except Exception as e:
            logger.error(f"Error getting stopped instances duration for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # Snapshots Dashboard Route
    @app.route('/snapshots')
    @app.route('/snapshots/dashboard')
    def snapshots_dashboard():
        """Snapshots & AMI dashboard page"""
        return render_template('aws/snapshots/dashboard.html')
    
    @app.route('/snapshots/api/accounts/<account_id>/snapshots', methods=['GET'])
    def get_snapshots(account_id):
        """API endpoint to get snapshots for an account"""
        try:
            snapshot_service = app.config['SNAPSHOT_SERVICE']
            region = request.args.get('region')
            
            snapshots = snapshot_service.get_snapshots(account_id, region)
            
            return jsonify({
                'success': True,
                'snapshots': snapshots
            })
        
        except Exception as e:
            logger.error(f"Error getting snapshots for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/snapshots/api/accounts/<account_id>/analysis')
    def get_snapshot_analysis(account_id):
        """API endpoint to get snapshot analysis data"""
        try:
            snapshot_service = app.config['SNAPSHOT_SERVICE']
            region = request.args.get('region')
            
            snapshots = snapshot_service.get_snapshots(account_id, region)
            analysis = snapshot_service.get_snapshot_analysis(snapshots)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
        
        except Exception as e:
            logger.error(f"Error getting snapshot analysis for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/snapshots/api/accounts/<account_id>/volumes-without-snapshots')
    def get_volumes_without_snapshots(account_id):
        """API endpoint to get volumes without snapshots"""
        try:
            snapshot_service = app.config['SNAPSHOT_SERVICE']
            region = request.args.get('region')
            
            volumes = snapshot_service.get_volumes_without_snapshots(account_id, region)
            
            return jsonify({
                'success': True,
                'volumes': volumes
            })
        
        except Exception as e:
            logger.error(f"Error getting volumes without snapshots for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/snapshots/api/accounts/<account_id>/sync', methods=['POST'])
    def sync_snapshot_data(account_id):
        """API endpoint to sync snapshot data for an account"""
        try:
            snapshot_service = app.config['SNAPSHOT_SERVICE']
            
            # Fetch fresh snapshot data
            snapshots = snapshot_service.get_snapshots(account_id, use_cache=False)
            
            # Store in database
            snapshot_service.store_snapshot_data(account_id, snapshots)
            
            return jsonify({
                'success': True,
                'snapshots_synced': len(snapshots),
                'message': f'Successfully synced {len(snapshots)} snapshots'
            })
        
        except Exception as e:
            logger.error(f"Error syncing snapshot data for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # AMI API endpoints
    @app.route('/snapshots/api/accounts/<account_id>/amis', methods=['GET'])
    def get_ami_analysis(account_id):
        """API endpoint to get AMI analysis data"""
        try:
            snapshot_service = app.config['SNAPSHOT_SERVICE']
            region = request.args.get('region')
            
            # Get AMI analysis data
            analysis = snapshot_service.get_ami_analysis(account_id, region)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
        
        except Exception as e:
            logger.error(f"Error getting AMI analysis for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/snapshots/api/accounts/<account_id>/amis/list', methods=['GET'])
    def get_amis_list(account_id):
        """API endpoint to get AMIs list for an account"""
        try:
            snapshot_service = app.config['SNAPSHOT_SERVICE']
            region = request.args.get('region')
            
            # Get AMIs data
            amis = snapshot_service.get_amis(account_id, region)
            
            return jsonify({
                'success': True,
                'amis': amis
            })
        
        except Exception as e:
            logger.error(f"Error getting AMIs for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/snapshots/api/accounts/<account_id>/big-volume-snapshots', methods=['GET'])
    def get_big_volume_snapshots(account_id):
        """API endpoint to get big volume snapshots list for an account"""
        try:
            snapshot_service = app.config['SNAPSHOT_SERVICE']
            region = request.args.get('region')
            size_threshold = int(request.args.get('size_threshold', 100))
            
            # Get big volume snapshots data
            big_snapshots = snapshot_service.get_big_volume_snapshots(account_id, region, size_threshold)
            
            return jsonify({
                'success': True,
                'snapshots': big_snapshots
            })
        
        except Exception as e:
            logger.error(f"Error getting big volume snapshots for account {account_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/ec2/api/accounts/<account_id>/sync', methods=['POST'])
    def sync_ec2_data(account_id):
        """API endpoint to sync EC2 data for an account"""
        try:
            ec2_service = app.config['EC2_SERVICE']
            
            # Fetch fresh EC2 data
            instances = ec2_service.get_ec2_instances(account_id)
            
            # Store in database
            ec2_service.store_ec2_data(account_id, instances)
            
            return jsonify({
                'success': True,
                'message': f'Synced {len(instances)} EC2 instances',
                'instances_synced': len(instances)
            })
            
        except Exception as e:
            logger.error(f"Error syncing EC2 data: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # CloudWatch Dashboard Routes
    @app.route('/cloudwatch')
    @app.route('/cloudwatch/dashboard')
    def cloudwatch_dashboard():
        """CloudWatch alarms dashboard"""
        return render_template('aws/cloudwatch/dashboard.html')
    
    @app.route('/cloudwatch/insights')
    def cloudwatch_insights():
        """CloudWatch RAG insights page"""
        return render_template('aws/cloudwatch/insights.html')
    
    @app.route('/cloudwatch/api/accounts/<account_id>/alarms')
    def get_cloudwatch_alarms(account_id):
        """API endpoint to get CloudWatch alarms for an account"""
        try:
            # Simulated CloudWatch alarms data
            region = request.args.get('region')
            
            # Mock alarm data
            alarms = [
                {
                    'alarmName': 'HighCPUUtilization-WebServer',
                    'state': 'ALARM',
                    'metricName': 'CPUUtilization',
                    'threshold': 80,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': region or 'us-east-1',
                    'stateUpdatedTimestamp': '2024-01-15T10:30:00Z',
                    'alarmDescription': 'CPU utilization is too high'
                },
                {
                    'alarmName': 'LowDiskSpace-Database',
                    'state': 'OK',
                    'metricName': 'DiskSpaceUtilization',
                    'threshold': 90,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': region or 'us-east-1',
                    'stateUpdatedTimestamp': '2024-01-15T09:15:00Z',
                    'alarmDescription': 'Disk space monitoring'
                },
                {
                    'alarmName': 'MemoryUtilization-AppServer',
                    'state': 'INSUFFICIENT_DATA',
                    'metricName': 'MemoryUtilization',
                    'threshold': 85,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': region or 'us-east-1',
                    'stateUpdatedTimestamp': '2024-01-15T08:45:00Z',
                    'alarmDescription': 'Memory usage monitoring'
                }
            ]
            
            return jsonify({
                'success': True,
                'alarms': alarms
            })
            
        except Exception as e:
            logger.error(f"Error getting CloudWatch alarms: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/cloudwatch/api/accounts/<account_id>/sync', methods=['POST'])
    def sync_cloudwatch_data(account_id):
        """API endpoint to sync CloudWatch data for an account"""
        try:
            # Simulated sync operation
            alarms_synced = 15
            
            return jsonify({
                'success': True,
                'alarms_synced': alarms_synced,
                'message': f'Successfully synced {alarms_synced} CloudWatch alarms'
            })
            
        except Exception as e:
            logger.error(f"Error syncing CloudWatch data: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/cloudwatch/api/accounts/<account_id>/duplicate-analysis')
    def analyze_duplicate_alarms(account_id):
        """API endpoint to analyze duplicate CloudWatch alarms"""
        try:
            # Get current alarms for the account
            region = request.args.get('region')
            
            # Mock alarm data for analysis (in real implementation, get from CloudWatch API)
            mock_alarms = [
                {
                    'alarmName': 'HighCPUUtilization-WebServer-1',
                    'metricName': 'CPUUtilization',
                    'threshold': 80,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': 'us-east-1',
                    'dimensions': [{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}],
                    'alarmActions': ['arn:aws:sns:us-east-1:123456789012:alerts']
                },
                {
                    'alarmName': 'HighCPUUtilization-WebServer-2',
                    'metricName': 'CPUUtilization',
                    'threshold': 85,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': 'us-east-1',
                    'dimensions': [{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}],
                    'alarmActions': ['arn:aws:sns:us-east-1:123456789012:alerts']
                },
                {
                    'alarmName': 'HighMemoryUtilization-WebServer',
                    'metricName': 'MemoryUtilization',
                    'threshold': 90,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': 'us-east-1',
                    'dimensions': [{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}],
                    'alarmActions': ['arn:aws:sns:us-east-1:123456789012:alerts']
                },
                {
                    'alarmName': 'DiskSpaceAlert-WebServer',
                    'metricName': 'DiskSpaceUtilization',
                    'threshold': 85,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': 'us-east-1',
                    'dimensions': [{'Name': 'InstanceId', 'Value': 'i-abcdef1234567890'}],
                    'alarmActions': ['arn:aws:sns:us-east-1:123456789012:alerts']
                },
                {
                    'alarmName': 'DiskSpaceWarning-WebServer',
                    'metricName': 'DiskSpaceUtilization',
                    'threshold': 80,
                    'comparisonOperator': 'GreaterThanThreshold',
                    'region': 'us-east-1',
                    'dimensions': [{'Name': 'InstanceId', 'Value': 'i-abcdef1234567890'}],
                    'alarmActions': ['arn:aws:sns:us-east-1:123456789012:alerts']
                }
            ]
            
            # Analyze duplicates
            analysis = analyze_alarm_duplicates(mock_alarms)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error analyzing duplicate alarms: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Terraform Analyzer Routes
    @app.route('/terraform')
    def terraform_analyzer():
        """Terraform state analyzer page"""
        return render_template('aws/terraform/analyzer.html')
    
    @app.route('/terraform/diagram')
    def terraform_diagram():
        """Terraform architecture diagram page"""
        return render_template('aws/terraform/diagram.html')

    @app.route('/terraform/api/analyze', methods=['POST'])
    def analyze_terraform_state():
        """Analyze uploaded terraform.tfstate file"""
        if 'tfstate_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'})
        
        file = request.files['tfstate_file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'})
            
        if file:
            try:
                state_content = file.read().decode('utf-8')
                graph_data = analyze_state_file(state_content)
                
                return jsonify({
                    'success': True,
                    'data': graph_data
                })
            except Exception as e:
                logger.error(f"Error analyzing Terraform state: {str(e)}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        return jsonify({'success': False, 'error': 'File processing error'}), 500
        """API endpoint to sync EC2 data for an account"""
        try:
            ec2_service = app.config['EC2_SERVICE']
            
            # Fetch fresh EC2 data
            instances = ec2_service.get_ec2_instances(account_id)
            
            # Store in database
            ec2_service.store_ec2_data(account_id, instances)
            
            return jsonify({
                'success': True,
                'message': f'Synced {len(instances)} EC2 instances',
                'instances_synced': len(instances)
            })
            
        except Exception as e:
            logger.error(f"Error syncing EC2 data: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Additional helper function for Terraform analysis
    def analyze_state_file(state_content):
        """Analyze Terraform state file content"""
        try:
            import json
            state_data = json.loads(state_content) if isinstance(state_content, str) else state_content
            
            nodes = []
            edges = []
            resource_types = set()
            
            # Extract resources from state
            resources = []
            if 'resources' in state_data:
                resources = state_data['resources']
            elif 'modules' in state_data:
                # Older Terraform format
                for module in state_data['modules']:
                    if 'resources' in module:
                        resources.extend(module['resources'].values())
            
            # Process each resource
            for i, resource in enumerate(resources):
                if resource.get('mode') == 'managed':
                    resource_type = resource['type']
                    resource_name = resource['name']
                    resource_id = f"{resource_type}.{resource_name}"
                    
                    # Add to resource types
                    resource_types.add(resource_type)
                    
                    # Get resource attributes
                    attributes = {}
                    if 'instances' in resource and resource['instances']:
                        attributes = resource['instances'][0].get('attributes', {})
                    
                    # Create node
                    node = {
                        'id': i,
                        'label': resource_name,
                        'title': resource_id,
                        'group': resource_type,
                        'image': get_resource_icon_url(resource_type),
                        'attributes': attributes
                    }
                    nodes.append(node)
                    
                    # Create simple dependencies (for demo purposes)
                    if i > 0:
                        edges.append({
                            'from': i - 1,
                            'to': i,
                            'arrows': 'to'
                        })
            
            return {
                "nodes": nodes,
                "edges": edges,
                "resource_types": list(resource_types)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing state file: {str(e)}")
            logger.error(f"State content type: {type(state_content)}")
            if isinstance(state_content, str):
                logger.error(f"State content preview: {state_content[:200]}...")
            return {"nodes": [], "edges": [], "resource_types": []}
    
    def get_resource_icon_url(resource_type):
        """Get icon URL for resource type"""
        icon_map = {
            'aws_instance': 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/Compute/EC2.png',
            'aws_vpc': 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/NetworkingContentDelivery/VPC.png',
            'aws_subnet': 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/NetworkingContentDelivery/VPC.png',
            'aws_security_group': 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/SecurityIdentityCompliance/IAM.png',
            'aws_s3_bucket': 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/Storage/S3.png',
            'aws_rds_instance': 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/Database/RDS.png',
            'aws_lambda_function': 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/Compute/Lambda.png'
        }
        return icon_map.get(resource_type, 'https://cdn.jsdelivr.net/gh/aws-samples/aws-icons-for-plantuml@main/dist/General/General.png')

    @app.route('/terraform/api/generate-diagram', methods=['POST'])
    def generate_terraform_diagram():
        """Generate architecture diagram from Terraform state"""
        try:
            data = request.get_json()
            state_data = data.get('stateData')
            
            if not state_data:
                return jsonify({'success': False, 'error': 'No state data provided'})
            
            # Parse and generate diagram
            diagram_generator = TerraformDiagramGenerator()
            graph_data = diagram_generator.generate_cytoscape_data(state_data)
            
            if graph_data.get('success', False):
                return jsonify({
                    'success': True,
                    'graphData': {
                        'elements': graph_data['elements'],
                        'metadata': graph_data.get('metadata', {})
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': graph_data.get('error', 'Unknown error in diagram generation')
                })
            
        except Exception as e:
            logger.error(f"Error generating Terraform diagram: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/terraform/api/test-diagram', methods=['POST'])
    def test_terraform_diagram():
        """Test endpoint with minimal data"""
        try:
            return jsonify({
                'success': True,
                'graphData': {
                    'elements': [
                        { 'data': { 'id': 'test-vpc', 'label': '🌐 test-vpc', 'category': 'network', 'type': 'aws_vpc' } },
                        { 'data': { 'id': 'test-subnet', 'label': '📡 test-subnet', 'category': 'network', 'type': 'aws_subnet' } },
                        { 'data': { 'id': 'test-instance', 'label': '🖥️ test-instance', 'category': 'compute', 'type': 'aws_instance' } },
                        { 'data': { 'id': 'vpc-subnet', 'source': 'test-vpc', 'target': 'test-subnet', 'type': 'dependency' } },
                        { 'data': { 'id': 'subnet-instance', 'source': 'test-subnet', 'target': 'test-instance', 'type': 'dependency' } }
                    ],
                    'metadata': {
                        'total_resources': 3,
                        'total_dependencies': 2,
                        'categories': ['network', 'compute'],
                        'providers': ['aws']
                    }
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/cloudwatch/api/query', methods=['POST'])
    def cloudwatch_natural_query():
        """Process natural language queries for CloudWatch data"""
        try:
            from cloudwatch_rag import CloudWatchRAG
            
            data = request.get_json()
            query = data.get('query', '').strip()
            account_id = data.get('account_id')
            region = data.get('region')
            
            if not query:
                return jsonify({
                    'success': False,
                    'error': 'Query is required'
                }), 400
            
            # Initialize RAG system
            rag = CloudWatchRAG()
            
            # Process query
            result = rag.query(query, account_id, region)
            
            return jsonify({
                'success': result.success,
                'query': query,
                'sql_query': result.sql_query,
                'data': result.data,
                'summary': result.summary,
                'execution_time_ms': result.execution_time_ms,
                'error': result.error,
                'data_count': len(result.data)
            })
            
        except Exception as e:
            logger.error(f"Natural language query failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/cloudwatch/api/ingest-sample-data', methods=['POST'])
    def ingest_sample_cloudwatch_data():
        """Ingest sample CloudWatch data for testing"""
        try:
            from cloudwatch_rag import CloudWatchDataIngestion
            from datetime import datetime, timedelta
            import random
            
            ingestion = CloudWatchDataIngestion()
            
            # Generate sample metrics data
            sample_metrics = []
            base_time = datetime.now()
            
            for i in range(100):
                timestamp = base_time - timedelta(minutes=i*5)
                sample_metrics.append({
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'namespace': 'AWS/EC2',
                    'metric_name': 'CPUUtilization',
                    'dimensions': {'InstanceId': f'i-{random.randint(100000, 999999)}'},
                    'timestamp': timestamp.isoformat(),
                    'value': random.uniform(10, 90),
                    'unit': 'Percent',
                    'statistic': 'Average'
                })
            
            # Generate sample log data
            sample_logs = []
            log_levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
            
            for i in range(50):
                timestamp = base_time - timedelta(minutes=i*2)
                level = random.choice(log_levels)
                
                if level == 'ERROR':
                    message = f"Database connection failed: Connection timeout after 30s"
                elif level == 'WARN':
                    message = f"High memory usage detected: {random.randint(80, 95)}%"
                else:
                    message = f"Request processed successfully in {random.randint(100, 500)}ms"
                
                sample_logs.append({
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'log_group': '/aws/lambda/my-function',
                    'log_stream': f'2024/01/01/[LATEST]{random.randint(1000, 9999)}',
                    'timestamp': timestamp.isoformat(),
                    'message': message,
                    'log_level': level,
                    'request_id': f'req-{random.randint(100000, 999999)}'
                })
            
            # Ingest data
            ingestion.ingest_metrics(sample_metrics)
            ingestion.ingest_logs(sample_logs)
            
            return jsonify({
                'success': True,
                'message': f'Ingested {len(sample_metrics)} metrics and {len(sample_logs)} logs'
            })
            
        except Exception as e:
            logger.error(f"Sample data ingestion failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/cloudwatch/api/query-examples')
    def get_query_examples():
        """Get example natural language queries"""
        examples = [
            {
                'category': 'Performance',
                'queries': [
                    "Show me CPU utilization for the last 24 hours",
                    "What instances had high CPU usage today?",
                    "Find servers with CPU above 80% in the last hour"
                ]
            },
            {
                'category': 'Errors & Issues',
                'queries': [
                    "Show me all error logs from today",
                    "What are the most common errors in the last week?",
                    "Find database connection errors in the last 24 hours"
                ]
            },
            {
                'category': 'Alarms',
                'queries': [
                    "Show me all active alarms",
                    "What alarms triggered in the last hour?",
                    "List all critical alarms for production instances"
                ]
            },
            {
                'category': 'Trends',
                'queries': [
                    "Show memory usage trends for the last week",
                    "Compare CPU usage between today and yesterday",
                    "What's the average response time for my API?"
                ]
            }
        ]
        
        return jsonify({
            'success': True,
            'examples': examples
        })

    @app.route('/terraform/api/debug', methods=['GET'])
    def debug_terraform():
        """Debug endpoint to test basic functionality"""
        try:
            return jsonify({
                'success': True,
                'message': 'Terraform API is working',
                'test_data': {
                    'elements': [
                        {
                            'data': {
                                'id': 'test-node',
                                'label': 'Test Node',
                                'type': 'test',
                                'category': 'test'
                            }
                        }
                    ]
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/terraform/api/ai-analyze', methods=['POST'])
    def ai_analyze_terraform():
        """AI-powered Terraform state analysis using Gemini"""
        try:
            from app.services.terraform_ai_analyzer import TerraformAIAnalyzer
            
            data = request.get_json()
            state_data = data.get('stateData')
            
            if not state_data:
                return jsonify({
                    'success': False,
                    'error': 'No state data provided'
                }), 400
            
            # Initialize AI analyzer
            ai_analyzer = TerraformAIAnalyzer()
            
            # Perform AI analysis
            analysis_result = ai_analyzer.analyze_terraform_state(state_data)
            
            if analysis_result.success:
                return jsonify({
                    'success': True,
                    'analysis': {
                        'findings': analysis_result.findings,
                        'security_suggestions': analysis_result.security_suggestions,
                        'cost_suggestions': analysis_result.cost_suggestions,
                        'mermaid_diagram': analysis_result.mermaid_diagram,
                        'ai_available': ai_analyzer.is_available()
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': analysis_result.error,
                    'ai_available': ai_analyzer.is_available()
                }), 500
                
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return app

class TerraformDiagramGenerator:
    """Advanced Terraform diagram generator with dependency analysis and proper grouping"""
    
    def __init__(self):
        self.metadata = {}
        self.resources = []
        self.dependencies = []
    
    def generate_cytoscape_data(self, state_data):
        """Generate Cytoscape.js compatible graph data with proper grouping and dependencies"""
        try:
            print(f"Processing state data with {len(state_data.get('resources', []))} resources")
            
            self.resources = self._extract_resources_with_dependencies(state_data)
            print(f"Extracted {len(self.resources)} resources")
            
            self.dependencies = self._analyze_dependencies(state_data)
            print(f"Found {len(self.dependencies)} dependencies")
            
            result = self._create_cytoscape_graph()
            print(f"Created graph with {len(result.get('elements', []))} elements")
            
            return result
        except Exception as e:
            print(f"Error in generate_cytoscape_data: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'elements': []
            }
    
    def _extract_resources_with_dependencies(self, state_data):
        """Extract resources with detailed attributes and dependency information"""
        resources = []
        try:
            if not isinstance(state_data, dict) or 'resources' not in state_data:
                return resources
                
            for resource in state_data['resources']:
                try:
                    if resource.get('mode') == 'managed':
                        # Get resource attributes for dependency analysis
                        attributes = {}
                        if 'instances' in resource and resource['instances'] and len(resource['instances']) > 0:
                            attributes = resource['instances'][0].get('attributes', {})
                        
                        # Ensure we have valid resource type and name
                        resource_type = resource.get('type', '')
                        resource_name = resource.get('name', '')
                        
                        if not resource_type or not resource_name:
                            continue
                        
                        resource_data = {
                            'id': f"{resource_type}.{resource_name}",
                            'type': resource_type,
                            'name': resource_name,
                            'category': self._get_category(resource_type),
                            'attributes': attributes,
                            'dependencies': resource.get('dependencies', []),
                            'provider': self._get_provider(resource_type)
                        }
                        resources.append(resource_data)
                except Exception as e:
                    print(f"Error processing resource: {e}")
                    continue
        except Exception as e:
            print(f"Error extracting resources: {e}")
        
        return resources
    
    def _analyze_dependencies(self, state_data):
        """Analyze resource dependencies from Terraform state"""
        dependencies = []
        
        if 'resources' in state_data:
            for resource in state_data['resources']:
                if resource.get('mode') == 'managed':
                    resource_id = f"{resource['type']}.{resource['name']}"
                    
                    # Check explicit dependencies
                    if 'dependencies' in resource:
                        for dep in resource['dependencies']:
                            dependencies.append({
                                'source': dep,
                                'target': resource_id,
                                'type': 'dependency'
                            })
                    
                    # Check attribute references (implicit dependencies)
                    if 'instances' in resource and resource['instances']:
                        attributes = resource['instances'][0].get('attributes', {})
                        self._extract_attribute_references(attributes, resource_id, dependencies)
        
        return dependencies
    
    def _extract_attribute_references(self, attributes, resource_id, dependencies):
        """Extract implicit dependencies from resource attributes"""
        try:
            if not isinstance(attributes, dict):
                return
                
            for key, value in attributes.items():
                if value is None:
                    continue
                    
                if isinstance(value, str):
                    # Look for references like "aws_vpc.main.id"
                    try:
                        if '.' in value and any(provider in value for provider in ['aws_', 'google_', 'azurerm_']):
                            # Extract referenced resource
                            parts = value.split('.')
                            if len(parts) >= 2:
                                referenced_resource = f"{parts[0]}.{parts[1]}"
                                dependencies.append({
                                    'source': referenced_resource,
                                    'target': resource_id,
                                    'type': 'reference',
                                    'attribute': key
                                })
                    except (AttributeError, TypeError):
                        continue
                elif isinstance(value, dict):
                    self._extract_attribute_references(value, resource_id, dependencies)
                elif isinstance(value, list):
                    for item in value:
                        if item is None:
                            continue
                        if isinstance(item, dict):
                            self._extract_attribute_references(item, resource_id, dependencies)
                        elif isinstance(item, str):
                            try:
                                if '.' in item and any(provider in item for provider in ['aws_', 'google_', 'azurerm_']):
                                    parts = item.split('.')
                                    if len(parts) >= 2:
                                        referenced_resource = f"{parts[0]}.{parts[1]}"
                                        dependencies.append({
                                            'source': referenced_resource,
                                            'target': resource_id,
                                            'type': 'reference',
                                            'attribute': key
                                        })
                            except (AttributeError, TypeError):
                                continue
        except Exception as e:
            print(f"Error processing attributes for {resource_id}: {e}")
            # Continue processing other resources
    
    def _get_category(self, resource_type):
        """Categorize resources for better organization"""
        if any(x in resource_type for x in ['vpc', 'subnet', 'gateway', 'route', 'nat']):
            return 'network'
        elif any(x in resource_type for x in ['instance', 'launch', 'autoscaling', 'lambda']):
            return 'compute'
        elif any(x in resource_type for x in ['bucket', 'volume', 'snapshot', 'efs']):
            return 'storage'
        elif any(x in resource_type for x in ['security_group', 'iam', 'policy', 'role']):
            return 'security'
        elif any(x in resource_type for x in ['rds', 'dynamodb', 'elasticache']):
            return 'database'
        else:
            return 'other'
    
    def _get_provider(self, resource_type):
        """Get cloud provider from resource type"""
        if resource_type.startswith('aws_'):
            return 'aws'
        elif resource_type.startswith('google_'):
            return 'gcp'
        elif resource_type.startswith('azurerm_'):
            return 'azure'
        else:
            return 'unknown'
    
    def _create_cytoscape_graph(self):
        """Create Cytoscape.js compatible graph structure"""
        elements = []
        
        # Safe string conversion function
        def safe_str(value, default=''):
            if value is None:
                return default
            return str(value)
        
        # Group resources by category for compound nodes
        categories = {}
        for resource in self.resources:
            if not isinstance(resource, dict):
                continue
            category = safe_str(resource.get('category', 'unknown'))
            if category not in categories:
                categories[category] = []
            categories[category].append(resource)
        
        # Create parent nodes for each category
        for category, resources in categories.items():
            if len(resources) > 1:  # Only create parent if multiple resources
                elements.append({
                    'data': {
                        'id': safe_str(f'parent_{category}'),
                        'label': safe_str(f'{category.title()} Resources'),
                        'type': safe_str('parent'),
                        'category': safe_str(category),
                        'provider': safe_str(''),
                        'name': safe_str('')
                    }
                })
        
        # Create nodes for each resource
        for resource in self.resources:
            if not isinstance(resource, dict):
                print(f"Skipping non-dict resource: {resource}")
                continue
                
            # Ensure all values are safely converted to strings
            resource_id = safe_str(resource.get('id'))
            resource_type = safe_str(resource.get('type'))
            resource_name = safe_str(resource.get('name'))
            resource_category = safe_str(resource.get('category', 'unknown'))
            resource_provider = safe_str(resource.get('provider', 'unknown'))
            
            if not resource_id or not resource_type:
                print(f"Skipping resource with missing id or type: {resource}")
                continue
            
            # Use resource_name or fallback to resource_id for display
            display_name = resource_name if resource_name else resource_id
            
            node_data = {
                'id': resource_id,
                'label': safe_str(f"{self._get_icon(resource_type)} {display_name}"),
                'type': resource_type,
                'category': resource_category,
                'provider': resource_provider,
                'name': display_name
            }
            
            # Add parent if category has multiple resources
            if resource_category in categories and len(categories[resource_category]) > 1:
                node_data['parent'] = safe_str(f"parent_{resource_category}")
            
            elements.append({'data': node_data})
        
        # Create edges for dependencies
        for dep in self.dependencies:
            # Validate dependency data
            if not isinstance(dep, dict) or 'source' not in dep or 'target' not in dep:
                print(f"Skipping invalid dependency: {dep}")
                continue
                
            dep_source = safe_str(dep.get('source'))
            dep_target = safe_str(dep.get('target'))
            dep_type = safe_str(dep.get('type', 'dependency'))
            dep_attribute = safe_str(dep.get('attribute', ''))
            
            if not dep_source or not dep_target:
                print(f"Skipping dependency with missing source/target: {dep}")
                continue
            
            # Create unique edge ID
            edge_id = safe_str(f"{dep_source}_to_{dep_target}")
            
            elements.append({
                'data': {
                    'id': edge_id,
                    'source': dep_source,
                    'target': dep_target,
                    'type': dep_type,
                    'label': dep_attribute,
                    'category': safe_str(''),
                    'provider': safe_str(''),
                    'name': safe_str('')
                }
            })
        
        
        return {
            'success': True,
            'elements': elements,
            'metadata': {
                'total_resources': len(self.resources),
                'total_dependencies': len(self.dependencies),
                'categories': list(categories.keys()),
                'providers': list(set(r['provider'] for r in self.resources))
            }
        }
    
    def _get_icon(self, resource_type):
        """Get appropriate icon for resource type"""
        icon_map = {
            # Network
            'aws_vpc': '🌐',
            'aws_subnet': '📡',
            'aws_internet_gateway': '🌍',
            'aws_route_table': '🛣️',
            'aws_nat_gateway': '🔄',
            
            # Compute  
            'aws_instance': '🖥️',
            'aws_launch_template': '🚀',
            'aws_autoscaling_group': '📈',
            'aws_lambda_function': '⚡',
            
            # Storage
            'aws_s3_bucket': '🪣',
            'aws_ebs_volume': '💾',
            'aws_efs_file_system': '📁',
            
            # Security
            'aws_security_group': '🔒',
            'aws_iam_role': '👤',
            'aws_iam_policy': '📋',
            
            # Database
            'aws_rds_instance': '🗄️',
            'aws_dynamodb_table': '📊',
            'aws_elasticache_cluster': '⚡'
        }
        return icon_map.get(resource_type, '📦')
    
    def get_metadata(self):
        """Return metadata about the infrastructure"""
        return self.metadata

def analyze_alarm_duplicates(alarms):
    """Analyze CloudWatch alarms for duplicates and redundancies"""
    duplicate_groups = []
    total_duplicates = 0
    similar_thresholds = 0
    redundant_actions = 0
    total_savings = 0
    
    # Group alarms by metric + resource combination
    metric_resource_groups = {}
    for alarm in alarms:
        # Create a key based on metric name and resource dimensions
        dimensions_key = ""
        if alarm.get('dimensions'):
            dimensions_key = "|".join([f"{d['Name']}:{d['Value']}" for d in alarm['dimensions']])
        
        key = f"{alarm['metricName']}|{dimensions_key}"
        
        if key not in metric_resource_groups:
            metric_resource_groups[key] = []
        metric_resource_groups[key].append(alarm)
    
    # Analyze each group for duplicates
    for key, group_alarms in metric_resource_groups.items():
        if len(group_alarms) > 1:
            # Found potential duplicates
            group_type = "Exact Duplicate Alarms"
            severity = "high"
            description = f"Multiple alarms monitoring the same metric on the same resource"
            
            # Check for similar thresholds
            thresholds = [alarm['threshold'] for alarm in group_alarms]
            threshold_variance = max(thresholds) - min(thresholds)
            
            if threshold_variance <= (min(thresholds) * 0.1):  # Within 10%
                similar_thresholds += len(group_alarms) - 1
                group_type = "Similar Threshold Alarms"
                severity = "medium"
                description = f"Alarms with similar thresholds (within 10% variance)"
            
            # Check for redundant actions
            action_sets = [set(alarm.get('alarmActions', [])) for alarm in group_alarms]
            if len(set(frozenset(actions) for actions in action_sets)) == 1:
                redundant_actions += len(group_alarms) - 1
                if group_type == "Similar Threshold Alarms":
                    group_type = "Redundant Alarms"
                    severity = "high"
                    description = f"Alarms with similar thresholds and identical actions"
            
            # Calculate potential savings (CloudWatch alarm costs ~$0.10/month per alarm)
            potential_savings = (len(group_alarms) - 1) * 0.10
            total_savings += potential_savings
            
            duplicate_groups.append({
                'type': group_type,
                'severity': severity,
                'description': description,
                'alarms': group_alarms,
                'potentialSavings': round(potential_savings, 2),
                'recommendation': generate_duplicate_recommendation(group_alarms)
            })
            
            total_duplicates += len(group_alarms) - 1
    
    # Look for cross-metric redundancies (e.g., CPU and Memory alarms on same instance)
    instance_groups = {}
    for alarm in alarms:
        if alarm.get('dimensions'):
            for dim in alarm['dimensions']:
                if dim['Name'] == 'InstanceId':
                    instance_id = dim['Value']
                    if instance_id not in instance_groups:
                        instance_groups[instance_id] = []
                    instance_groups[instance_id].append(alarm)
    
    for instance_id, instance_alarms in instance_groups.items():
        if len(instance_alarms) > 3:  # More than 3 alarms per instance might be excessive
            potential_savings = (len(instance_alarms) - 3) * 0.10
            total_savings += potential_savings
            
            duplicate_groups.append({
                'type': 'Excessive Alarms per Resource',
                'severity': 'low',
                'description': f'Instance {instance_id} has {len(instance_alarms)} alarms - consider consolidation',
                'alarms': instance_alarms,
                'potentialSavings': round(potential_savings, 2),
                'recommendation': 'Consider using composite alarms or reducing the number of individual alarms'
            })
    
    return {
        'duplicateGroups': duplicate_groups,
        'totalDuplicates': total_duplicates,
        'similarThresholds': similar_thresholds,
        'redundantActions': redundant_actions,
        'totalSavings': round(total_savings, 2)
    }

def generate_duplicate_recommendation(alarms):
    """Generate specific recommendations for duplicate alarm groups"""
    if len(alarms) <= 1:
        return "No action needed"
    
    recommendations = []
    
    # Analyze thresholds
    thresholds = [alarm['threshold'] for alarm in alarms]
    if len(set(thresholds)) > 1:
        recommendations.append(f"Keep alarm with threshold {min(thresholds)} (most sensitive)")
        recommendations.append(f"Remove alarms with higher thresholds: {', '.join(map(str, sorted(set(thresholds))[1:]))}")
    else:
        recommendations.append("Keep the alarm with the most descriptive name")
        recommendations.append("Remove duplicate alarms with identical thresholds")
    
    # Check for different comparison operators
    operators = set(alarm['comparisonOperator'] for alarm in alarms)
    if len(operators) > 1:
        recommendations.append("Consolidate to use consistent comparison operators")
    
    # Action recommendations
    recommendations.append("Verify all alarms have the same notification actions")
    recommendations.append("Consider using composite alarms for complex monitoring scenarios")
    
    return recommendations

if __name__ == '__main__':
    print("🌟 Starting AWS Cost Optimization Tool...")
    print("📍 Server running at: http://127.0.0.1:5000")
    print("🎯 Dashboard URL: http://127.0.0.1:5000/dashboard")
    print("🔧 EC2 Dashboard: http://127.0.0.1:5000/ec2")
    print("⚙️  Debug mode: ON")
    print("=" * 50)
    
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
