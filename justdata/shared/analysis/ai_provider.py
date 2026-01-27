#!/usr/bin/env python3
"""
AI analysis utilities for data analysis using GPT-4 and Claude.
Shared across BranchSight, BizSight, and LendSight.
"""

import sys
import os
import json
import numpy as np
from typing import List, Tuple, Dict, Any

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

def ask_ai(prompt: str, ai_provider: str = "claude", model: str = None, api_key: str = None) -> str:
    """Send a prompt to the configured AI provider and return the response."""
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
        
    def _call_ai(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> str:
        """Make a call to the configured AI provider."""
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

