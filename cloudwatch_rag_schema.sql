-- CloudWatch RAG Database Schema
-- This schema supports storing CloudWatch metrics, logs, and alarms for LLM querying

-- CloudWatch Metrics Table
CREATE TABLE IF NOT EXISTS cloudwatch_metrics (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    namespace VARCHAR(100) NOT NULL,  -- AWS/EC2, AWS/RDS, etc.
    metric_name VARCHAR(100) NOT NULL,  -- CPUUtilization, NetworkIn, etc.
    dimensions JSONB,  -- Instance ID, Volume ID, etc.
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(50),  -- Percent, Bytes, Count, etc.
    statistic VARCHAR(20),  -- Average, Maximum, Minimum, Sum
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_metrics_account_region (account_id, region),
    INDEX idx_metrics_namespace_metric (namespace, metric_name),
    INDEX idx_metrics_timestamp (timestamp),
    INDEX idx_metrics_dimensions USING GIN (dimensions)
);

-- CloudWatch Logs Table
CREATE TABLE IF NOT EXISTS cloudwatch_logs (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    log_group VARCHAR(255) NOT NULL,
    log_stream VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    message TEXT NOT NULL,
    log_level VARCHAR(20),  -- ERROR, WARN, INFO, DEBUG
    source_ip INET,
    user_agent TEXT,
    request_id VARCHAR(100),
    duration_ms INTEGER,
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Full-text search index
    INDEX idx_logs_message_fts USING GIN (to_tsvector('english', message)),
    INDEX idx_logs_account_region (account_id, region),
    INDEX idx_logs_log_group (log_group),
    INDEX idx_logs_timestamp (timestamp),
    INDEX idx_logs_level (log_level)
);

-- CloudWatch Alarms Table (Enhanced)
CREATE TABLE IF NOT EXISTS cloudwatch_alarms (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    alarm_name VARCHAR(255) NOT NULL,
    alarm_description TEXT,
    metric_name VARCHAR(100) NOT NULL,
    namespace VARCHAR(100) NOT NULL,
    dimensions JSONB,
    statistic VARCHAR(20),
    period INTEGER,  -- in seconds
    evaluation_periods INTEGER,
    threshold DOUBLE PRECISION,
    comparison_operator VARCHAR(50),  -- GreaterThanThreshold, etc.
    state VARCHAR(20),  -- OK, ALARM, INSUFFICIENT_DATA
    state_reason TEXT,
    state_updated_timestamp TIMESTAMP WITH TIME ZONE,
    alarm_actions JSONB,  -- SNS topics, Auto Scaling actions, etc.
    ok_actions JSONB,
    treat_missing_data VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_alarms_account_region (account_id, region),
    INDEX idx_alarms_state (state),
    INDEX idx_alarms_metric (namespace, metric_name),
    INDEX idx_alarms_dimensions USING GIN (dimensions)
);

-- CloudWatch Insights Queries (for caching common queries)
CREATE TABLE IF NOT EXISTS cloudwatch_insights_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,  -- MD5 of normalized query
    natural_language_query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    result_data JSONB,
    account_id VARCHAR(50) NOT NULL,
    region VARCHAR(50),
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    INDEX idx_insights_hash (query_hash),
    INDEX idx_insights_account (account_id),
    INDEX idx_insights_expires (expires_at)
);

-- Resource Metadata (for context in queries)
CREATE TABLE IF NOT EXISTS aws_resources (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,  -- EC2, RDS, Lambda, etc.
    resource_id VARCHAR(255) NOT NULL,
    resource_name VARCHAR(255),
    tags JSONB,
    state VARCHAR(50),  -- running, stopped, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_resource (account_id, region, resource_type, resource_id),
    INDEX idx_resources_account_region (account_id, region),
    INDEX idx_resources_type (resource_type),
    INDEX idx_resources_tags USING GIN (tags)
);

-- LLM Query History (for learning and improvement)
CREATE TABLE IF NOT EXISTS llm_query_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    session_id VARCHAR(100),
    natural_language_query TEXT NOT NULL,
    generated_sql TEXT,
    sql_execution_success BOOLEAN,
    sql_execution_error TEXT,
    result_count INTEGER,
    llm_response TEXT,
    user_feedback INTEGER,  -- 1-5 rating
    feedback_comment TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_query_history_user (user_id),
    INDEX idx_query_history_session (session_id),
    INDEX idx_query_history_created (created_at)
);

-- Views for common queries
CREATE VIEW cloudwatch_metrics_summary AS
SELECT 
    account_id,
    region,
    namespace,
    metric_name,
    datetime(timestamp, 'start of hour') as hour,
    AVG(value) as avg_value,
    MAX(value) as max_value,
    MIN(value) as min_value,
    COUNT(*) as data_points
FROM cloudwatch_metrics
GROUP BY account_id, region, namespace, metric_name, datetime(timestamp, 'start of hour');

CREATE VIEW recent_alarms AS
SELECT 
    account_id,
    region,
    alarm_name,
    state,
    state_reason,
    metric_name,
    namespace,
    state_updated_timestamp
FROM cloudwatch_alarms
WHERE state_updated_timestamp >= datetime('now', '-24 hours')
ORDER BY state_updated_timestamp DESC;

CREATE VIEW error_logs_summary AS
SELECT 
    account_id,
    region,
    log_group,
    datetime(timestamp, 'start of hour') as hour,
    COUNT(*) as error_count,
    COUNT(DISTINCT log_stream) as affected_streams
FROM cloudwatch_logs
WHERE log_level IN ('ERROR', 'FATAL')
GROUP BY account_id, region, log_group, datetime(timestamp, 'start of hour')
HAVING COUNT(*) > 0
ORDER BY hour DESC;
