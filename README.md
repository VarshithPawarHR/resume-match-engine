# ATS Resume Scoring System with Google Gemini API

This project implements an ATS (Applicant Tracking System) scoring system using Google's Gemini API with structured output capabilities. The system can analyze resumes against job descriptions to provide detailed assessments with consistent JSON-formatted output.

## Features

- **Single Resume Analysis**: Compare one resume against one job description
- **Bulk Resume Processing (2 options)**:
  - **Batch API**: Process multiple resumes using Google's Batch API at 50% of standard cost
  - **Parallel Processing**: Process multiple resumes in parallel threads without using Batch API
- **Structured Output**: Get consistent JSON-formatted analysis results
- **Detailed Evaluations**: Comprehensive resume analysis including skills matching, experience fit, and hiring decision factors
- **Error Handling**: Robust error handling with retry functionality for connection issues
- **PostgreSQL Database**: Simplified database structure with user-specific data storage

## Setup

### Prerequisites

1. **PostgreSQL Database**: Install and run PostgreSQL server
2. **Python Dependencies**: Install required packages

### Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root with your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

### PostgreSQL Setup

The system uses PostgreSQL with a simplified 2-column schema:
- `user_id`: Unique identifier for users
- `data`: JSON field containing all user data

#### Option 1: Automatic Setup (Recommended)

Set environment variables for your PostgreSQL connection:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=context_cache
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
```

Run the setup script:
```bash
python setup_postgres.py
```

#### Option 2: Manual Setup

1. Create the database:
```sql
CREATE DATABASE context_cache;
```

2. The application will automatically create the required table when first run.

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| POSTGRES_HOST | localhost | PostgreSQL server host |
| POSTGRES_PORT | 5432 | PostgreSQL server port |
| POSTGRES_DB | context_cache | Database name |
| POSTGRES_USER | postgres | Database username |
| POSTGRES_PASSWORD | password | Database password |

## Usage

### Single Resume Analysis

```python
from utils.context_caching import analyze_two_files

result = analyze_two_files(
    "path/to/resume.pdf",  # PDF or DOCX file
    "path/to/job_description.pdf",  # PDF or DOCX file
    use_structured_output=True
)

print(result)  # JSON string with analysis results
```

### Batch Processing (Multiple Resumes)

#### Option 1: Using Batch API (50% cost savings)

```python
from utils.context_caching import analyze_bulk_resumes
from pathlib import Path

bulk_results = analyze_bulk_resumes(
    "path/to/job_description.pdf",  # PDF or DOCX file
    [
        "path/to/resume1.pdf",
        "path/to/resume2.pdf",
        "path/to/resume3.pdf",
        # Add more resume paths as needed
    ],
    use_structured_output=True,
    batch_method="inline"  # Use "inline" for small batches, "file" for large batches (>50 resumes)
)

# Process and display results
for resume_path, result in bulk_results.items():
    print(f"\n--- {Path(resume_path).name} ---")
    print(result)
```

#### Option 2: Using Parallel Processing (faster for smaller batches)

```python
from utils.context_caching import analyze_bulk_resumes_parallel
from pathlib import Path

parallel_results = analyze_bulk_resumes_parallel(
    "path/to/job_description.pdf",  # PDF or DOCX file
    [
        "path/to/resume1.pdf",
        "path/to/resume2.pdf",
        "path/to/resume3.pdf",
        # Add more resume paths as needed
    ],
    use_structured_output=True,
    max_workers=5  # Adjust based on your system's capabilities
)

# Process and display results
for resume_path, result in parallel_results.items():
    print(f"\n--- {Path(resume_path).name} ---")
    print(result)
```


## Output Structure

The system produces a structured JSON output with the following information:

```json
{
  "candidate_name": "Extracted from resume",
  "position_applied": "Extracted from job description",
  "company": "Extracted from job description",
  "overall_fit_score": 85,  // 0-100 score
  "recommendation": "APPROVED",  // APPROVED or REJECTED
  "fit_level": "HIGH_FIT",  // HIGH_FIT, MEDIUM_FIT, LOW_FIT, or NO_FIT
  "key_strengths": [
    "Strength 1",
    "Strength 2"
  ],
  "major_concerns": [
    "Concern 1",
    "Concern 2"
  ],
  "skills_assessment": {
    "required_skills_match": 90,  // 0-100 percentage
    "preferred_skills_match": 75,  // 0-100 percentage
    "critical_skills_missing": [
      "Missing skill 1",
      "Missing skill 2"
    ],
    "skill_gaps_impact": "Medium"  // Low, Medium, High, Critical
  },
  "experience_fit": {
    "years_required": 5,
    "years_candidate_has": 6,
    "experience_relevance": "High",  // High, Medium, Low, None
    "project_quality": "Good"  // Excellent, Good, Average, Poor
  },
  "hiring_decision_factors": {
    "technical_competency": 85,  // 0-100 score
    "experience_level": 90,  // 0-100 score
    "cultural_fit_indicators": 80,  // 0-100 score
    "growth_potential": 85,  // 0-100 score
    "immediate_productivity": 75  // 0-100 score
  },
  "evaluation_timestamp": "2023-07-01T12:34:56.789Z"  // Automatically added
}
```

## Implementation Details

- **Context Caching**: Uses Google's Context Cache feature for efficient document processing
- **Batch API**: Processes multiple resumes in batch mode at reduced cost
- **Structured Output**: Enforces consistent output format with a predefined JSON schema
- **Tenacity Retry**: Implements retry logic for handling connection issues
- **File Format Support**: Works with both PDF and DOCX files

## Troubleshooting

1. **SSL Connection Errors**: The system has built-in retry logic for connection issues, but if problems persist, try:
   - Check your internet connection
   - Verify your API key is valid
   - Try running with a smaller batch size

2. **Batch API Errors**: If you encounter batch API errors:
   - Start with "inline" batch method for testing
   - For large batches, use the "file" method
   - Check the error messages in the output for specific issues

3. **Input File Issues**:
   - Ensure PDF files are text-based (not scanned images)
   - For DOCX files, make sure they contain actual text content
   - Verify file paths are correct

## Dependencies

- google-generativeai
- python-docx
- tenacity
- python-dotenv
- pathlib

## License

MIT License

## Acknowledgements

This project uses Google's Gemini API for generative AI capabilities.
