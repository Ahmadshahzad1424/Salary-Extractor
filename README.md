# TaxMind AI - Salary Certificate Information Extractor

An AI-powered extraction pipeline built for the **AI Engineer Intern** technical evaluation at **TaxMind AI**.

This application extracts structured tax compliance and compensation data from salary certificates using **Google Gemini** and **Pydantic**.

---

## Technical Overview & Features

- **Document Processing**: Ingests salary certificate text documents.
- **LLM Integration**: Leverages Google Gemini with JSON mode (`response_mime_type: "application/json"`) and zero-shot prompt engineering.
- **Structured Output & Validation**: Uses **Pydantic** (`SalaryCertificateSchema`) to enforce schema integrity, sanitize numeric amounts (`gross_salary`, `tax_deducted`), and handle null values.
- **No Hallucinations**: Strict instructions ensure missing or unmentioned fields default to `null`.
- **Fault-Tolerant Error Handling**: Comprehensive error trapping for file I/O, missing API keys, network/quota failures, and invalid LLM responses.

### Target Schema

| Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `employer_name` | `string \| null` | Name of the employing organization | `"ABC Technologies (Pvt.) Ltd."` |
| `employer_ntn` | `string \| null` | Employer's National Tax Number | `"1234567-8"` |
| `employee_name` | `string \| null` | Full name of employee | `"Ahmed Khan"` |
| `employee_cnic` | `string \| null` | Employee's CNIC number | `"35202-1234567-1"` |
| `gross_salary` | `number \| null` | Total gross salary amount | `1500000` |
| `tax_deducted` | `number \| null` | Total tax deducted/withheld | `125000` |
| `tax_year` | `string \| null` | Relevant tax year | `"2026"` |

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- A Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Alternatively, set the environment variable directly in your terminal: `export GEMINI_API_KEY="..."` or `$env:GEMINI_API_KEY="..."` on Windows).*

---

## How to Run

Pass any salary certificate text file to `main.py`:

```bash
python main.py sample_certificate.txt
```

### Example Output

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

## Error Handling

- **Missing Input File**: Displays a clear message if the file cannot be located.
- **Missing API Key**: Informs the user how to configure `GEMINI_API_KEY`.
- **API or Network Failures**: Catches exceptions without crashing.
- **Malformed LLM Output**: Strips code fences and validates structure with Pydantic, ensuring clean JSON output or an informative error report.
