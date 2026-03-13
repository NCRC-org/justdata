#!/usr/bin/env python3
"""
AI Provider for BizSight
AI analysis utilities using Claude and OpenAI.
"""

import os
import json
import numpy as np
from typing import Dict, Any


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


class AIAnalyzer:
    """Base AI analyzer class for BizSight."""
    
    def __init__(self, ai_provider: str = "claude", model: str = None, api_key: str = None):
        self.provider = ai_provider
        self.model = model
        if ai_provider == "claude":
            self.api_key = api_key or os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
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
                import anthropic
                client = anthropic.Anthropic(api_key=self.api_key)
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
            else:
                raise Exception(f"Unsupported AI provider: {self.provider}")
        except Exception as e:
            raise Exception(f"Error calling {self.provider.upper()} API: {e}")


class AIProvider:
    """Simple wrapper around AIAnalyzer for compatibility."""

    STYLE_GUIDE = """
        NCRC STYLE GUIDE (apply to all narrative output):
        - Keep sentences short and direct. Maximum one subordinate clause per sentence.
        - If a sentence exceeds 30 words, break it into two sentences.
        - State the finding first, then the explanation. Do not front-load qualifiers.
        - Do not hedge excessively. Use "suggest," "appear to," or "may indicate" no more than once per paragraph. After that, state findings directly.
        - Prefer periods over semicolons. Use semicolons only to separate items in a complex list.
        - Do not use the Oxford comma (no comma before "and" or "or" in a series).
        - Do not insert commas before dependent clauses that complete the main thought. When in doubt, omit the comma.
        - One sentence maximum for table or chart introductions. Lead with what the data shows, not what the visual element is.
        - Do not separately describe a chart and its underlying table when they show the same data.
        - Professional, objective, measured tone. No promotional language.
        - Avoid adjectives that editorialize: "dramatic," "alarming," "impressive," "significant" (unless statistically significant). Let the data speak.
        - Do not use em-dashes. Use commas, periods or colons instead.
        - Do not use emoticons or emoji.
        """

    def __init__(self, ai_provider: str = "claude", model: str = None, api_key: str = None):
        self.analyzer = AIAnalyzer(ai_provider=ai_provider, model=model, api_key=api_key)

    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> str:
        """Generate text using the AI provider with NCRC style guide prepended."""
        styled_prompt = self.STYLE_GUIDE + "\n" + prompt
        return self.analyzer._call_ai(styled_prompt, max_tokens=max_tokens, temperature=temperature)

