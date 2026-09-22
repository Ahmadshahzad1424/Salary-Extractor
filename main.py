import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types  # type: ignore
from pydantic import BaseModel

load_dotenv()


class SalaryCertificate(BaseModel):
    employer_name: Optional[str] = None
    employer_ntn: Optional[str] = None
    employee_name: Optional[str] = None
    employee_cnic: Optional[str] = None
    gross_salary: Optional[int] = None
    tax_deducted: Optional[int] = None
    tax_year: Optional[str] = None


def read_certificate(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text(encoding="utf-8")


def call_llm(certificate_text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Add it to your .env file.")

    client = genai.Client(api_key=api_key)
    prompt = (
        "Extract the following 7 fields from this salary certificate. "
        "If a field is missing or unclear, set it to null. Never guess.\n\n"
        f"Certificate:\n{certificate_text}"
    )

    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SalaryCertificate,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        return response.text
    except Exception as err:
        raise RuntimeError(f"Gemini API error: {err}") from err


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py <certificate_file>", file=sys.stderr)
        sys.exit(1)

    try:
        text = read_certificate(sys.argv[1])
        raw_response = call_llm(text)
        data = SalaryCertificate.model_validate_json(raw_response)
        print(json.dumps(data.model_dump(), indent=2))
    except FileNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    except ValueError as err:
        print(f"Configuration error: {err}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as err:
        print(f"API error: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f"Failed to process response: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
