import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, Optional, Union
import warnings

from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import BaseModel, ConfigDict, field_validator

# Suppress library deprecation warning for clean output
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

# Load environment variables (.env file supported)
load_dotenv()


class SalaryCertificateSchema(BaseModel):
    """Pydantic model representing structured salary certificate fields.

    Matches the exact 7-field schema required for tax compliance processing:
    - employer_name
    - employer_ntn
    - employee_name
    - employee_cnic
    - gross_salary
    - tax_deducted
    - tax_year
    """

    model_config = ConfigDict(extra="ignore")

    employer_name: Optional[str] = None
    employer_ntn: Optional[str] = None
    employee_name: Optional[str] = None
    employee_cnic: Optional[str] = None
    gross_salary: Optional[Union[int, float]] = None
    tax_deducted: Optional[Union[int, float]] = None
    tax_year: Optional[str] = None

    @field_validator("gross_salary", "tax_deducted", mode="before")
    @classmethod
    def clean_numeric_amount(cls, value: Any) -> Optional[Union[int, float]]:
        """Clean string representation of currency amounts to pure numbers.

        Examples:
            "PKR 1,500,000" -> 1500000
            "125,000.50" -> 125000.5
            None / "null" -> None
        """
        if value is None or str(value).strip().lower() in {"null", "none", "n/a", ""}:
            return None

        if isinstance(value, (int, float)):
            return value

        # Remove currency codes, symbols, commas, and whitespace
        clean_str = re.sub(r"[^\d.-]", "", str(value).strip())
        if not clean_str or clean_str == "-":
            return None

        try:
            float_val = float(clean_str)
            return int(float_val) if float_val.is_integer() else float_val
        except ValueError:
            return None

    @field_validator("tax_year", mode="before")
    @classmethod
    def clean_tax_year(cls, value: Any) -> Optional[str]:
        """Ensure tax_year is returned as a string."""
        if value is None or str(value).strip().lower() in {"null", "none", "n/a", ""}:
            return None
        return str(value).strip()


EXTRACTION_PROMPT_TEMPLATE = """You are an expert AI document processing engine for TaxMind AI, a tax compliance platform.
Your task is to extract structured tax and compensation data from the provided salary certificate.

Target Fields to Extract:
1. "employer_name": Full legal name of the employer / organization (string, or null).
2. "employer_ntn": National Tax Number (NTN) of the employer (e.g. "1234567-8", or null).
3. "employee_name": Full name of the employee (string, or null).
4. "employee_cnic": Computerized National Identity Card number of the employee (e.g. "35202-1234567-1", or null).
5. "gross_salary": Total gross salary amount as a number without currency symbols (e.g. 1500000, or null).
6. "tax_deducted": Total tax deducted or deposited amount as a number without currency symbols (e.g. 125000, or null).
7. "tax_year": The applicable tax year (e.g. "2026", or null).

Strict Extraction Rules:
- Return a single, valid JSON object containing ONLY the 7 keys listed above.
- Do NOT wrap the output in markdown code fences (e.g. do not include ```json or ```).
- If a field is not mentioned or cannot be determined from the certificate, you MUST set its value to null.
- CRITICAL: Never guess, infer, or invent missing information. Use only explicitly stated facts.

Salary Certificate Text:
{certificate_text}"""


def read_salary_certificate(file_path: Union[str, Path]) -> str:
    """Read a salary certificate text file and return its content as a string.

    Args:
        file_path: Path to the certificate text file.

    Returns:
        The content of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If an error occurs reading the file.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Salary certificate file not found: {path.resolve()}")

    if not path.is_file():
        raise IsADirectoryError(f"Target path is a directory, not a file: {path.resolve()}")

    try:
        with open(path, mode="r", encoding="utf-8") as file:
            return file.read()
    except UnicodeDecodeError:
        with open(path, mode="r", encoding="latin-1") as file:
            return file.read()
    except OSError as err:
        raise IOError(f"Could not read certificate file at '{path}': {err}") from err


def call_llm(certificate_text: str, model_name: str = "gemini-flash-latest") -> str:
    """Send certificate text to Gemini LLM with structured extraction instructions.

    Args:
        certificate_text: The text content of the salary certificate.
        model_name: The Gemini model identifier (default: "gemini-flash-latest").

    Returns:
        The raw text response from the LLM.

    Raises:
        ValueError: If the API key is not configured.
        RuntimeError: If the LLM API request fails.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set 'GEMINI_API_KEY' in your environment or in a .env file."
        )

    effective_model = os.getenv("GEMINI_MODEL", model_name)
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(certificate_text=certificate_text)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=effective_model,
            generation_config={"response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as err:
        raise RuntimeError(f"Gemini API error ({effective_model}): {err}") from err


def parse_llm_response(raw_response: str) -> Union[Dict[str, Any], str]:
    """Parse, clean, and validate the LLM response using Pydantic.

    - Strips markdown code fences (```json ... ```)
    - Parses JSON content
    - Validates against the 7-field schema with Pydantic
    - Returns a clean Python dictionary or a descriptive error message on failure

    Args:
        raw_response: Raw response string from the LLM.

    Returns:
        A dictionary with all 7 keys guaranteed, or an error string if invalid.
    """
    if not isinstance(raw_response, str):
        return f"Error: Expected string response from LLM, got {type(raw_response).__name__}."

    cleaned = raw_response.strip()

    # 1. Strip markdown code fences if present
    if cleaned.startswith("```"):
        pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
        match = re.match(pattern, cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

    # 2. Parse JSON
    try:
        raw_json = json.loads(cleaned)
    except json.JSONDecodeError as err:
        return f"Error: Failed to parse LLM response as JSON ({err})."

    if not isinstance(raw_json, dict):
        return f"Error: Expected JSON object (dict), received {type(raw_json).__name__}."

    # 3. Validate and enforce schema using Pydantic
    try:
        validated_data = SalaryCertificateSchema(**raw_json)
        return validated_data.model_dump()
    except Exception as err:
        return f"Error: Schema validation failed ({err})."


def main() -> None:
    """End-to-end execution pipeline for salary certificate extraction."""
    # 1. Check command-line arguments and read input file
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_salary_certificate_file>", file=sys.stderr)
        print("Example: python main.py sample_certificate.txt", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]

    try:
        certificate_text = read_salary_certificate(input_path)
    except FileNotFoundError as err:
        print(f"Error reading input file: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f"Unexpected file error: {err}", file=sys.stderr)
        sys.exit(1)

    # 2. Call Gemini LLM
    try:
        raw_response = call_llm(certificate_text)
    except ValueError as err:
        print(f"Configuration error: {err}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as err:
        print(f"LLM API error: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f"Unexpected error calling LLM: {err}", file=sys.stderr)
        sys.exit(1)

    # 3. Parse and validate structured output
    parsed_result = parse_llm_response(raw_response)
    if isinstance(parsed_result, str):
        print(f"Extraction error: {parsed_result}", file=sys.stderr)
        sys.exit(1)

    # 4. Print clean, nicely formatted JSON output
    print(json.dumps(parsed_result, indent=2))


if __name__ == "__main__":
    main()
