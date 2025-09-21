import psycopg2
import psycopg2.extras
import json
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters - you can set these via environment variables
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'context_cache')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')

def get_db_connection():
    """Create a connection to the PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        # Return dictionary-like rows
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize the database with the simplified user_data table"""
    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            # Create the simplified user_data table with only 2 columns
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                user_id TEXT PRIMARY KEY,
                data JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Create an index on user_id for faster lookups
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_data_user_id ON user_data(user_id)
            ''')

            # Create an index on the data JSONB column for efficient queries
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_data_data ON user_data USING GIN(data)
            ''')

        conn.commit()
        print("PostgreSQL database initialized successfully.")
    except psycopg2.Error as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_or_create_user(username):
    """Get a user by username or create if not exists"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Try to get existing user
            cursor.execute('SELECT user_id, data FROM user_data WHERE user_id = %s', (username,))
            user = cursor.fetchone()

            if user:
                return {'id': user['user_id'], 'username': user['user_id']}

            # Create new user if not exists
            cursor.execute('''
            INSERT INTO user_data (user_id, data)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO NOTHING
            ''', (username, psycopg2.extras.Json({})))

            conn.commit()
            return {'id': username, 'username': username}
    except psycopg2.Error as e:
        print(f"Error in get_or_create_user: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def save_file_record(user_id, filename, file_path, file_type, mime_type, gemini_file_id=None):
    """Save a record of an uploaded file to the user's data"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current user data
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result:
                # Create user if doesn't exist
                user_data = {}
            else:
                user_data = result['data'] or {}

            # Initialize files array if it doesn't exist
            if 'files' not in user_data:
                user_data['files'] = []

            # Create file record
            file_record = {
                'id': len(user_data['files']) + 1,  # Simple ID generation
                'filename': filename,
                'file_path': file_path,
                'file_type': file_type,
                'mime_type': mime_type,
                'gemini_file_id': gemini_file_id,
                'upload_timestamp': datetime.now().isoformat()
            }

            user_data['files'].append(file_record)

            # Update user data
            cursor.execute('''
            UPDATE user_data
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            ''', (psycopg2.extras.Json(user_data), user_id))

            conn.commit()
            return file_record['id']
    except psycopg2.Error as e:
        print(f"Error in save_file_record: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_files(user_id, file_type=None):
    """Get all files uploaded by a user, optionally filtered by file type"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result or not result['data']:
                return []

            user_data = result['data']
            files = user_data.get('files', [])

            if file_type:
                files = [f for f in files if f.get('file_type') == file_type]

            return files
    except psycopg2.Error as e:
        print(f"Error in get_user_files: {e}")
        raise
    finally:
        conn.close()

def save_cache_record(user_id, cache_name, display_name, jd_file_id, resume_file_id, ttl=1800):
    """Save a record of a created Gemini cache to the user's data"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current user data
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result:
                user_data = {}
            else:
                user_data = result['data'] or {}

            # Initialize caches array if it doesn't exist
            if 'caches' not in user_data:
                user_data['caches'] = []

            # Create cache record
            cache_record = {
                'id': len(user_data['caches']) + 1,  # Simple ID generation
                'cache_name': cache_name,
                'display_name': display_name,
                'jd_file_id': jd_file_id,
                'resume_file_id': resume_file_id,
                'ttl': ttl,
                'created_at': datetime.now().isoformat()
            }

            user_data['caches'].append(cache_record)

            # Update user data
            cursor.execute('''
            UPDATE user_data
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            ''', (psycopg2.extras.Json(user_data), user_id))

            conn.commit()
            return cache_record['id']
    except psycopg2.Error as e:
        print(f"Error in save_cache_record: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_caches(user_id):
    """Get all caches created by a user"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result or not result['data']:
                return []

            user_data = result['data']
            caches = user_data.get('caches', [])

            # Enrich cache data with file information
            files = user_data.get('files', [])
            file_map = {f['id']: f for f in files}

            for cache in caches:
                if cache.get('jd_file_id') and cache['jd_file_id'] in file_map:
                    cache['jd_filename'] = file_map[cache['jd_file_id']].get('filename')
                if cache.get('resume_file_id') and cache['resume_file_id'] in file_map:
                    cache['resume_filename'] = file_map[cache['resume_file_id']].get('filename')

            return caches
    except psycopg2.Error as e:
        print(f"Error in get_user_caches: {e}")
        raise
    finally:
        conn.close()

def save_analysis_result(user_id, cache_id, jd_file_id, resume_file_id, result_json):
    """Save an analysis result to the user's data"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current user data
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result:
                user_data = {}
            else:
                user_data = result['data'] or {}

            # Initialize analysis_results array if it doesn't exist
            if 'analysis_results' not in user_data:
                user_data['analysis_results'] = []

            # Try to extract score and recommendation from JSON
            score = None
            recommendation = None

            try:
                result_data = json.loads(result_json)
                if isinstance(result_data, dict):
                    score = result_data.get('overall_fit_score')
                    recommendation = result_data.get('recommendation')
            except (json.JSONDecodeError, AttributeError):
                pass

            # Create analysis result record
            analysis_record = {
                'id': len(user_data['analysis_results']) + 1,  # Simple ID generation
                'cache_id': cache_id,
                'jd_file_id': jd_file_id,
                'resume_file_id': resume_file_id,
                'result_json': result_json,
                'score': score,
                'recommendation': recommendation,
                'processed_at': datetime.now().isoformat()
            }

            user_data['analysis_results'].append(analysis_record)

            # Update user data
            cursor.execute('''
            UPDATE user_data
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            ''', (psycopg2.extras.Json(user_data), user_id))

            conn.commit()
            return analysis_record['id']
    except psycopg2.Error as e:
        print(f"Error in save_analysis_result: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_analysis_results(user_id, limit=None):
    """Get analysis results for a user, optionally limited to a number of recent results"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result or not result['data']:
                return []

            user_data = result['data']
            analysis_results = user_data.get('analysis_results', [])

            # Sort by processed_at in descending order
            analysis_results.sort(key=lambda x: x.get('processed_at', ''), reverse=True)

            if limit:
                analysis_results = analysis_results[:limit]

            # Enrich with file information
            files = user_data.get('files', [])
            file_map = {f['id']: f for f in files}

            for result in analysis_results:
                if result.get('jd_file_id') and result['jd_file_id'] in file_map:
                    result['jd_filename'] = file_map[result['jd_file_id']].get('filename')
                if result.get('resume_file_id') and result['resume_file_id'] in file_map:
                    result['resume_filename'] = file_map[result['resume_file_id']].get('filename')

            return analysis_results
    except psycopg2.Error as e:
        print(f"Error in get_user_analysis_results: {e}")
        raise
    finally:
        conn.close()

def get_analysis_result_by_id(user_id, result_id):
    """Get a specific analysis result by ID for a user"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result or not result['data']:
                return None

            user_data = result['data']
            analysis_results = user_data.get('analysis_results', [])

            # Find the specific result
            for result in analysis_results:
                if result.get('id') == result_id:
                    # Enrich with file information
                    files = user_data.get('files', [])
                    file_map = {f['id']: f for f in files}

                    if result.get('jd_file_id') and result['jd_file_id'] in file_map:
                        result['jd_filename'] = file_map[result['jd_file_id']].get('filename')
                    if result.get('resume_file_id') and result['resume_file_id'] in file_map:
                        result['resume_filename'] = file_map[result['resume_file_id']].get('filename')

                    result['username'] = user_id
                    return result

            return None
    except psycopg2.Error as e:
        print(f"Error in get_analysis_result_by_id: {e}")
        raise
    finally:
        conn.close()

def save_batch_job(user_id, job_name, job_state, num_requests):
    """Save a record of a batch job to the user's data"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current user data
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result:
                user_data = {}
            else:
                user_data = result['data'] or {}

            # Initialize batch_jobs array if it doesn't exist
            if 'batch_jobs' not in user_data:
                user_data['batch_jobs'] = []

            # Create batch job record
            batch_job_record = {
                'id': len(user_data['batch_jobs']) + 1,  # Simple ID generation
                'job_name': job_name,
                'job_state': job_state,
                'num_requests': num_requests,
                'created_at': datetime.now().isoformat(),
                'completed_at': None
            }

            user_data['batch_jobs'].append(batch_job_record)

            # Update user data
            cursor.execute('''
            UPDATE user_data
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            ''', (psycopg2.extras.Json(user_data), user_id))

            conn.commit()
            return batch_job_record['id']
    except psycopg2.Error as e:
        print(f"Error in save_batch_job: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def update_batch_job_status(user_id, job_id, job_state, completed_at=None):
    """Update the status of a batch job for a user"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current user data
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result or not result['data']:
                return

            user_data = result['data']
            batch_jobs = user_data.get('batch_jobs', [])

            # Find and update the batch job
            for job in batch_jobs:
                if job.get('id') == job_id:
                    job['job_state'] = job_state
                    if completed_at is None and job_state in ['JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED']:
                        job['completed_at'] = datetime.now().isoformat()
                    else:
                        job['completed_at'] = completed_at
                    break

            # Update user data
            cursor.execute('''
            UPDATE user_data
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            ''', (psycopg2.extras.Json(user_data), user_id))

            conn.commit()
    except psycopg2.Error as e:
        print(f"Error in update_batch_job_status: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_batch_jobs(user_id):
    """Get all batch jobs for a user"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT data FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if not result or not result['data']:
                return []

            user_data = result['data']
            batch_jobs = user_data.get('batch_jobs', [])

            # Sort by created_at in descending order
            batch_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            return batch_jobs
    except psycopg2.Error as e:
        print(f"Error in get_user_batch_jobs: {e}")
        raise
    finally:
        conn.close()

def get_user_data(user_id):
    """Get all data for a specific user"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT user_id, data, created_at, updated_at FROM user_data WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()

            if result:
                return dict(result)
            return None
    except psycopg2.Error as e:
        print(f"Error in get_user_data: {e}")
        raise
    finally:
        conn.close()

def update_user_data(user_id, data):
    """Update the data for a specific user"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
            UPDATE user_data
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            ''', (psycopg2.extras.Json(data), user_id))
            conn.commit()
    except psycopg2.Error as e:
        print(f"Error in update_user_data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

# Initialize the database when this module is imported
init_db()