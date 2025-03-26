import azure.functions as func
import logging
import json
import requests
import os
import base64
from models import JobResponse, JobRequest, JobStatusResponse, JobResultsResponse, ErrorResponse # Import models
from typing import Optional

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Configuration - should be moved to environment variables
TUSDATOS_API_BASE_URL = "https://docs.tusdatos.co/api"
TUSDATOS_API_USERNAME = os.environ.get("TUSDATOS_API_USERNAME", "pruebas")
TUSDATOS_API_PASSWORD = os.environ.get("TUSDATOS_API_PASSWORD", "password")

VALID_DOC_TYPES = {'CC', 'CE', 'INT', 'NIT', 'PP', 'PPT', 'NOMBRE'}

# Helper function to get headers
def get_headers():
    auth_str = f"{TUSDATOS_API_USERNAME}:{TUSDATOS_API_PASSWORD}"
    base64_auth = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    return {"Authorization": f"Basic {base64_auth}", "Content-Type": "application/json"}

@app.route(route="consult", methods=["POST"])
def consult(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing consult request')
    try:
        req_body = req.get_json()
        request_data = JobRequest(**req_body)
        
        payload = request_data.model_dump(exclude_none=True)
        response = requests.post(f"{TUSDATOS_API_BASE_URL}/launch", headers=get_headers(), json=payload)
        logging.info(f"Response: {response}")
        response_data = response.json()

        if response.status_code == 403 or response.status_code == 500:
            return func.HttpResponse(
                json.dumps({"error": response_data}), status_code=403, mimetype="application/json"
            )
        
        # Parse response into ConsultResponse model
        
        consult_response = JobResponse(**response_data)
        return func.HttpResponse(
            consult_response.json(), status_code=response.status_code, mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in consult endpoint: {str(e)}")
        return func.HttpResponse(json.dumps({"error": "Internal server error"}), status_code=500, mimetype="application/json")

@app.route(route="consult_status/{job_id}", methods=["GET"])
def consult_status(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing consult_status request')
    try:
        job_id = req.route_params.get('job_id')
        if not job_id:
            return func.HttpResponse("Job ID is required", status_code=400)
        
        response = requests.get(f"{TUSDATOS_API_BASE_URL}/results/{job_id}", headers=get_headers())
        response_data = response.json()

        if response.status_code == 400:
            # Parse response into ErrorResponse model
            response_data = response.json()
            error_response = ErrorResponse(**response_data)
            return func.HttpResponse(
                error_response.json(), status_code=400, mimetype="application/json"
            )
        
        # Parse response into JobStatusResponse model
        job_status_response = JobStatusResponse(**response_data)
        return func.HttpResponse(
            job_status_response.json(), status_code=response.status_code, mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in consult_status endpoint: {str(e)}")
        return func.HttpResponse("Internal server error", status_code=500)

@app.route(route="consult_results/{job_id}", methods=["GET"])
def consult_results(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing consult_results request')
    try:
        job_id = req.route_params.get('job_id')
        if not job_id:
            return func.HttpResponse("Job ID is required", status_code=400)
        
        response = requests.get(f"{TUSDATOS_API_BASE_URL}/report_json/{job_id}", headers=get_headers())
        response_data = response.json()

        if response.status_code == 400:
        # Parse response into ErrorResponse model
            
            error_response = ErrorResponse(**response_data)
            return func.HttpResponse(
                error_response.json(), status_code=400, mimetype="application/json"
            )
    
        results = {'job_id': job_id, 'data': response_data}
        consult_results_response = JobResultsResponse(**results)
        return func.HttpResponse(
            consult_results_response.json(), status_code=response.status_code, mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in consult_results endpoint: {str(e)}")
        return func.HttpResponse("Internal server error", status_code=500)