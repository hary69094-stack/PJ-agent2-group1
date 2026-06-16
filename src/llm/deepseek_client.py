"""DeepSeek API client — thin OpenAI-compatible wrapper with retry logic."""

import time
from typing import List, Dict, Optional
from openai import OpenAI, RateLimitError, APIConnectionError, APIError


class ChatError(Exception):
    """Raised when the LLM chat call fails after all retries."""


class DeepSeekClient:
    """OpenAI-compatible client for DeepSeek API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_backoff_seconds: float = 2.0,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send messages to DeepSeek and return the response content string.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            temperature: Override default temperature.
            max_tokens: Override default max_tokens.

        Returns:
            The assistant's response text.

        Raises:
            ChatError: If the API call fails after all retries.
        """
        temp = temperature if temperature is not None else self.temperature
        mt = max_tokens if max_tokens is not None else self.max_tokens

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=mt,
                )
                return response.choices[0].message.content or ""

            except (RateLimitError, APIConnectionError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = self.retry_backoff_seconds * (2 ** attempt)
                    time.sleep(wait)
                else:
                    break
            except APIError as e:
                last_error = e
                break

        raise ChatError(
            f"DeepSeek API call failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def chat_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Alias for chat() — the retry is built in."""
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens)
