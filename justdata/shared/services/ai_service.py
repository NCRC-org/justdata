"""
Shared AI service for JustData applications.
"""

from typing import Dict, Any, List, Optional
import anthropic
import openai
from core.config.settings import get_settings
import structlog

logger = structlog.get_logger()


class AIService:
    """Unified AI service for Claude and GPT."""
    
    def __init__(self):
        self.settings = get_settings()
        self.claude_client = None
        self.openai_client = None
        
        # Initialize Claude client
        if self.settings.claude_api_key:
            try:
                self.claude_client = anthropic.Anthropic(
                    api_key=self.settings.claude_api_key
                )
                logger.info("Claude client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Claude client", error=str(e))
        
        # Initialize OpenAI client
        if self.settings.openai_api_key:
            try:
                self.openai_client = openai.OpenAI(
                    api_key=self.settings.openai_api_key
                )
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize OpenAI client", error=str(e))
    
    async def analyze_with_claude(
        self,
        prompt: str,
        data: Dict[str, Any],
        max_tokens: int = 1000,
        model: str = "claude-3-sonnet-20240229"
    ) -> Optional[str]:
        """Analyze data using Claude."""
        if not self.claude_client:
            logger.warning("Claude client not available")
            return None
        
        try:
            # Format the prompt with data
            formatted_prompt = self._format_claude_prompt(prompt, data)
            
            response = self.claude_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error("Claude analysis failed", error=str(e))
            return None
    
    async def analyze_with_gpt(
        self,
        prompt: str,
        data: Dict[str, Any],
        max_tokens: int = 1000,
        model: str = "gpt-4"
    ) -> Optional[str]:
        """Analyze data using GPT."""
        if not self.openai_client:
            logger.warning("OpenAI client not available")
            return None
        
        try:
            # Format the prompt with data
            formatted_prompt = self._format_gpt_prompt(prompt, data)
            
            response = self.openai_client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("GPT analysis failed", error=str(e))
            return None
    
    async def analyze_with_best_available(
        self,
        prompt: str,
        data: Dict[str, Any],
        max_tokens: int = 1000,
        preferred_model: str = "claude"
    ) -> Optional[str]:
        """Analyze data using the best available AI model."""
        if preferred_model == "claude" and self.claude_client:
            result = await self.analyze_with_claude(prompt, data, max_tokens)
            if result:
                return result
        
        if self.openai_client:
            result = await self.analyze_with_gpt(prompt, data, max_tokens)
            if result:
                return result
        
        if self.claude_client:
            result = await self.analyze_with_claude(prompt, data, max_tokens)
            if result:
                return result
        
        logger.error("No AI service available")
        return None
    
    def _format_claude_prompt(self, prompt: str, data: Dict[str, Any]) -> str:
        """Format prompt for Claude."""
        # Convert data to a readable format
        data_str = self._format_data_for_prompt(data)
        return f"{prompt}\n\nData:\n{data_str}"
    
    def _format_gpt_prompt(self, prompt: str, data: Dict[str, Any]) -> str:
        """Format prompt for GPT."""
        # Convert data to a readable format
        data_str = self._format_data_for_prompt(data)
        return f"{prompt}\n\nData:\n{data_str}"
    
    def _format_data_for_prompt(self, data: Dict[str, Any]) -> str:
        """Format data for AI prompt consumption."""
        import json
        try:
            return json.dumps(data, indent=2, default=str)
        except Exception:
            return str(data)
    
    def get_available_models(self) -> Dict[str, bool]:
        """Get available AI models."""
        return {
            "claude": self.claude_client is not None,
            "gpt": self.openai_client is not None
        }


# Global AI service instance
ai_service = AIService()


def get_ai_service() -> AIService:
    """Get the global AI service instance."""
    return ai_service
