import requests
import base64
import os
from models import BackgroundCheckRequest, BackgroundCheckResponse, CheckStatusResponse
from db_operations import get_pending_checks, update_check_status
import logging

# Configuration - should be moved to environment variables
TUSDATOS_API_BASE_URL = os.environ.get("TUSDATOS_API_URL", "https://docs.tusdatos.co/api")
TUSDATOS_API_USERNAME = os.environ.get("TUSDATOS_API_USERNAME", "pruebas")
TUSDATOS_API_PASSWORD = os.environ.get("TUSDATOS_API_PASSWORD", "password")

VALID_DOC_TYPES = {'CC', 'CE', 'INT', 'NIT', 'PP', 'PPT', 'NOMBRE'}

# Helper function to get headers
def get_headers():
    auth_str = f"{TUSDATOS_API_USERNAME}:{TUSDATOS_API_PASSWORD}"
    base64_auth = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    return {"Authorization": f"Basic {base64_auth}", "Content-Type": "application/json"}

def launch_verify(request_data: BackgroundCheckRequest) -> BackgroundCheckResponse:
    """
    Function to launch a background check request.
    """
    if request_data.typedoc not in VALID_DOC_TYPES:
        return 400, f"Invalid document type: {request_data.typedoc}. Must be one of {VALID_DOC_TYPES}."
    
    payload = request_data.model_dump(exclude_none=True)
    response = requests.post(f"{TUSDATOS_API_BASE_URL}/launch", headers=get_headers(), json=payload)
    
    if response.status_code == 200:
        response_data = response.json()
        return response.status_code, BackgroundCheckResponse(**response_data)
    else:
        return response.status_code, response.text

def get_job_status(job_id) -> CheckStatusResponse:
    """
    Function to get the status of a job using its job ID.
    """
    # Assuming TUSDATOS_API_BASE_URL and get_headers() are defined elsewhere
    # mocked_jobid = "6460fc34-4154-43db-9438-8c5a059304c0"
    response = requests.get(f"{TUSDATOS_API_BASE_URL}/results/{job_id}", headers=get_headers())
    
    if response.status_code == 200:
        status_data = response.json()
        status_model = CheckStatusResponse(**status_data)
        return status_model
    else:
        return None

def sync_pending_checks(user_id):
    """
    Function to sync the check status of a user.
    """
    checks_list = get_pending_checks(user_id)
    if not checks_list:
        return {"message": "No pending checks found."}
    
    for check in checks_list:
        check_id = check['id']
        job_id = check['jobid']
        c_state = check['status']
        # Assuming TUSDATOS_API_BASE_URL and get_headers() are defined elsewhere
        status_data = get_job_status(job_id)   
        
        if not status_data:
            update_check_status(check_id, 'error')
        elif status_data.estado != c_state: 
            update_check_status(check_id, status_data.estado)
    return True

def launch_check_results(job_id):
    """
    Function to get the results of a check using its check ID.
    """

    # Assuming TUSDATOS_API_BASE_URL and get_headers() are defined elsewhere
    response = requests.get(f"{TUSDATOS_API_BASE_URL}/report_json/{job_id}", headers=get_headers())
    return response