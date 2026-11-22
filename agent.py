"""LangChain-based test-design agent.

Workflow (each step is an explicit stage reported to the UI):

    validate input -> check provider -> ANALYSE requirement -> (clarification gate)
    -> GENERATE test cases -> VALIDATE schema (+ self-repair) -> filter & de-duplicate

The LLM provider is pluggable (Ollama locally, or Google Gemini). Every
provider/network failure is translated into a typed :mod:`errors` exception.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from config import SCENARIO_TYPES, Settings
from errors import (
    AppError,
    AuthenticationError,
    ConfigurationError,
    InvalidLLMResponseError,
    LLMProviderError,
    LLMTimeoutError,
    ModelNotFoundError,
    ProviderUnavailableError,
    RateLimitError,
)
from prompts import ANALYSIS_PROMPT, GENERATION_PROMPT, REPAIR_PROMPT, target_case_range
from validators import (
    RequirementAnalysis,
    TestCaseModel,
    deduplicate,
    extract_json,
    parse_analysis,
    parse_test_cases,
    validate_requirement,
    validate_scenario_selection,
)

ProgressCallback = Callable[[str, str], None]

OLLAMA_INSTALL_HINT = (
    "Install Ollama from https://ollama.com/download, start it (it runs in the background, or run "
    "'ollama serve'), then download the model with 'ollama pull {model}'. "
    "Alternatively set LLM_PROVIDER=gemini and GEMINI_API_KEY in the .env file."
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def message_text(message: Any) -> str:
    """Extract plain text from a LangChain message (string or content blocks)."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type", "text") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content or "")


def classify_exception(exc: BaseException, provider: str, model: str) -> AppError:
    """Map any provider/SDK/network exception onto a typed application error."""
    if isinstance(exc, AppError):
        return exc
    name = type(exc).__name__
    text = f"{name} {exc}".lower()
    short = str(exc).strip().splitlines()[0][:300] if str(exc).strip() else name

    if isinstance(exc, (TimeoutError, requests.Timeout)) or any(
        k in text for k in ("timed out", "timeout", "deadline exceeded", "deadlineexceeded")
    ):
        return LLMTimeoutError(
            f"The {provider} model did not respond in time.",
            "Try again, shorten the requirement, or increase LLM_TIMEOUT_SECONDS in .env.",
        )
    if any(k in text for k in ("api key not valid", "api_key_invalid", "invalid api key",
                               "unauthenticated", "permission_denied", "permissiondenied",
                               " 401", " 403", "api key expired")):
        return AuthenticationError(
            "The Gemini API key was rejected by Google.",
            "Check GEMINI_API_KEY in your .env file (create a key at https://aistudio.google.com/apikey) "
            "and restart the application.",
        )
    if any(k in text for k in ("connection refused", "failed to establish", "actively refused",
                               "connecterror", "connectionerror", "max retries exceeded",
                               "name or service not known", "getaddrinfo failed",
                               "nodename nor servname")):
        if provider == "ollama":
            return ProviderUnavailableError(
                "Cannot connect to the Ollama server.", OLLAMA_INSTALL_HINT.format(model=model)
            )
        return ProviderUnavailableError(
            "Cannot reach the Gemini API.", "Check your internet connection or proxy settings and retry."
        )
    if ("not found" in text or " 404" in text or "notfound" in text) and "model" in text:
        if provider == "ollama":
            return ModelNotFoundError(
                f"The Ollama model '{model}' is not installed.", f"Run: ollama pull {model}"
            )
        return ModelNotFoundError(
            f"The Gemini model '{model}' is not available for this API key.",
            "Set GEMINI_MODEL in .env to an available model such as gemini-3.6-flash.",
        )
    if any(k in text for k in ("429", "quota", "resource_exhausted", "resourceexhausted", "rate limit",
                               "503", "overloaded", "high demand", "serviceunavailable",
                               "service unavailable")):
        return RateLimitError(
            f"The {provider} service is busy or the quota is exhausted.",
            "Wait a minute and try again. If it persists, check your quota or switch model.",
        )
    return LLMProviderError(f"The {provider} provider returned an error: {short}",
                            "Check the provider configuration in the System Status page.")


# --------------------------------------------------------------------------- #
# Provider client
# --------------------------------------------------------------------------- #
class LLMClient:
    """Thin wrapper around a LangChain chat model with readiness checks."""

    def __init__(self, settings: Settings, chat_model: BaseChatModel | None = None) -> None:
        self.settings = settings
        self.provider = settings.llm_provider
        self.model_name = settings.active_model
        self._injected = chat_model is not None
        self._chat_model = chat_model

    # -- construction --------------------------------------------------------
    def _build(self) -> BaseChatModel:
        s = self.settings
        if self.provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=s.ollama_model,
                base_url=s.ollama_base_url,
                temperature=s.temperature,
                format="json",
                num_ctx=8192,
                num_predict=4096,
                client_kwargs={"timeout": s.timeout_seconds},
            )
        if self.provider == "gemini":
            if not s.gemini_key_configured:
                raise ConfigurationError(
                    "GEMINI_API_KEY is not set.",
                    "Add GEMINI_API_KEY=<your key> to the .env file in the project folder and restart.",
                )
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=s.gemini_model,
                google_api_key=s.gemini_api_key,
                temperature=s.temperature,
                timeout=s.timeout_seconds,
                max_retries=2,
                response_mime_type="application/json",
            )
        raise ConfigurationError(
            f"Unknown LLM_PROVIDER '{self.provider}'.", "Use LLM_PROVIDER=ollama or LLM_PROVIDER=gemini."
        )

    @property
    def chat_model(self) -> BaseChatModel:
        if self._chat_model is None:
            self._chat_model = self._build()
        return self._chat_model

    # -- readiness -------------------------------------------------------------
    def check_ready(self) -> None:
        """Raise a typed error if the configured provider cannot be used."""
        if self._injected:
            return
        if self.provider == "ollama":
            self._check_ollama()
        elif self.provider == "gemini":
            if not self.settings.gemini_key_configured:
                raise ConfigurationError(
                    "GEMINI_API_KEY is not set.",
                    "Add GEMINI_API_KEY=<your key> to the .env file in the project folder and restart.",
                )
        else:
            raise ConfigurationError(
                f"Unknown LLM_PROVIDER '{self.provider}'.", "Use LLM_PROVIDER=ollama or LLM_PROVIDER=gemini."
            )

    def _check_ollama(self) -> None:
        model = self.settings.ollama_model
        url = f"{self.settings.ollama_base_url}/api/tags"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            names = {m.get("name", "") for m in resp.json().get("models", [])}
        except requests.RequestException as exc:
            raise ProviderUnavailableError(
                f"Ollama is not running at {self.settings.ollama_base_url}.",
                OLLAMA_INSTALL_HINT.format(model=model),
            ) from exc
        wanted = {model} if ":" in model else {model, f"{model}:latest"}
        if not names & wanted:
            installed = ", ".join(sorted(n for n in names if n)) or "none"
            raise ModelNotFoundError(
                f"The Ollama model '{model}' is not installed (installed: {installed}).",
                f"Run: ollama pull {model}   — or set OLLAMA_MODEL in .env to an installed model.",
            )

    def describe_status(self) -> dict[str, Any]:
        """Non-throwing status probe for the System Status page."""
        info: dict[str, Any] = {"provider": self.provider, "model": self.model_name}
        try:
            self.check_ready()
            info.update(ok=True, message="Ready")
        except AppError as exc:
            info.update(ok=False, message=exc.message, hint=exc.hint, title=exc.title)
        return info

    def ping(self) -> dict[str, Any]:
        """Perform a real round-trip to the model (used by 'Test connection')."""
        from langchain_core.prompts import ChatPromptTemplate as _T

        started = time.perf_counter()
        self.check_ready()
        reply = self.invoke(_T.from_messages([("human", 'Return exactly this JSON: {{"status": "ok"}}')]), {})
        data = extract_json(reply)
        if not isinstance(data, dict):
            raise InvalidLLMResponseError("Unexpected reply to the connection test.")
        return {"latency_seconds": round(time.perf_counter() - started, 2), "reply": data}

    # -- invocation --------------------------------------------------------------
    def invoke(self, prompt: ChatPromptTemplate, variables: dict[str, Any]) -> str:
        chain = prompt | self.chat_model
        try:
            return message_text(chain.invoke(variables))
        except Exception as exc:  # noqa: BLE001 - every failure is classified
            raise classify_exception(exc, self.provider, self.model_name) from exc


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #
@dataclass
class AgentResult:
    status: str  # "completed" | "needs_clarification"
    requirement: str
    scenario_types: list[str]
    analysis: RequirementAnalysis
    test_cases: list[TestCaseModel] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicates_removed: int = 0
    raw_case_count: int = 0
    repair_attempts: int = 0
    elapsed_seconds: float = 0.0
    provider: str = ""
    model: str = ""


class TestCaseAgent:
    __test__ = False  # not a pytest test class

    """Two-stage requirement-analysis and test-design agent."""

    def __init__(self, client: LLMClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        self._repairs = 0

    # -- structured invocation with self-repair ----------------------------------
    def _invoke_structured(self, prompt: ChatPromptTemplate, variables: dict[str, Any],
                           parser: Callable[[Any], Any], task: str,
                           progress: ProgressCallback) -> Any:
        raw = self.client.invoke(prompt, variables)
        attempts = 0
        while True:
            try:
                return parser(extract_json(raw))
            except InvalidLLMResponseError as exc:
                if attempts >= self.settings.max_repair_attempts:
                    raise
                attempts += 1
                self._repairs += 1
                progress("repair", f"Response failed validation ({exc.message}) — asking the model to self-correct…")
                raw = self.client.invoke(REPAIR_PROMPT, {
                    "error": f"{exc.message} {exc.hint}".strip(),
                    "task": task,
                    "previous": (raw or "")[:3000],
                })

    # -- public API ----------------------------------------------------------------
    def analyse(self, requirement: str, progress: ProgressCallback | None = None) -> RequirementAnalysis:
        progress = progress or (lambda *_: None)
        return self._invoke_structured(
            ANALYSIS_PROMPT, {"requirement": requirement}, parse_analysis,
            "Analyse the requirement and return the analysis JSON object with keys title, summary, "
            "main_functionality, actors, inputs, validation_rules, missing_information, assumptions, "
            "applicable_scenarios, clarity, clarification_questions.",
            progress,
        )

    def run(self, requirement: str, scenario_types: list[str], *,
            proceed_with_assumptions: bool = False,
            progress: ProgressCallback | None = None) -> AgentResult:
        progress = progress or (lambda *_: None)
        started = time.perf_counter()
        self._repairs = 0

        progress("validate", "Validating requirement input…")
        requirement = validate_requirement(requirement)
        scenario_types = validate_scenario_selection(scenario_types)

        progress("connect", f"Connecting to {self.client.provider} · {self.client.model_name}…")
        self.client.check_ready()

        progress("analyse", "Understanding the requirement — functionality, rules and gaps…")
        analysis = self.analyse(requirement, progress)

        result = AgentResult(
            status="completed", requirement=requirement, scenario_types=scenario_types,
            analysis=analysis, provider=self.client.provider, model=self.client.model_name,
        )

        if analysis.needs_clarification and not proceed_with_assumptions:
            progress("clarify", "Requirement is too vague — clarification needed.")
            result.status = "needs_clarification"
            result.repair_attempts = self._repairs
            result.elapsed_seconds = round(time.perf_counter() - started, 2)
            return result

        lo, hi = target_case_range(len(scenario_types), self.settings.max_test_cases)
        progress("generate", f"Designing {lo}–{hi} test cases across {', '.join(scenario_types)}…")
        analysis_json = json.dumps(analysis.model_dump(), indent=2, ensure_ascii=False)
        cases, warnings = self._invoke_structured(
            GENERATION_PROMPT,
            {
                "requirement": requirement,
                "analysis": analysis_json,
                "scenario_types": ", ".join(f'"{s}"' for s in scenario_types),
                "min_cases": lo,
                "max_cases": hi,
            },
            parse_test_cases,
            'Generate test cases and return {"test_cases": [...]} where each item has scenario, '
            "scenario_type, steps (list), test_data, expected_result, priority (High/Medium/Low), assumption.",
            progress,
        )

        progress("validate_output", "Validating structure, filtering and removing duplicates…")
        result.raw_case_count = len(cases)
        in_scope = [c for c in cases if c.scenario_type in scenario_types]
        dropped = len(cases) - len(in_scope)
        if dropped:
            warnings.append(f"{dropped} test case(s) of an unselected scenario type were discarded.")
        unique, dupes = deduplicate(in_scope)
        if not unique:
            raise InvalidLLMResponseError(
                "The model did not return any test case for the selected scenario types.",
                "Try again or select additional scenario types.",
            )
        for stype in scenario_types:
            if not any(c.scenario_type == stype for c in unique):
                warnings.append(f"No '{stype}' test case was produced for this requirement.")
        if dupes:
            warnings.append(f"{dupes} duplicate test case(s) were removed.")

        # Stable ordering: by scenario type (selection order) then priority.
        order_t = {t: i for i, t in enumerate(SCENARIO_TYPES)}
        order_p = {"High": 0, "Medium": 1, "Low": 2}
        unique.sort(key=lambda c: (order_t[c.scenario_type], order_p[c.priority]))

        result.test_cases = unique
        result.warnings = warnings
        result.duplicates_removed = dupes
        result.repair_attempts = self._repairs
        result.elapsed_seconds = round(time.perf_counter() - started, 2)
        progress("done", f"Generated {len(unique)} validated test cases.")
        return result
