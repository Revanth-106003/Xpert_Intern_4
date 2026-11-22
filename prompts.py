"""Prompt engineering for the two-stage test-design agent.

Stage 1 (ANALYSIS) makes the model *understand* the requirement before writing
any tests: functionality, actors, inputs, explicitly stated rules, gaps and
assumptions, plus a clarity verdict.

Stage 2 (GENERATION) designs test cases grounded in that analysis.

A REPAIR prompt is used when a response fails JSON/schema validation.
All prompts are LangChain ``ChatPromptTemplate`` objects; literal braces in the
JSON examples are escaped as ``{{ }}``.
"""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_ROLE = (
    "You are a meticulous Senior QA Engineer and test architect with 15 years of experience "
    "in requirement-based test design (equivalence partitioning, boundary value analysis, "
    "decision tables, state transition and error guessing). You never invent business rules: "
    "anything not stated in the requirement is either a clearly labelled assumption or an open "
    "question. You always answer with a single valid JSON object and nothing else."
)

# --------------------------------------------------------------------------- #
# Stage 1 - requirement analysis
# --------------------------------------------------------------------------- #
ANALYSIS_INSTRUCTIONS = """Analyse the software requirement below BEFORE any test design.

REQUIREMENT:
\"\"\"
{requirement}
\"\"\"

Do the following:
1. Identify the main functionality and who uses it (actors).
2. List the user inputs / data fields involved.
3. Extract ONLY the validation and business rules that are EXPLICITLY stated. Quote or closely
   paraphrase the requirement. Never add rules that are not written (e.g. do not invent password
   lengths, limits or formats).
4. List missing or unclear information that a tester would need to ask about.
5. List the minimal assumptions needed to test it anyway (each must be reasonable and generic,
   prefixed with "Assumption:").
6. Decide which scenario types are applicable: "Positive", "Negative", "Edge Case".
7. Rate clarity:
   - "clear": the behaviour is testable as written.
   - "partially_clear": testable, but some details are missing (use assumptions).
   - "unclear": too vague to know WHAT the system should do (e.g. "make it better", a single
     word, no observable behaviour). Provide 2-5 specific clarification questions.

Return ONLY this JSON object:
{{
  "title": "short name of the feature, max 8 words",
  "summary": "one or two sentences restating the requirement in your own words",
  "main_functionality": "the core behaviour under test",
  "actors": ["..."],
  "inputs": ["..."],
  "validation_rules": ["rules explicitly stated in the requirement"],
  "missing_information": ["..."],
  "assumptions": ["Assumption: ..."],
  "applicable_scenarios": ["Positive", "Negative", "Edge Case"],
  "clarity": "clear | partially_clear | unclear",
  "clarification_questions": ["..."]
}}"""

ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_ROLE), ("human", ANALYSIS_INSTRUCTIONS)]
)

# --------------------------------------------------------------------------- #
# Stage 2 - test case generation
# --------------------------------------------------------------------------- #
GENERATION_INSTRUCTIONS = """Design software test cases for the requirement below, grounded in the analysis.

REQUIREMENT:
\"\"\"
{requirement}
\"\"\"

ANALYSIS (produced in the previous step):
{analysis}

SCENARIO TYPES TO COVER: {scenario_types}
TARGET: between {min_cases} and {max_cases} test cases in total, distributed across the requested
scenario types according to how much the requirement supports each. Quality over quantity.

Rules:
- Only use the requested scenario types. Scenario type values must be exactly one of:
  {scenario_types}.
  * Positive  = valid input / expected successful behaviour.
  * Negative  = invalid input, unauthorised action or violated rule; the system must reject or handle it.
  * Edge Case = boundaries, limits, empty/maximum values, special characters, concurrency, repeated
    actions or unusual-but-valid conditions.
- Every test case must verify something DIFFERENT. No duplicates or trivial rewordings.
- Each validation rule from the analysis should be covered by at least one test case.
- "steps": 3-7 concrete, actionable steps a manual tester can follow (no numbering prefix).
- "test_data": realistic, specific values (e.g. "Email: priya.sharma@example.com, Password: Secure@123").
  Use "N/A" only if no data is involved.
- "expected_result": a precise, observable, verifiable outcome.
- "priority": exactly "High", "Medium" or "Low".
  High = core functionality, security or data integrity; Medium = important validations and common
  alternate flows; Low = cosmetic or rare conditions.
- Do NOT invent business rules. If a test relies on something not stated in the requirement, put the
  assumption in "assumption" (e.g. "Assumption: maximum length is 50 characters"); otherwise use "".

Return ONLY this JSON object:
{{
  "test_cases": [
    {{
      "scenario": "concise description of what is being verified",
      "scenario_type": "Positive | Negative | Edge Case",
      "steps": ["step one", "step two", "step three"],
      "test_data": "specific input values",
      "expected_result": "observable expected outcome",
      "priority": "High | Medium | Low",
      "assumption": ""
    }}
  ]
}}"""

GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_ROLE), ("human", GENERATION_INSTRUCTIONS)]
)

# --------------------------------------------------------------------------- #
# Repair prompt - self-correction when output fails validation
# --------------------------------------------------------------------------- #
REPAIR_INSTRUCTIONS = """Your previous response could not be used because it failed validation.

VALIDATION ERROR:
{error}

ORIGINAL TASK:
{task}

YOUR PREVIOUS RESPONSE (may be truncated):
{previous}

Return the corrected response as ONE valid JSON object that follows the required schema exactly.
Do not include explanations, markdown or code fences."""

REPAIR_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_ROLE), ("human", REPAIR_INSTRUCTIONS)]
)


def target_case_range(scenario_count: int, max_cases: int) -> tuple[int, int]:
    """Number of test cases to request, scaled to the number of scenario types."""
    upper = max(4, min(max_cases, 6 * scenario_count + 2))
    lower = max(3, min(upper, 3 * scenario_count + 1))
    return lower, upper
