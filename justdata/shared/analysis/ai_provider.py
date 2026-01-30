#!/usr/bin/env python3
"""
AI analysis utilities for data analysis using GPT-4 and Claude.
Shared across BranchSight, BizSight, and LendSight.
"""

import sys
import os
import json
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime

# =============================================================================
# AI USAGE TRACKING
# =============================================================================
# Pricing per 1M tokens (as of Jan 2026)
AI_PRICING = {
    'claude-sonnet-4-20250514': {'input': 3.00, 'output': 15.00},
    'claude-3-5-sonnet-20241022': {'input': 3.00, 'output': 15.00},
    'claude-3-opus-20240229': {'input': 15.00, 'output': 75.00},
    'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25},
    'gpt-4': {'input': 30.00, 'output': 60.00},
    'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
    'gpt-4o': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
}

# In-memory usage accumulator (flushed to BigQuery periodically)
_ai_usage_buffer = []
_last_flush_time = None


def log_ai_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    app_name: str = None,
    report_type: str = None
) -> dict:
    """
    Log AI API usage for cost tracking.
    
    Args:
        provider: 'claude' or 'openai'
        model: Model name used
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        app_name: Application that made the call (e.g., 'lendsight', 'bizsight')
        report_type: Type of report being generated
    
    Returns:
        dict with usage details and estimated cost
    """
    # Calculate cost
    pricing = AI_PRICING.get(model, {'input': 10.0, 'output': 30.0})  # Default to GPT-4 pricing
    input_cost = (input_tokens / 1_000_000) * pricing['input']
    output_cost = (output_tokens / 1_000_000) * pricing['output']
    total_cost = input_cost + output_cost
    
    usage_record = {
        'timestamp': datetime.utcnow().isoformat(),
        'provider': provider,
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'input_cost_usd': round(input_cost, 6),
        'output_cost_usd': round(output_cost, 6),
        'total_cost_usd': round(total_cost, 6),
        'app_name': app_name or 'unknown',
        'report_type': report_type or 'unknown'
    }
    
    # Add to buffer
    _ai_usage_buffer.append(usage_record)
    
    # Log to console for debugging
    print(f"[AI Usage] {provider}/{model}: {input_tokens}+{output_tokens} tokens = ${total_cost:.4f}")
    
    # Flush to BigQuery immediately (was 10, but data was lost on app restart)
    _flush_ai_usage_to_bigquery()
    
    return usage_record


def _flush_ai_usage_to_bigquery():
    """Flush accumulated AI usage to BigQuery."""
    global _ai_usage_buffer, _last_flush_time
    
    if not _ai_usage_buffer:
        return
    
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        
        # Get credentials
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            creds_dict = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            client = bigquery.Client(project='justdata-ncrc', credentials=credentials)
        else:
            client = bigquery.Client(project='justdata-ncrc')
        
        # Create table if it doesn't exist
        table_id = 'justdata-ncrc.firebase_analytics.ai_usage'
        
        try:
            client.get_table(table_id)
        except Exception:
            # Table doesn't exist, create it
            schema = [
                bigquery.SchemaField("timestamp", "STRING"),
                bigquery.SchemaField("provider", "STRING"),
                bigquery.SchemaField("model", "STRING"),
                bigquery.SchemaField("input_tokens", "INTEGER"),
                bigquery.SchemaField("output_tokens", "INTEGER"),
                bigquery.SchemaField("total_tokens", "INTEGER"),
                bigquery.SchemaField("input_cost_usd", "FLOAT"),
                bigquery.SchemaField("output_cost_usd", "FLOAT"),
                bigquery.SchemaField("total_cost_usd", "FLOAT"),
                bigquery.SchemaField("app_name", "STRING"),
                bigquery.SchemaField("report_type", "STRING"),
            ]
            table = bigquery.Table(table_id, schema=schema)
            client.create_table(table)
            print(f"[AI Usage] Created table {table_id}")
        
        # Insert rows
        rows_to_insert = _ai_usage_buffer.copy()
        print(f"[AI Usage] Attempting to insert {len(rows_to_insert)} rows to {table_id}")
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if errors:
            print(f"[AI Usage] BigQuery insert errors: {errors}")
        else:
            print(f"[AI Usage] SUCCESS: Flushed {len(rows_to_insert)} records to BigQuery")
            _ai_usage_buffer = []
            _last_flush_time = datetime.utcnow()
            
    except Exception as e:
        # Don't fail the main operation if logging fails
        print(f"[AI Usage] Failed to flush to BigQuery: {e}")


def get_ai_usage_summary(days: int = 30) -> dict:
    """Get AI usage summary from BigQuery ai_usage table."""
    # #region agent log
    print(f"[AI Usage Summary] ENTRY days={days}")
    # #endregion
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        # #region agent log
        print(f"[AI Usage Summary] CREDS_CHECK has_creds={creds_json is not None} len={len(creds_json) if creds_json else 0}")
        # #endregion
        if creds_json:
            creds_dict = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            client = bigquery.Client(project='justdata-ncrc', credentials=credentials)
        else:
            client = bigquery.Client(project='justdata-ncrc')
        
        # Query the actual ai_usage table where log_ai_usage() writes to
        query = f"""
        SELECT
            app_name,
            model,
            provider,
            COUNT(*) as request_count,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            SUM(total_tokens) as total_tokens,
            SUM(total_cost_usd) as total_cost_usd
        FROM `justdata-ncrc.firebase_analytics.ai_usage`
        WHERE TIMESTAMP(timestamp) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY app_name, model, provider
        ORDER BY total_cost_usd DESC
        """
        
        results = list(client.query(query).result())
        # #region agent log
        print(f"[AI Usage Summary] QUERY_RESULTS count={len(results)} first={dict(results[0]) if results else None}")
        # Check total count in table (all time)
        try:
            count_query = "SELECT COUNT(*) as total FROM `justdata-ncrc.firebase_analytics.ai_usage`"
            count_result = list(client.query(count_query).result())
            total_all_time = count_result[0].total if count_result else 0
            print(f"[AI Usage Summary] TABLE_TOTAL_ROWS all_time={total_all_time}")
        except Exception as ce:
            print(f"[AI Usage Summary] TABLE_COUNT_ERROR {ce}")
        # #endregion
        
        total_cost = sum(r.total_cost_usd or 0 for r in results)
        total_requests = sum(r.request_count or 0 for r in results)
        total_tokens = sum(r.total_tokens or 0 for r in results)
        
        by_app = {}
        by_model = {}
        for r in results:
            app = r.app_name or 'unknown'
            model = r.model or 'unknown'
            
            if app not in by_app:
                by_app[app] = {'requests': 0, 'tokens': 0, 'cost_usd': 0}
            by_app[app]['requests'] += r.request_count or 0
            by_app[app]['tokens'] += r.total_tokens or 0
            by_app[app]['cost_usd'] += r.total_cost_usd or 0
            
            if model not in by_model:
                by_model[model] = {'requests': 0, 'tokens': 0, 'cost_usd': 0, 'provider': r.provider}
            by_model[model]['requests'] += r.request_count or 0
            by_model[model]['tokens'] += r.total_tokens or 0
            by_model[model]['cost_usd'] += r.total_cost_usd or 0
        
        # Convert by_model dict to list for frontend
        by_model_list = [
            {'model': k, **v} for k, v in by_model.items()
        ]
        
        # #region agent log - diagnostic: check total rows in table
        total_all_time = 0
        try:
            count_query = "SELECT COUNT(*) as total FROM `justdata-ncrc.firebase_analytics.ai_usage`"
            count_result = list(client.query(count_query).result())
            total_all_time = count_result[0].total if count_result else 0
        except:
            pass
        # #endregion
        
        return {
            'period_days': days,
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 4),
            'by_app': by_app,
            'by_model': by_model_list,
            '_debug_table_total_rows': total_all_time  # diagnostic
        }
    except Exception as e:
        import traceback as _tb
        # #region agent log
        print(f"[AI Usage Summary] EXCEPTION error={str(e)[:300]}")
        print(f"[AI Usage Summary] TRACEBACK {_tb.format_exc()[:500]}")
        # #endregion
        return {
            'period_days': days,
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost_usd': 0,
            'by_app': {},
            'by_model': [],
            'error': str(e)
        }

def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        # Convert dictionary, ensuring keys are strings (JSON requirement)
        # and values are properly converted
        # CRITICAL: JSON requires ALL keys to be strings to avoid comparison errors
        result = {}
        for key, value in obj.items():
            # Convert key to string if it's not already a string (JSON requires string keys)
            if isinstance(key, str):
                key_str = key
            elif isinstance(key, (int, np.integer)):
                key_str = str(int(key))
            elif isinstance(key, (float, np.floating)):
                key_str = str(float(key))
            elif isinstance(key, bool):
                key_str = str(key)
            else:
                # For any other type, convert to string
                key_str = str(key)
            result[key_str] = convert_numpy_types(value)
        return result
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        # Already a native Python type
        return obj
    else:
        # For any other type, try to convert to string as fallback
        try:
            # If it's a numeric type, try to convert
            if hasattr(obj, '__int__'):
                return int(obj)
            elif hasattr(obj, '__float__'):
                return float(obj)
        except:
            pass
        return obj

def ask_ai(
    prompt: str, 
    ai_provider: str = "claude", 
    model: str = None, 
    api_key: str = None,
    app_name: str = None,
    report_type: str = None
) -> str:
    """
    Send a prompt to the configured AI provider and return the response.
    
    Args:
        prompt: The prompt to send
        ai_provider: 'claude' or 'openai'
        model: Specific model to use (optional)
        api_key: API key (optional, defaults to env var)
        app_name: Application name for usage tracking
        report_type: Report type for usage tracking
    
    Returns:
        The AI response text
    """
    if not api_key:
        # Check both CLAUDE_API_KEY and ANTHROPIC_API_KEY for compatibility
        if ai_provider == "claude":
            api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        else:
            api_key = os.getenv("OPENAI_API_KEY")

    # Strip any whitespace/newlines from API key (prevents "Illegal header value" errors)
    if api_key:
        api_key = api_key.strip()

    if not api_key:
        raise Exception(f"No API key found for provider: {ai_provider}")
    
    try:
        if ai_provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            if not model:
                model = "gpt-4"
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Log usage
            if hasattr(response, 'usage') and response.usage:
                log_ai_usage(
                    provider='openai',
                    model=model,
                    input_tokens=response.usage.prompt_tokens or 0,
                    output_tokens=response.usage.completion_tokens or 0,
                    app_name=app_name,
                    report_type=report_type
                )
            
            return response.choices[0].message.content
            
        elif ai_provider == "claude":
            try:
                import anthropic
            except ImportError:
                raise Exception("anthropic module not installed. Install it with: pip install anthropic")
            client = anthropic.Anthropic(api_key=api_key)
            if not model:
                model = "claude-sonnet-4-20250514"
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Log usage
            if hasattr(response, 'usage') and response.usage:
                log_ai_usage(
                    provider='claude',
                    model=model,
                    input_tokens=response.usage.input_tokens or 0,
                    output_tokens=response.usage.output_tokens or 0,
                    app_name=app_name,
                    report_type=report_type
                )
            
            return response.content[0].text
        else:
            raise Exception(f"Unsupported AI provider: {ai_provider}")
    except Exception as e:
        raise Exception(f"Error calling {ai_provider.upper()} API: {e}")


class AIAnalyzer:
    """Base AI analyzer class for all applications."""
    
    def __init__(self, ai_provider: str = "claude", model: str = None, api_key: str = None):
        self.provider = ai_provider
        self.model = model
        if ai_provider == "claude":
            # Check both CLAUDE_API_KEY and ANTHROPIC_API_KEY for compatibility
            self.api_key = api_key or os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        # Strip any whitespace/newlines from API key (prevents "Illegal header value" errors)
        if self.api_key:
            self.api_key = self.api_key.strip()

        if not self.api_key:
            raise Exception(f"No API key found for provider: {ai_provider}")
        
        # Set default models
        if not self.model:
            self.model = "claude-sonnet-4-20250514" if ai_provider == "claude" else "gpt-4"
        
    def _call_ai(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.3, 
                  app_name: str = None, report_type: str = None) -> str:
        """Make a call to the configured AI provider with usage tracking."""
        try:
            if self.provider == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                # Log usage
                if hasattr(response, 'usage') and response.usage:
                    log_ai_usage(
                        provider='openai',
                        model=self.model,
                        input_tokens=response.usage.prompt_tokens or 0,
                        output_tokens=response.usage.completion_tokens or 0,
                        app_name=app_name or getattr(self, 'app_name', None),
                        report_type=report_type
                    )
                
                return response.choices[0].message.content.strip()
                
            elif self.provider == "claude":
                try:
                    import anthropic
                except ImportError:
                    raise Exception("anthropic module not installed. Install it with: pip install anthropic")
                client = anthropic.Anthropic(api_key=self.api_key)
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Log usage
                if hasattr(response, 'usage') and response.usage:
                    log_ai_usage(
                        provider='claude',
                        model=self.model,
                        input_tokens=response.usage.input_tokens or 0,
                        output_tokens=response.usage.output_tokens or 0,
                        app_name=app_name or getattr(self, 'app_name', None),
                        report_type=report_type
                    )
                
                return response.content[0].text.strip()
        except Exception as e:
            error_msg = f"Error calling {self.provider} API: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            # Re-raise the exception so calling code can handle it
            raise Exception(error_msg) from e
        
    def generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Generate an executive summary of the analysis."""
        raise NotImplementedError("Subclasses must implement generate_executive_summary")
        
    def generate_key_findings(self, data: Dict[str, Any]) -> str:
        """Generate key findings from the analysis."""
        raise NotImplementedError("Subclasses must implement generate_key_findings")
        
    def generate_trends_analysis(self, data: Dict[str, Any]) -> str:
        """Generate trends analysis."""
        raise NotImplementedError("Subclasses must implement generate_trends_analysis")

