import os

from anthropic import (Anthropic, APIConnectionError, APIStatusError,
                       RateLimitError)
from dotenv import load_dotenv

load_dotenv()

claude_client = Anthropic(api_key=os.getenv("CLAUDE_KEY"))


class LLMClient:
    def fetch(self, model, max_tokens, system, messages):
        try:
            message = claude_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )

        except APIConnectionError:
            raise
        except RateLimitError:
            raise
        except APIStatusError:
            raise

        return message
