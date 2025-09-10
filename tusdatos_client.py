import requests
import base64
import os
from models import BackgroundCheckRequest, BackgroundCheckResponse, CheckStatusResponse
from db_operations import * #get_pending_checks, update_check_status, get_check, save_backgroundCheck_result
import logging
import json
logging.basicConfig(level=logging.INFO)

# from dotenv import load_dotenv
# load_dotenv(".env")

# Configuration - should be moved to environment variables
TUSDATOS_API_BASE_URL = os.environ.get("TUSDATOS_API_BASE_URL", "https://docs.tusdatos.co/api")
TUSDATOS_API_USERNAME = os.environ.get("TUSDATOS_API_USERNAME", "pruebas")
TUSDATOS_API_PASSWORD = os.environ.get("TUSDATOS_API_PASSWORD", "password")

VALID_DOC_TYPES = {'CC', 'CE', 'INT', 'NIT', 'PP', 'PPT', 'NOMBRE'}

# Helper function to get headers
def get_headers():
    logging.info(f"Using TUSDATOS_API_BASE_URL: {TUSDATOS_API_BASE_URL}")
    logging.info(f"Using TUSDATOS_API_USERNAME: {TUSDATOS_API_USERNAME}")
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
        logging.info(f"Background check launched successfully {response}.")
        logging.debug(f"Response data: {response_data}")

        if response_data.get('jobid', None):
            status = 'procesando'
            jobid = response_data['jobid']
            id = None
        elif response_data.get('id'):
            status = 'finalizado'
            jobid = None
            id = response_data['id']
        else:  
            status = 'error'
            jobid = None
            id = None
        response_data = json.dumps(response_data, indent=4, ensure_ascii=False)
    
    else: 
        logging.error(f"Error launching background check: {response.text}")
        status = 'error'
        jobid = None    
        id = None
        response_data = response.text

    response_dict = {
        "id": id,
        "jobid": jobid,
        "status": status,
        "response_data": response_data
    }

    return response.status_code, response_dict

def get_job_status(job_id) -> str:
    """
    Function to get the status of a job using its job ID.
    """
    # Assuming TUSDATOS_API_BASE_URL and get_headers() are defined elsewhere
    # mocked_jobid = "6460fc34-4154-43db-9438-8c5a059304c0"
    response = requests.get(f"{TUSDATOS_API_BASE_URL}/results/{job_id}", headers=get_headers())
    
    if response.status_code == 200:
        status_data = response.json()
        # status_model = CheckStatusResponse(**status_data)
        return status_data
    else:
        return response.json()

def sync_pending_checks(user_id):
    """
    Function to sync the check status of a user.
    """
    checks_list = get_pending_checks(user_id)
    if not checks_list:
        return {"message": "No pending checks found."}
    
    _state_changed = False
    for check in checks_list:
        check_id = check['id']
        job_id = check['jobid']
        c_state = check['status']
        # Assuming TUSDATOS_API_BASE_URL and get_headers() are defined elsewhere
        max_retries = 3
        retry_count = 0
        status_data = None

        while retry_count < max_retries:
            status_data = get_job_status(job_id)
            if status_data is not None:
                break
            retry_count += 1
            logging.warning(f"Retry {retry_count}/{max_retries} for check_id {check_id} with job_id {job_id}")
        
        if status_data is None:
            error_text = f"Failed to fetch status for check_id {check_id} with job_id {job_id} after {max_retries} retries."
            update_status_response(check_id, error_text)
            update_check_status(check_id, 'procesando')
            logging.error(error_text)
            continue

        update_status_response(check_id, json.dumps(status_data))

        try:
            if status_data['estado'] == 'finalizado':
                update_check_result_id(check_id, status_data['id'])

            if status_data['estado'] != c_state:
                update_check_status(check_id, status_data['estado'])
                _state_changed = True
        except KeyError as e:
            logging.error(f"KeyError for check_id {check_id} with job_id {job_id}: {e}")
            update_check_status(check_id, 'error')
            continue
    return _state_changed

def launch_check_results(job_id):
    """
    Function to get the results of a check using its check ID.
    """

    # Assuming TUSDATOS_API_BASE_URL and get_headers() are defined elsewhere
    try:
        response = requests.get(f"{TUSDATOS_API_BASE_URL}/report_json/{job_id}", headers=get_headers())
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f"Error fetching check results for job_id {job_id}: {e}")
        return None

def update_pending_results(user_id):    
    check_ids = get_user_outdated_results(user_id)

    for check_id in check_ids:
        check = get_check(check_id)

        job_id = check['result_id']   

        results_response = launch_check_results(job_id) #get_check_results(check_id)

        results_data = results_response.json()
        # Save data to db
        save_backgroundCheck_result(check_id, 
                                doc=check['document'],
                                hallazgos_altos=len(results_data['dict_hallazgos']['altos']) if 'dict_hallazgos' in results_data else 0,
                                hallazgos_medios=len(results_data['dict_hallazgos']['medios']) if 'dict_hallazgos' in results_data else 0,
                                hallazgos_bajos=len(results_data['dict_hallazgos']['bajos']) if 'dict_hallazgos' in results_data else 0,
                                response_payload=results_data)
    return results_data