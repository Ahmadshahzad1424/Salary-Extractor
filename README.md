# Salary Certificate Extractor

A script that reads a salary certificate (text file) and uses Google Gemini to extract structured info — employer, employee, salary, and tax details — as JSON.

---

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your API key:**
   ```bash
   cp .env.example .env
   ```
   Add your Gemini API key to `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

---

## Run

Run the script by passing any certificate text file:

```bash
python main.py sample_certificate.txt
```

---

## Output

```json
{
  "employer_name": "ABC Technologies (Pvt.) Ltd.",
  "employer_ntn": "1234567-8",
  "employee_name": "Ahmed Khan",
  "employee_cnic": "35202-1234567-1",
  "gross_salary": 1500000,
  "tax_deducted": 125000,
  "tax_year": "2026"
}
```

---

## How It Works

- **`read_certificate`**: Reads the input certificate text file with UTF-8 encoding.
- **`call_llm`**: Sends the text to Gemini with `response_schema=SalaryCertificate` so Gemini directly outputs schema-compliant JSON without requiring regex post-processing.
- **`SalaryCertificate`**: Pydantic schema defining the 7 required fields with typing and `null` defaults for unmentioned fields.
- **Error Handling**: Gracefully handles missing input files, missing API keys, API errors, and invalid responses with clear error messages instead of traceback crashes.

---

## Note

This project uses the official `google-genai` SDK with native structured JSON mode (`response_mime_type="application/json"`) and Pydantic schema validation.

---

## Files

- `main.py` — core extraction script & Pydantic schema
- `sample_certificate.txt` — example input certificate
- `requirements.txt` — Python dependencies
- `.env.example` — environment variables template
