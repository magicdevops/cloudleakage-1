# CloudWatch RAG (Retrieval-Augmented Generation) System

## 🧠 Overview

The CloudWatch RAG system enables **natural language querying** of AWS CloudWatch data using Large Language Models (LLM). Users can ask questions in plain English and get intelligent insights from their CloudWatch metrics, logs, and alarms.

### Key Features

- **Natural Language Interface**: Ask questions like "Show me CPU usage for the last 24 hours"
- **AI-Powered Analysis**: Uses Google's Gemini Pro LLM for intelligent query processing
- **SQL Generation**: Automatically converts natural language to optimized SQL queries
- **Real-time Data**: Queries live CloudWatch data stored in your database
- **Intelligent Caching**: Caches results for improved performance
- **Export Capabilities**: Export results to CSV for further analysis

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Query    │───▶│   CloudWatch     │───▶│   Database      │
│ "Show CPU usage"│    │   RAG System     │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          ▲
                              ▼                          │
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Gemini Pro     │    │   Data          │
                       │   LLM            │    │   Ingestion     │
                       └──────────────────┘    └─────────────────┘
                              │                          ▲
                              ▼                          │
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Generated      │    │   AWS           │
                       │   SQL Query      │    │   CloudWatch    │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Initialize the System

```bash
cd /home/ubuntu/LocalAWS_CodeBuild/repos/cloudleakage
python init_cloudwatch_rag.py
```

### 2. Configure API Keys

Edit the `.env` file and add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key from: https://makersuite.google.com/app/apikey

### 3. Start the Application

```bash
python app.py
```

### 4. Access CloudWatch Insights

Visit: http://localhost:5000/cloudwatch/insights

### 5. Load Sample Data (for testing)

Click the "Load Sample Data" button to populate the database with sample CloudWatch data.

## 📊 Database Schema

### Core Tables

#### `cloudwatch_metrics`
Stores time-series metrics data from CloudWatch.

```sql
- account_id: AWS account identifier
- region: AWS region
- namespace: AWS service namespace (AWS/EC2, AWS/RDS, etc.)
- metric_name: Metric name (CPUUtilization, NetworkIn, etc.)
- dimensions: JSON object with resource identifiers
- timestamp: When the metric was recorded
- value: Metric value
- unit: Unit of measurement
- statistic: Aggregation type (Average, Maximum, etc.)
```

#### `cloudwatch_logs`
Stores log entries from CloudWatch Logs.

```sql
- account_id: AWS account identifier
- region: AWS region
- log_group: CloudWatch log group name
- log_stream: CloudWatch log stream name
- timestamp: Log entry timestamp
- message: Log message content
- log_level: Log level (ERROR, WARN, INFO, DEBUG)
- request_id: Request identifier for correlation
```

#### `cloudwatch_alarms`
Stores CloudWatch alarm configurations and states.

```sql
- account_id: AWS account identifier
- region: AWS region
- alarm_name: Alarm name
- state: Current alarm state (OK, ALARM, INSUFFICIENT_DATA)
- metric_name: Associated metric name
- threshold: Alarm threshold value
- comparison_operator: Comparison logic
```

## 🔍 Example Queries

### Performance Analysis
- "Show me CPU utilization for the last 24 hours"
- "What instances had high CPU usage today?"
- "Find servers with CPU above 80% in the last hour"
- "Show memory usage trends for the last week"

### Error Analysis
- "Show me all error logs from today"
- "What are the most common errors in the last week?"
- "Find database connection errors in the last 24 hours"
- "Show me failed API requests with status code 500"

### Alarm Management
- "Show me all active alarms"
- "What alarms triggered in the last hour?"
- "List all critical alarms for production instances"
- "Find alarms that have been in ALARM state for more than 1 hour"

### Trend Analysis
- "Compare CPU usage between today and yesterday"
- "What's the average response time for my API?"
- "Show network traffic patterns for the last week"
- "Find instances with increasing error rates"

## 🛠️ API Endpoints

### `/cloudwatch/api/query` (POST)
Process natural language queries.

**Request:**
```json
{
  "query": "Show me CPU utilization for the last 24 hours",
  "account_id": "123456789012",
  "region": "us-east-1"
}
```

**Response:**
```json
{
  "success": true,
  "query": "Show me CPU utilization for the last 24 hours",
  "sql_query": "SELECT * FROM cloudwatch_metrics WHERE metric_name = 'CPUUtilization' AND timestamp >= datetime('now', '-24 hours')",
  "data": [...],
  "summary": "Found 245 CPU utilization data points over the last 24 hours. Average CPU usage was 45.2% with peaks reaching 89% during business hours.",
  "execution_time_ms": 156,
  "data_count": 245
}
```

### `/cloudwatch/api/ingest-sample-data` (POST)
Load sample data for testing.

### `/cloudwatch/api/query-examples` (GET)
Get example queries organized by category.

## 🔧 Configuration

### Environment Variables

```env
# Required: Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Database path
DATABASE_PATH=cloudleakage.db

# Optional: AWS credentials for data ingestion
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### Caching Configuration

The system automatically caches query results for 1 hour to improve performance. Cache settings can be modified in `cloudwatch_rag.py`:

```python
expires_at = datetime.now() + timedelta(hours=1)  # Adjust cache duration
```

## 📈 Data Ingestion

### Real-time Data Ingestion

To ingest real CloudWatch data, use the `CloudWatchDataIngestion` class:

```python
from cloudwatch_rag import CloudWatchDataIngestion

ingestion = CloudWatchDataIngestion()

# Ingest metrics
metrics_data = [
    {
        'account_id': '123456789012',
        'region': 'us-east-1',
        'namespace': 'AWS/EC2',
        'metric_name': 'CPUUtilization',
        'dimensions': {'InstanceId': 'i-1234567890abcdef0'},
        'timestamp': '2024-01-01T12:00:00Z',
        'value': 75.5,
        'unit': 'Percent',
        'statistic': 'Average'
    }
]

ingestion.ingest_metrics(metrics_data)
```

### AWS Integration

For production use, set up automated data ingestion from AWS CloudWatch:

1. **Lambda Function**: Create a Lambda function to periodically fetch CloudWatch data
2. **EventBridge**: Schedule regular data collection
3. **Kinesis**: Stream real-time log data
4. **CloudWatch API**: Use boto3 to fetch metrics and logs

Example Lambda function:

```python
import boto3
from cloudwatch_rag import CloudWatchDataIngestion

def lambda_handler(event, context):
    cloudwatch = boto3.client('cloudwatch')
    ingestion = CloudWatchDataIngestion()
    
    # Fetch metrics
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        StartTime=datetime.now() - timedelta(hours=1),
        EndTime=datetime.now(),
        Period=300,
        Statistics=['Average']
    )
    
    # Transform and ingest data
    metrics_data = transform_cloudwatch_data(response)
    ingestion.ingest_metrics(metrics_data)
```

## 🧪 Testing

### Unit Tests

Run the test suite:

```bash
python -m pytest tests/test_cloudwatch_rag.py
```

### Manual Testing

1. Load sample data: Click "Load Sample Data" button
2. Try example queries from different categories
3. Test edge cases with complex queries
4. Verify SQL generation and execution
5. Check caching behavior

### Performance Testing

Monitor query performance:

```python
from cloudwatch_rag import CloudWatchRAG

rag = CloudWatchRAG()
result = rag.query("Show me CPU usage for the last hour")
print(f"Execution time: {result.execution_time_ms}ms")
```

## 🔒 Security Considerations

### API Key Security
- Store API keys in environment variables
- Use AWS Secrets Manager for production
- Rotate keys regularly

### Database Security
- Use proper database permissions
- Encrypt sensitive data
- Implement access controls

### Query Validation
- Sanitize user inputs
- Limit query complexity
- Implement rate limiting

## 🚀 Production Deployment

### Scaling Considerations

1. **Database**: Consider PostgreSQL for larger datasets
2. **Caching**: Use Redis for distributed caching
3. **Load Balancing**: Deploy multiple application instances
4. **Monitoring**: Set up application monitoring

### Performance Optimization

1. **Database Indexing**: Ensure proper indexes on timestamp and account_id columns
2. **Query Optimization**: Monitor slow queries and optimize
3. **Connection Pooling**: Use database connection pooling
4. **Async Processing**: Consider async query processing for complex queries

### Monitoring and Alerting

Set up monitoring for:
- Query response times
- Error rates
- Database performance
- API key usage limits
- Cache hit rates

## 🤝 Contributing

### Adding New Features

1. **New Query Types**: Extend the LLM prompts and SQL generation logic
2. **Additional Data Sources**: Add support for other AWS services
3. **Enhanced Analytics**: Implement more sophisticated analysis features
4. **UI Improvements**: Enhance the frontend interface

### Code Structure

```
cloudwatch_rag.py          # Core RAG system
app.py                     # Flask API endpoints
templates/                 # Frontend templates
cloudwatch_rag_schema.sql  # Database schema
init_cloudwatch_rag.py     # Initialization script
```

## 📚 Resources

- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [AWS CloudWatch API Reference](https://docs.aws.amazon.com/cloudwatch/latest/APIReference/)
- [SQLite Documentation](https://sqlite.org/docs.html)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 🐛 Troubleshooting

### Common Issues

**"No Gemini API key provided"**
- Solution: Add `GEMINI_API_KEY` to your `.env` file

**"Database table doesn't exist"**
- Solution: Run `python init_cloudwatch_rag.py`

**"Query generation failed"**
- Solution: Check your internet connection and API key validity

**"No data found"**
- Solution: Load sample data or ingest real CloudWatch data

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

- Check database indexes
- Monitor query complexity
- Verify cache configuration
- Review LLM response times

## 📄 License

This project is part of the CloudLeakage application and follows the same licensing terms.
