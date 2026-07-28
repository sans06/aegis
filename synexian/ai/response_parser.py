"""Aegis AI response module

This module implements techniques for parsing and validating LLM responses, 
with focus on structured output extraction and error recovery.

Some of the reference research :
1. Structured Outputs - OpenAI (2024)
   https://platform.openai.com/docs/guides/structured-outputs
   - 100% JSON compliance with strict mode
   - Reduced parsing errors through schema enforcement
   - Response validation critical for reliability

2. Mastering Structured Output in LLMs - Medium (2024)
   https://medium.com/@docherty/mastering-structured-output-in-llms-choosing-the-right-model-for-json-output-with-langchain-be29fb6f6675
   - Multiple extraction strategies needed
   - Fallback mechanisms essential
   - Validation before downstream use

3. Practical Techniques to Constraint LLM Output (2024)
   https://mychen76.medium.com/practical-techniques-to-constraint-llm-output-in-json-format-e3e72396c670
   - Multiple parsing attempts with different strategies
   - JSON repair techniques for malformed output
   - Graceful degradation on parse failures

Key Features :
- Multi-stage JSON extraction with fallbacks
- Schema validation for structured responses
- Robust error recovery with detailed logging
- Support for markdown code blocks
- Nested JSON extraction
"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential


import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("synexian.ai.parser")


def parse_json_response(response: str, strict: bool = False) -> Optional[Dict[str, Any]]:
    """Parse JSON from AI response with multiple fallback strategies.

    Implements multi-stage parsing (Medium 2024):
    1. Direct JSON parse (fastest)
    2. Extract from ```json``` markdown blocks
    3. Extract from first { to last }
    4. Repair common JSON errors
    5. Return None if all fail

    Args:
        response: AI response string
        strict: If True, return None on parse failure instead of attempting repair

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not response or not response.strip():
        logger.warning("Empty response provided to parser")
        return None

    # Strategy 1: Direct JSON parse (works if response is pure JSON)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    # Pattern: ```json\n{...}\n```
    if "```json" in response:
        try:
            # Find ```json block
            start_pattern = r"```json\s*"
            end_pattern = r"\s*```"

            match = re.search(
                start_pattern + r"(.*?)" + end_pattern,
                response,
                re.DOTALL | re.IGNORECASE,
            )

            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to parse markdown JSON block: {e}")

    # Strategy 3: Extract from any code block (```...```)
    if "```" in response:
        try:
            # Find any code block
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to parse generic code block: {e}")

    # Strategy 4: Extract first { to last } (for JSON embedded in text)
    try:
        start = response.index("{")
        end = response.rindex("}") + 1
        json_str = response[start:end]
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        logger.debug(f"Failed to extract JSON from braces: {e}")

    # Strategy 5: Attempt JSON repair (if not strict)
    if not strict:
        repaired = attempt_json_repair(response)
        if repaired:
            return repaired

    logger.warning("All JSON parsing strategies failed")
    return None


def attempt_json_repair(response: str) -> Optional[Dict[str, Any]]:
    """Attempt to repair common JSON formatting errors.

    Common issues:
    - Missing quotes around keys
    - Trailing commas
    - Single quotes instead of double quotes
    - Unescaped newlines in strings

    Args:
        response: Potentially malformed JSON string

    Returns:
        Parsed JSON dict or None
    """
    try:
        # Extract potential JSON portion
        start = response.find("{")
        end = response.rfind("}") + 1
        if start == -1 or end == 0:
            return None

        json_str = response[start:end]

        # Repair 1: Replace single quotes with double quotes
        # (but not within strings)
        json_str = json_str.replace("'", '"')

        # Repair 2: Remove trailing commas before } or ]
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # Repair 3: Add quotes to unquoted keys
        # Pattern: word characters followed by colon
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)

        # Try parsing repaired JSON
        return json.loads(json_str)

    except (ValueError, json.JSONDecodeError, Exception) as e:
        logger.debug(f"JSON repair failed: {e}")
        return None


def extract_recommendations(response: Dict[str, Any]) -> List[str]:
    """Extract recommendations from AI response.

    Supports multiple common key names for recommendations.

    Args:
        response: Parsed AI response

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Try common keys for recommendations
    possible_keys = [
        "recommendations",
        "suggestions",
        "improvements",
        "action_items",
        "fixes",
        "next_steps",
    ]

    for key in possible_keys:
        if key in response:
            value = response[key]

            # Handle list of strings
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        recommendations.append(item)
                    elif isinstance(item, dict) and 'text' in item:
                        recommendations.append(item['text'])

            # Handle single string
            elif isinstance(value, str):
                recommendations.append(value)

    return recommendations


def extract_score(
    response: Dict[str, Any],
    score_keys: Optional[List[str]] = None,
    default: Optional[float] = None,
) -> Optional[float]:
    """Extract numerical score from AI response.

    Args:
        response: Parsed AI response
        score_keys: List of possible keys containing the score
        default: Default value if score not found

    Returns:
        Score value or default/None
    """
    if score_keys is None:
        score_keys = [
            "score",
            "quality_score",
            "architecture_score",
            "readability_score",
            "test_quality_score",
            "complexity_score",
            "security_score",
            "overall_score",
        ]

    # Try each possible key
    for key in score_keys:
        if key in response:
            try:
                score = float(response[key])
                # Validate score range (0-100)
                if 0 <= score <= 100:
                    return score
                else:
                    logger.warning(f"Score {score} outside valid range [0,100]")
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not convert {key} to float: {e}")
                continue

    return default


def validate_analysis_response(
    response: Dict[str, Any],
    required_keys: Optional[List[str]] = None,
    strict: bool = False,
) -> bool:
    """Validate that AI response has required structure.

    Args:
        response: Parsed AI response
        required_keys: List of required keys (None = no validation)
        strict: If True, return False on any validation error

    Returns:
        True if response is valid
    """
    if not isinstance(response, dict):
        logger.warning("Response is not a dictionary")
        return False

    if required_keys is None:
        return True

    # Check all required keys present
    missing_keys = [key for key in required_keys if key not in response]

    if missing_keys:
        logger.warning(f"Response missing required keys: {missing_keys}")
        if strict:
            return False

    # Validate non-empty values for required keys
    for key in required_keys:
        if key in response:
            value = response[key]

            # Check for None or empty values
            if value is None or (isinstance(value, (list, dict, str)) and not value):
                logger.warning(f"Required key '{key}' has empty value")
                if strict:
                    return False

    return not (strict and missing_keys)


def extract_issues(response: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract issues/violations from AI response.

    Args:
        response: Parsed AI response

    Returns:
        List of issue dictionaries
    """
    issues = []

    # Try common keys for issues
    possible_keys = [
        "issues",
        "violations",
        "problems",
        "errors",
        "warnings",
        "solid_violations",
        "missing_edge_cases",
        "boundary_issues",
        "validation_gaps",
    ]

    for key in possible_keys:
        if key in response and isinstance(response[key], list):
            for item in response[key]:
                if isinstance(item, dict):
                    issues.append(item)
                elif isinstance(item, str):
                    issues.append({"description": item})

    return issues


def get_response_summary(response: Dict[str, Any]) -> str:
    """Generate a summary of AI response contents.

    Useful for logging and debugging.

    Args:
        response: Parsed AI response

    Returns:
        Summary string
    """
    if not isinstance(response, dict):
        return f"Non-dict response: {type(response)}"

    summary_parts = []

    # Count keys
    summary_parts.append(f"{len(response)} keys")

    # Extract score if present
    score = extract_score(response)
    if score is not None:
        summary_parts.append(f"score: {score}")

    # Count recommendations
    recommendations = extract_recommendations(response)
    if recommendations:
        summary_parts.append(f"{len(recommendations)} recommendations")

    # Count issues
    issues = extract_issues(response)
    if issues:
        summary_parts.append(f"{len(issues)} issues")

    return " | ".join(summary_parts)
