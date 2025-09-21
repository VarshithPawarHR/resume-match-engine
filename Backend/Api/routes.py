from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import List
import shutil
import os
import asyncio
import json
import zipfile
import tempfile
from pathlib import Path
from utils.context_caching import analyze_bulk_resumes_parallel
from utils import db_manager

router = APIRouter()

@router.post("/bulk-upload/")
async def bulk_upload_files(jd: UploadFile = File(...), resumes_zip: UploadFile = File(...), user_uuid: str = Form(...)):
    """
    Uploads a job description and a zip file containing multiple resumes for bulk processing.

    - **jd**: The job description PDF file.
    - **resumes_zip**: A zip file containing multiple resume PDF files.
    - **user_uuid**: Unique identifier for the user submitting the analysis
    """
    upload_folder = "uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Save JD file
    jd_filename = os.path.join(upload_folder, jd.filename)
    with open(jd_filename, "wb") as buffer:
        shutil.copyfileobj(jd.file, buffer)

    # Save and extract zip file
    zip_filename = os.path.join(upload_folder, resumes_zip.filename)
    with open(zip_filename, "wb") as buffer:
        shutil.copyfileobj(resumes_zip.file, buffer)

    # Extract resumes from zip
    resume_filenames = []
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_ref.extractall(temp_dir)
            
            # Find all PDF files in the extracted directory (recursive)
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        full_path = os.path.join(root, file)
                        # Copy to uploads directory
                        dest_path = os.path.join(upload_folder, f"resume_{len(resume_filenames)}_{file}")
                        shutil.copy2(full_path, dest_path)
                        resume_filenames.append(dest_path)

    # Process the resumes against the job description in a separate thread
    analysis_results = await asyncio.to_thread(
        analyze_bulk_resumes_parallel,
        jd_filename,
        resume_filenames,
        username=user_uuid
    )

    # Convert the dictionary of results into a list of objects
    formatted_results = []
    for key, value in analysis_results.items():
        try:
            # Parse the JSON string into a dictionary
            analysis_data = json.loads(value)
            formatted_results.append({
                "resume_file": os.path.basename(key),
                "analysis": analysis_data
            })
        except json.JSONDecodeError:
            # If parsing fails, keep it as a string
            formatted_results.append({
                "resume_file": os.path.basename(key),
                "analysis": value
            })

    return {"analysis_results": formatted_results}

@router.post("/upload/")
async def upload_single_files(jd: UploadFile = File(...), resume: UploadFile = File(...), user_uuid: str = Form(...)):
    """
    Uploads a job description and a single resume file (PDF or DOCX).

    - **jd**: The job description PDF file.
    - **resume**: A single resume file (PDF or DOCX).
    - **user_uuid**: Unique identifier for the user submitting the analysis
    """
    upload_folder = "uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Save JD file
    jd_filename = os.path.join(upload_folder, jd.filename)
    with open(jd_filename, "wb") as buffer:
        shutil.copyfileobj(jd.file, buffer)

    # Save resume file
    resume_filename = os.path.join(upload_folder, resume.filename)
    with open(resume_filename, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)

    resume_filenames = [resume_filename]

    # Process the resume against the job description in a separate thread
    analysis_results = await asyncio.to_thread(
        analyze_bulk_resumes_parallel,
        jd_filename,
        resume_filenames,
        username=user_uuid
    )

    # Convert the dictionary of results into a list of objects
    formatted_results = []
    for key, value in analysis_results.items():
        try:
            # Parse the JSON string into a dictionary
            analysis_data = json.loads(value)
            formatted_results.append({
                "resume_file": os.path.basename(key),
                "analysis": analysis_data
            })
        except json.JSONDecodeError:
            # If parsing fails, keep it as a string
            formatted_results.append({
                "resume_file": os.path.basename(key),
                "analysis": value
            })

    return {"analysis_results": formatted_results}


@router.get("/results/{user_uuid}")
async def get_user_results(user_uuid: str):
    """
    Retrieves all analysis results for a specific user UUID from the database.
    Returns only essential data without unnecessary internal fields.
    
    - **user_uuid**: The unique identifier for the user whose results you want to retrieve
    """
    try:
        # Get user data from PostgreSQL database
        user_data = await asyncio.to_thread(db_manager.get_user_data, user_uuid)
        
        if not user_data:
            raise HTTPException(status_code=404, detail=f"No data found for user UUID: {user_uuid}")
        
        # Extract analysis results from user data
        analysis_results = user_data.get('data', {}).get('analysis_results', [])
        
        if not analysis_results:
            raise HTTPException(status_code=404, detail=f"No analysis results found for user UUID: {user_uuid}")
        
        # Clean the results - remove unnecessary internal fields
        cleaned_results = []
        for result in analysis_results:
            try:
                # Parse the result JSON to get the actual analysis data
                if isinstance(result.get('result_json'), str):
                    analysis_data = json.loads(result['result_json'])
                else:
                    analysis_data = result.get('result_json', {})
                
                # Create cleaned result with only essential fields
                cleaned_result = {
                    "analysis_id": result.get('id'),
                    "processed_at": result.get('processed_at'),
                    "candidate_name": analysis_data.get('candidate_name'),
                    "position_applied": analysis_data.get('position_applied'),
                    "company": analysis_data.get('company'),
                    "overall_fit_score": analysis_data.get('overall_fit_score'),
                    "recommendation": analysis_data.get('recommendation'),
                    "fit_level": analysis_data.get('fit_level'),
                    "key_strengths": analysis_data.get('key_strengths', []),
                    "major_concerns": analysis_data.get('major_concerns', []),
                    "skills_assessment": analysis_data.get('skills_assessment', {}),
                    "experience_fit": analysis_data.get('experience_fit', {}),
                    "hiring_decision_factors": analysis_data.get('hiring_decision_factors', {}),
                    "evaluation_timestamp": analysis_data.get('evaluation_timestamp')
                }
                cleaned_results.append(cleaned_result)
                
            except (json.JSONDecodeError, KeyError) as e:
                # If there's an issue parsing, include basic info
                cleaned_results.append({
                    "analysis_id": result.get('id'),
                    "processed_at": result.get('processed_at'),
                    "error": "Failed to parse analysis data"
                })
        
        return {
            "user_uuid": user_uuid,
            "total_results": len(cleaned_results),
            "analyses": cleaned_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
