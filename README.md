# CloudLeakage - AWS Cost Optimization Tool

A comprehensive Flask-based web application for monitoring, analyzing, and optimizing AWS costs with professional CloudSpend-inspired UI and advanced multi-service AWS management.

## Features

### 🎯 Core Functionality
- **Real-time Cost Dashboard** - Monitor current and historical AWS spending with integrated CloudWatch alarms
- **EC2 Instance Management** - Comprehensive EC2 dashboard with real-time monitoring and cost optimization
- **CloudWatch Integration** - Complete CloudWatch alarms dashboard with state monitoring and export capabilities
- **Snapshot & AMI Management** - Advanced EBS snapshot and AMI monitoring with cost optimization recommendations
- **Cost Trend Analysis** - Visualize spending patterns with interactive charts
- **Service Breakdown** - Detailed cost analysis by AWS service
- **Optimization Recommendations** - Intelligent suggestions to reduce costs with potential savings calculations
- **Data Export** - Export EC2, snapshot, CloudWatch, and cost data in CSV, JSON, and Excel formats
- **Business Unit Management** - Organize costs by department/team
- **Account Integration** - Secure AWS account connection wizard with IAM role support
- **Terraform State Analyzer** - Visualize infrastructure from `terraform.tfstate` files

### 🔧 Technical Features
- **Professional UI** - CloudSpend/Site24x7 inspired modern interface
- **Multi-Database Support** - SQLite, PostgreSQL, MySQL compatibility
- **Encrypted Credentials** - Secure storage with Fernet encryption
- **Responsive Design** - Works seamlessly on desktop and mobile
- **Real-time Updates** - Auto-refreshing data and charts
- **Secure Integration** - IAM role-based AWS access
- **RESTful APIs** - JSON endpoints for data access

## Quick Start

### Prerequisites
- Python 3.8+
- AWS Account with appropriate permissions
- Modern web browser
- **Docker** (recommended for easy PostgreSQL setup)

### Installation

#### Option 1: Docker Setup (Recommended)
```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Start PostgreSQL with Docker
cd docker
docker-compose up -d postgres

# 3. Run application (connects to PostgreSQL automatically)
cd ..
python app.py
```

#### Option 2: Traditional Setup
```bash
# 1. Clone and Setup
cd /home/ubuntu/LocalAWS_CodeBuild/repos/cloudleakage
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Run the Application
python app.py
```

3. **Access the Dashboard**
- Open your browser to: http://127.0.0.1:5000
- Main Dashboard: http://127.0.0.1:5000/dashboard
- EC2 Dashboard: http://127.0.0.1:5000/ec2
- CloudWatch Dashboard: http://127.0.0.1:5000/cloudwatch
- Snapshots Dashboard: http://127.0.0.1:5000/snapshots

## 🗄️ Database Setup

CloudLeakage automatically detects and uses the best available database:

### PostgreSQL (Docker - Production & Development)
```bash
# 1. Start PostgreSQL container (recommended)
cd docker
docker-compose up -d postgres

# 2. Application automatically connects with these credentials:
# DATABASE_URL=postgresql://app_user:app_pass@localhost:5432/cloudleakage

# 3. Run application
cd ..
python app.py
```

**Database Connection:**
- **Host**: `localhost:5432`
- **Database**: `cloudleakage`
- **User**: `app_user`
- **Password**: `app_pass`

### SQLite (Development - No Setup Required)
```bash
# Application automatically creates cloudleakage.db
python app.py
```

### Database Schema
The application automatically creates these tables:
- **`cloud_accounts`** - Encrypted AWS credentials and account info
- **`cost_data`** - AWS cost and usage data
- **`sync_history`** - Synchronization operation tracking
- **`ec2_instances`** - EC2 instance data and metadata
- **`snapshots`** - EBS snapshot data and metadata
- **`volumes`** - EBS volume information and snapshot relationships

### Security Configuration
```bash
# Required for production
export ENCRYPTION_KEY="your-32-byte-base64-encoded-key"
export SECRET_KEY="your-flask-secret-key"

# Optional: Gemini API for Terraform Analyzer
export GEMINI_API_KEY="your-google-ai-studio-api-key"
```

## 🐳 Docker Setup

For the complete Docker and PostgreSQL setup guide, see:
- **`docker/README.md`** - Docker setup and management
- **`docs/DOCKER_POSTGRESQL_SETUP.md`** - Complete Docker deployment guide

### Quick Docker Commands
```bash
# Start PostgreSQL container
cd docker && docker-compose up -d postgres

# View logs
docker-compose logs -f postgres

# Stop database
docker-compose down postgres

# Run application (connects automatically)
cd .. && python app.py
```

## 📚 Documentation

For comprehensive documentation, see the `docs/` directory:
- **`docs/README.md`** - Complete documentation index
- **`docs/database_setup.md`** - Database configuration guide
- **`docs/aws_iam_permissions.md`** - AWS permissions and security
- **`docs/production_checklist.md`** - Production deployment guide

## Application Structure

```
cloudleakage/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .env.example                    # Environment configuration template
├── .gitignore                      # Git ignore patterns
├── setup_docker.sh                 # Docker setup script
├── setup_and_run.sh                # Traditional setup script
├── docker/                         # Docker configuration
│   ├── docker-compose.yml          # Docker services (PostgreSQL, Redis)
│   ├── Dockerfile                  # Application container definition
│   ├── README.md                   # Docker setup documentation
│   └── init-scripts/               # Database initialization scripts
├── docs/                           # Documentation directory
│   ├── README.md                   # Main documentation index
│   ├── DOCKER_POSTGRESQL_SETUP.md  # Complete Docker setup guide
│   ├── database_setup.md           # Database configuration
│   ├── aws_iam_permissions.md      # AWS permissions guide
│   └── [other documentation...]
├── cloudleakage.db                 # SQLite database (auto-created)
├── app/                            # Main application package
│   ├── __init__.py                 # Package initialization
│   ├── services/                   # Backend logic services
│   │   ├── __init__.py             # Services package init
│   │   ├── account_manager.py      # AWS account management
│   │   ├── ec2_service.py          # EC2 instance operations
│   │   ├── snapshot_service.py     # EBS snapshot operations
│   │   ├── simple_database.py      # Database management
│   │   └── terraform_analyzer.py   # Terraform state parsing logic
│   └── templates/                  # HTML templates
│       ├── layouts/                # Base layouts
│       ├── pages/                  # Main pages
│       ├── aws/                    # AWS service dashboards
│       │   ├── ec2/                # EC2 dashboard
│       │   ├── cloudwatch/         # CloudWatch dashboard
│       │   └── snapshots/          # Snapshots dashboard
│       ├── business_units/         # Business units pages
│       ├── integration/            # Account integration
│       ├── terraform/              # Terraform analyzer
│       └── errors/                 # Error pages
└── static/
    └── css/
        └── cloudspend-style.css    # Modern UI styling
```

## Key Pages

### 📊 Main Dashboard (`/dashboard`)
- Cost metrics cards with trend indicators
- Interactive cost trend chart
- CloudWatch alarms integration with export capabilities
- Top services breakdown
- Optimization recommendations
- Real-time data updates with account/region selectors

### 🖥️ EC2 Dashboard (`/ec2`)
- Real-time EC2 instance monitoring with cost optimization widgets
- Instance state management (running, stopped, pending)
- Comprehensive instance details with tags and AMI information
- Cost optimization recommendations with idle instance detection
- Monthly cost breakdown and potential savings analysis
- Data export (CSV, JSON, Excel formats)
- Multi-region support with 5-minute polling and caching
- Sync functionality for real-time updates

### ☁️ CloudWatch Dashboard (`/cloudwatch`)
- **Comprehensive Alarm Management** - Monitor all CloudWatch alarms across AWS regions
- **Alarm State Widgets** - Visual breakdown of alarm states (OK, ALARM, INSUFFICIENT_DATA)
- **Real-time Monitoring** - Live alarm status updates with color-coded indicators
- **Metric Insights** - Top resource usage and performance metrics
- **Export Capabilities** - Export alarm data in CSV, JSON, and Excel formats
- **Sync Functionality** - Manual and automatic data synchronization
- **Professional UI** - Consistent design matching EC2 and Snapshots dashboards

### 📸 Snapshots Dashboard (`/snapshots`)
- **EBS Snapshot & AMI Management** - Monitor all EBS snapshots and AMIs across AWS regions
- **Cost Optimization Engine** - Intelligent cleanup recommendations with potential savings calculations
- **Duplicate Detection** - Identify duplicate AMIs and recommend cleanup strategies
- **Enterprise-Style Widgets** - Professional metrics cards with meaningful icons
- **Comprehensive Export Options** - Export snapshot and AMI data in CSV, JSON, and Excel formats
- **Advanced Analysis** - Large AMI tracking, orphaned snapshot detection, storage cost breakdown
- **Cost Optimization Insights** - Identify old snapshots/AMIs (30, 60, 90+ days) for cleanup
- **Volume Relationship Tracking** - Monitor volumes with and without snapshots
- **Multi-Region Support** - Complete coverage of all 34 AWS regions
- **Real-Time Data Sync** - Automatic data refresh and synchronization with 5-minute caching

### 🏢 Business Units (`/business-units`)
- Cost allocation by department
- Resource tracking per unit
- Month-over-month comparisons
- Detailed cost breakdowns

### 🔗 Account Integration (`/integration`)
- Secure AWS account connection
- Step-by-step integration wizard
- IAM role setup guidance
- Connection status monitoring

### 🗺️ Terraform Analyzer (`/terraform`)
- Upload `terraform.tfstate` files to visualize your infrastructure
- View a network graph of resources and their dependencies
- Understand connections and relationships between components

## API Endpoints

### Cost Data
- `GET /api/cost-data` - Retrieve cost trend data
- `GET /api/recommendations` - Get optimization recommendations

### EC2 Management
- `GET /ec2/api/accounts/{id}/instances` - Get EC2 instances
- `GET /ec2/api/accounts/{id}/cost-optimization` - Get cost optimization recommendations
- `GET /ec2/api/analytics` - Get EC2 analytics data
- `POST /ec2/api/accounts/{id}/sync` - Sync EC2 data

### CloudWatch Management
- `GET /cloudwatch/api/accounts/{id}/alarms` - Get CloudWatch alarms
- `POST /cloudwatch/api/accounts/{id}/sync` - Sync CloudWatch data

### Snapshots & AMI Management
- `GET /snapshots/api/accounts/{id}/snapshots` - Get EBS snapshots
- `GET /snapshots/api/accounts/{id}/analysis` - Get snapshot analysis data
- `GET /snapshots/api/accounts/{id}/amis` - Get AMI analysis data
- `GET /snapshots/api/accounts/{id}/amis/list` - Get AMI list
- `GET /snapshots/api/accounts/{id}/cleanup-recommendations` - Get cleanup recommendations
- `GET /snapshots/api/accounts/{id}/cost-breakdown` - Get storage cost breakdown
- `GET /snapshots/api/accounts/{id}/volumes-without-snapshots` - Get volumes without snapshots
- `GET /snapshots/api/accounts/{id}/big-volume-snapshots` - Get large volume snapshots
- `POST /snapshots/api/accounts/{id}/sync` - Sync snapshot data

### Integration
- `POST /integration/api/accounts` - Create AWS account integration
- `POST /integration/api/policy/generate` - Generate IAM policy

### Terraform
- `POST /terraform/api/analyze` - Upload and analyze a `terraform.tfstate` file

## AWS Integration

The tool uses IAM roles for secure access to AWS Cost Explorer and other services:

### Required AWS Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues",
        "organizations:ListAccounts",
        "budgets:ViewBudget",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeRegions",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeSnapshots",
        "ec2:DescribeVolumes",
        "ec2:DescribeImages",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:ListMetrics",
        "pricing:GetProducts"
      ],
      "Resource": "*"
    }
  ]
}
```

## UI Design System

### Color Palette
- **Primary Blue**: `#1a73e8` - Main actions and highlights
- **Secondary Green**: `#34a853` - Success states and positive metrics
- **Warning Yellow**: `#fbbc04` - Warnings and attention items
- **Danger Red**: `#ea4335` - Errors and negative metrics

### Components
- **Metric Cards** - Key performance indicators with trend arrows
- **Charts** - Interactive Chart.js visualizations
- **Tables** - Responsive data tables with sorting
- **Navigation** - Fixed sidebar with section organization

## Development

### Adding New Features
1. Create service class in `app/services/` for backend logic
2. Create route in `app.py` and register service
3. Add template in `app/templates/`
4. Update navigation in sidebar
5. Add API endpoints if needed

### Architecture Overview
- **3-Tier Data Management**: Frontend (5min polling) → Memory Cache (5min TTL) → Database (persistent) → AWS API
- **Service Layer**: All backend logic organized in `app/services/` with proper class structure
- **Caching Strategy**: Intelligent caching with TTL management and manual sync capabilities
- **Consistent UI**: Unified design system across all AWS service dashboards

### Styling Guidelines
- Use CSS variables from `cloudspend-style.css`
- Follow existing component patterns
- Maintain responsive design principles
- Test on multiple screen sizes

## Production Deployment

### Environment Variables
```bash
export SECRET_KEY="your-production-secret-key"
export FLASK_ENV="production"
```

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Troubleshooting

### Common Issues
1. **Port 5000 in use**: Change port in `app.py` or kill existing process
2. **AWS permissions**: Ensure IAM role has required Cost Explorer permissions
3. **Missing dependencies**: Run `pip install -r requirements.txt`

### Debug Mode
The application runs in debug mode by default for development. Disable for production:
```python
app.run(debug=False)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Check the troubleshooting section
- Review AWS IAM permissions
- Ensure all dependencies are installed
- Verify Python version compatibility

---

**Built with ❤️ for AWS cost optimization**
