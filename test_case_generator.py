"""Application service layer.

Coordinates the agent and the database so the UI never talks to the LLM or to
SQL directly. Also validates every manual create/edit before persisting it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from agent import AgentResult, LLMClient, ProgressCallback, TestCaseAgent
from config import Settings
from database import Database
from validators import validate_manual_test_case


@dataclass
class GenerationOutcome:
    result: AgentResult
    session_id: int | None


class TestCaseGeneratorService:
    __test__ = False  # not a pytest test class

    def __init__(self, settings: Settings, db: Database,
                 client_factory: Callable[[Settings], LLMClient] | None = None) -> None:
        self.settings = settings
        self.db = db
        self._client_factory = client_factory or (lambda s: LLMClient(s))

    # ----------------------------------------------------------- generation
    def generate(self, requirement: str, scenario_types: list[str], *,
                 proceed_with_assumptions: bool = False,
                 progress: ProgressCallback | None = None) -> GenerationOutcome:
        agent = TestCaseAgent(self._client_factory(self.settings), self.settings)
        result = agent.run(requirement, scenario_types,
                           proceed_with_assumptions=proceed_with_assumptions, progress=progress)
        if result.status != "completed":
            return GenerationOutcome(result=result, session_id=None)
        session_id = self.db.create_session(
            title=result.analysis.title,
            requirement=result.requirement,
            scenario_types=result.scenario_types,
            test_cases=[{**c.model_dump(), "source": "ai"} for c in result.test_cases],
            metadata={
                "provider": result.provider,
                "model": result.model,
                "analysis": result.analysis.model_dump(),
                "warnings": result.warnings,
                "generation_seconds": result.elapsed_seconds,
                "raw_case_count": result.raw_case_count,
                "duplicates_removed": result.duplicates_removed,
                "repair_attempts": result.repair_attempts,
            },
        )
        return GenerationOutcome(result=result, session_id=session_id)

    # ------------------------------------------------------ manual editing
    @staticmethod
    def _clean(data: dict[str, Any]) -> dict[str, Any]:
        return validate_manual_test_case(data).model_dump()

    def add_test_case(self, session_id: int, data: dict[str, Any]) -> int:
        return self.db.add_test_case(session_id, {**self._clean(data), "source": "manual"})

    def update_test_case(self, case_id: int, data: dict[str, Any]) -> bool:
        return self.db.update_test_case(case_id, self._clean(data))

    def delete_test_case(self, case_id: int) -> bool:
        return self.db.delete_test_case(case_id)

    def delete_session(self, session_id: int) -> bool:
        return self.db.delete_session(session_id)

    def provider_status(self) -> dict[str, Any]:
        return self._client_factory(self.settings).describe_status()
