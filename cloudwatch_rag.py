"""
CloudWatch RAG (Retrieval-Augmented Generation) System
Enables natural language querying of CloudWatch data using LLM
"""

import os
import re
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import google.generativeai as genai
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Result of a natural language query"""
    success: bool
    sql_query: str
    data: List[Dict]
    summary: str
    execution_time_ms: int
    error: Optional[str] = None

class CloudWatchRAG:
    """Main RAG system for CloudWatch data analysis"""
    
    def __init__(self, db_path: str = "cloudleakage.db", gemini_api_key: str = None):
        self.db_path = db_path
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning("No Gemini API key provided. Using mock responses.")
            self.model = None
        
        self.schema_context = self._load_schema_context()
        
    def _load_schema_context(self) -> str:
        """Load database schema context for LLM"""
        return """
        Database Schema for CloudWatch Data:
        
        1. cloudwatch_metrics: Stores time-series metrics data
           - account_id, region, namespace, metric_name
           - dimensions (JSONB): resource identifiers
           - timestamp, value, unit, statistic
           
        2. cloudwatch_logs: Stores log entries
           - account_id, region, log_group, log_stream
           - timestamp, message, log_level
           - source_ip, user_agent, request_id, duration_ms, status_code
           
        3. cloudwatch_alarms: Stores alarm configurations and states
           - account_id, region, alarm_name, state
           - metric_name, namespace, threshold, comparison_operator
           - alarm_actions, state_reason
           
        4. aws_resources: Resource metadata for context
           - account_id, region, resource_type, resource_id
           - resource_name, tags, state
           
        Common Queries:
        - CPU usage: SELECT * FROM cloudwatch_metrics WHERE metric_name = 'CPUUtilization'
        - Error logs: SELECT * FROM cloudwatch_logs WHERE log_level = 'ERROR'
        - Active alarms: SELECT * FROM cloudwatch_alarms WHERE state = 'ALARM'
        """
    
    def query(self, natural_language_query: str, account_id: str = None, region: str = None) -> QueryResult:
        """
        Process natural language query and return results
        """
        start_time = datetime.now()
        
        try:
            # Check cache first
            cached_result = self._check_cache(natural_language_query, account_id, region)
            if cached_result:
                return cached_result
            
            # Generate SQL query using LLM
            sql_query = self._generate_sql_query(natural_language_query, account_id, region)
            
            # Execute SQL query
            data = self._execute_sql_query(sql_query)
            
            # Generate natural language summary
            summary = self._generate_summary(natural_language_query, data, sql_query)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            result = QueryResult(
                success=True,
                sql_query=sql_query,
                data=data,
                summary=summary,
                execution_time_ms=execution_time
            )
            
            # Cache the result
            self._cache_result(natural_language_query, result, account_id, region)
            
            return result
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return QueryResult(
                success=False,
                sql_query="",
                data=[],
                summary=f"Query failed: {str(e)}",
                execution_time_ms=execution_time,
                error=str(e)
            )
    
    def _generate_sql_query(self, natural_query: str, account_id: str = None, region: str = None) -> str:
        """Generate SQL query from natural language using LLM"""
        
        # Add context filters
        context_filters = []
        if account_id:
            context_filters.append(f"account_id = '{account_id}'")
        if region:
            context_filters.append(f"region = '{region}'")
        
        context_clause = " AND ".join(context_filters) if context_filters else ""
        
        prompt = f"""
        You are a SQL expert analyzing AWS CloudWatch data. Generate a SQL query based on the user's natural language request.
        
        {self.schema_context}
        
        User Query: "{natural_query}"
        
        Context Filters: {context_clause}
        
        Rules:
        1. Always include WHERE clauses for account_id and region if provided
        2. Use appropriate time ranges (last 24 hours, last week, etc.) based on context
        3. Use LIMIT to prevent excessive results (max 1000 rows)
        4. For time-based queries, use timestamp columns
        5. For log analysis, use log_level and message columns
        6. For metrics, use namespace, metric_name, and value columns
        7. Return only the SQL query, no explanations
        
        SQL Query:
        """
        
        if self.model:
            try:
                response = self.model.generate_content(prompt)
                sql_query = response.text.strip()
                
                # Clean up the SQL query
                sql_query = re.sub(r'^```sql\s*', '', sql_query, flags=re.IGNORECASE)
                sql_query = re.sub(r'\s*```$', '', sql_query)
                sql_query = sql_query.strip()
                
                # Add context filters if not present
                if context_clause and "WHERE" not in sql_query.upper():
                    sql_query = sql_query.rstrip(';') + f" WHERE {context_clause};"
                elif context_clause and "WHERE" in sql_query.upper():
                    sql_query = sql_query.rstrip(';') + f" AND {context_clause};"
                
                return sql_query
                
            except Exception as e:
                logger.error(f"LLM query generation failed: {e}")
                return self._fallback_sql_query(natural_query, account_id, region)
        else:
            return self._fallback_sql_query(natural_query, account_id, region)
    
    def _fallback_sql_query(self, natural_query: str, account_id: str = None, region: str = None) -> str:
        """Fallback SQL generation using pattern matching"""
        query_lower = natural_query.lower()
        
        # Build WHERE clause
        where_clauses = []
        if account_id:
            where_clauses.append(f"account_id = '{account_id}'")
        if region:
            where_clauses.append(f"region = '{region}'")
        
        # Time range detection
        if "last 24 hours" in query_lower or "today" in query_lower:
            where_clauses.append("timestamp >= datetime('now', '-24 hours')")
        elif "last week" in query_lower:
            where_clauses.append("timestamp >= datetime('now', '-7 days')")
        elif "last hour" in query_lower:
            where_clauses.append("timestamp >= datetime('now', '-1 hour')")
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Pattern matching for common queries
        if any(word in query_lower for word in ["cpu", "utilization"]):
            return f"SELECT * FROM cloudwatch_metrics WHERE metric_name = 'CPUUtilization'{' AND ' + ' AND '.join(where_clauses) if where_clauses else ''} ORDER BY timestamp DESC LIMIT 100;"
        
        elif any(word in query_lower for word in ["error", "errors"]):
            return f"SELECT * FROM cloudwatch_logs WHERE log_level = 'ERROR'{' AND ' + ' AND '.join(where_clauses) if where_clauses else ''} ORDER BY timestamp DESC LIMIT 100;"
        
        elif any(word in query_lower for word in ["alarm", "alarms"]):
            return f"SELECT * FROM cloudwatch_alarms WHERE state = 'ALARM'{' AND ' + ' AND '.join(where_clauses) if where_clauses else ''} ORDER BY state_updated_timestamp DESC LIMIT 100;"
        
        else:
            # Default to recent metrics
            return f"SELECT * FROM cloudwatch_metrics{where_clause} ORDER BY timestamp DESC LIMIT 100;"
    
    def _execute_sql_query(self, sql_query: str) -> List[Dict]:
        """Execute SQL query and return results"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            data = [dict(row) for row in rows]
            
            conn.close()
            return data
            
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise e
    
    def _generate_summary(self, natural_query: str, data: List[Dict], sql_query: str) -> str:
        """Generate natural language summary of results"""
        
        if not data:
            return "No data found matching your query."
        
        data_summary = {
            "total_records": len(data),
            "sample_data": data[:3] if len(data) > 3 else data,
            "columns": list(data[0].keys()) if data else []
        }
        
        prompt = f"""
        Analyze the following CloudWatch data and provide a concise, insightful summary.
        
        Original Query: "{natural_query}"
        SQL Query Used: {sql_query}
        
        Data Summary:
        - Total Records: {data_summary['total_records']}
        - Columns: {', '.join(data_summary['columns'])}
        - Sample Data: {json.dumps(data_summary['sample_data'], indent=2, default=str)}
        
        Provide a clear, actionable summary in 2-3 sentences. Focus on:
        1. Key findings and trends
        2. Notable anomalies or issues
        3. Recommendations if applicable
        
        Summary:
        """
        
        if self.model:
            try:
                response = self.model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.error(f"Summary generation failed: {e}")
                return self._fallback_summary(data_summary)
        else:
            return self._fallback_summary(data_summary)
    
    def _fallback_summary(self, data_summary: Dict) -> str:
        """Fallback summary generation"""
        total = data_summary['total_records']
        
        if total == 0:
            return "No data found matching your criteria."
        elif total == 1:
            return f"Found 1 record matching your query."
        else:
            return f"Found {total} records matching your query. The data includes {', '.join(data_summary['columns'][:3])} and other metrics."
    
    def _check_cache(self, query: str, account_id: str = None, region: str = None) -> Optional[QueryResult]:
        """Check if query result is cached"""
        try:
            query_hash = self._generate_query_hash(query, account_id, region)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT generated_sql, result_data, execution_time_ms
                FROM cloudwatch_insights_cache 
                WHERE query_hash = ? AND expires_at > datetime('now')
            """, (query_hash,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                sql_query, result_data_json, execution_time = row
                result_data = json.loads(result_data_json)
                
                return QueryResult(
                    success=True,
                    sql_query=sql_query,
                    data=result_data.get('data', []),
                    summary=result_data.get('summary', ''),
                    execution_time_ms=execution_time
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Cache check failed: {e}")
            return None
    
    def _cache_result(self, query: str, result: QueryResult, account_id: str = None, region: str = None):
        """Cache query result"""
        try:
            query_hash = self._generate_query_hash(query, account_id, region)
            expires_at = datetime.now() + timedelta(hours=1)  # Cache for 1 hour
            
            result_data = {
                'data': result.data,
                'summary': result.summary
            }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO cloudwatch_insights_cache 
                (query_hash, natural_language_query, generated_sql, result_data, 
                 account_id, region, execution_time_ms, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_hash, query, result.sql_query, json.dumps(result_data, default=str),
                account_id, region, result.execution_time_ms, expires_at
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Cache storage failed: {e}")
    
    def _generate_query_hash(self, query: str, account_id: str = None, region: str = None) -> str:
        """Generate hash for query caching"""
        content = f"{query}|{account_id}|{region}"
        return hashlib.md5(content.encode()).hexdigest()

class CloudWatchDataIngestion:
    """Handles ingestion of CloudWatch data into the database"""
    
    def __init__(self, db_path: str = "cloudleakage.db"):
        self.db_path = db_path
    
    def ingest_metrics(self, metrics_data: List[Dict]):
        """Ingest CloudWatch metrics data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for metric in metrics_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO cloudwatch_metrics 
                    (account_id, region, namespace, metric_name, dimensions, 
                     timestamp, value, unit, statistic)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric['account_id'], metric['region'], metric['namespace'],
                    metric['metric_name'], json.dumps(metric.get('dimensions', {})),
                    metric['timestamp'], metric['value'], 
                    metric.get('unit'), metric.get('statistic', 'Average')
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"Ingested {len(metrics_data)} metrics")
            
        except Exception as e:
            logger.error(f"Metrics ingestion failed: {e}")
    
    def ingest_logs(self, logs_data: List[Dict]):
        """Ingest CloudWatch logs data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for log in logs_data:
                cursor.execute("""
                    INSERT INTO cloudwatch_logs 
                    (account_id, region, log_group, log_stream, timestamp, 
                     message, log_level, source_ip, request_id, duration_ms, status_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log['account_id'], log['region'], log['log_group'],
                    log['log_stream'], log['timestamp'], log['message'],
                    log.get('log_level'), log.get('source_ip'),
                    log.get('request_id'), log.get('duration_ms'), log.get('status_code')
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"Ingested {len(logs_data)} log entries")
            
        except Exception as e:
            logger.error(f"Logs ingestion failed: {e}")
