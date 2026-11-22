"""Domain-specific exceptions.

Every failure the UI can encounter is mapped to one of these classes so that
the frontend can show a precise, actionable message instead of a stack trace.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all handled application errors."""

    title = "Something went wrong"

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class RequirementValidationError(AppError):
    title = "Requirement needs attention"


class TestCaseValidationError(AppError):
    __test__ = False  # not a pytest test class
    title = "Test case is incomplete"


class ConfigurationError(AppError):
    title = "Configuration problem"


class ProviderUnavailableError(AppError):
    title = "LLM provider not reachable"


class ModelNotFoundError(AppError):
    title = "Model not available"


class AuthenticationError(AppError):
    title = "Authentication failed"


class RateLimitError(AppError):
    title = "Provider busy or quota exceeded"


class LLMTimeoutError(AppError):
    title = "LLM request timed out"


class InvalidLLMResponseError(AppError):
    title = "Invalid AI response"


class LLMProviderError(AppError):
    title = "LLM provider error"
