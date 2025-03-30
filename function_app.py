import azure.functions as func
import logging
import json
import requests
import os
import base64
from models import * # Import models
from typing import Optional
import traceback
from dotenv import load_dotenv

# Load environment variables from the .env file (if present)
# load_dotenv('.env')

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

@app.route(route="backgroundCheck", methods=["POST"])
def backgroundCheck(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing consult request')
    try:
        req_body = req.get_json()
        request_data = BackgroundCheckRequest(**req_body)
        
        payload = request_data.model_dump(exclude_none=True)
        response = requests.post(f"{TUSDATOS_API_BASE_URL}/launch", headers=get_headers(), json=payload)
        logging.info(f"Response: {response}")
        
        if response.status_code != 200:
            return func.HttpResponse(
                response.text, status_code=response.status_code, mimetype=response.headers.get("Content-Type", "application/json")
            )
        
        response_data = response.json()
        consult_response = BackgroundCheckResponse(**response_data)
        return func.HttpResponse(
            consult_response.model_dump_json(), status_code=response.status_code, mimetype="application/json"
        )
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(f"Error in consult endpoint: {str(e)}")
        return func.HttpResponse(json.dumps({"error": f"Internal server error {str(e)}"}), status_code=500, mimetype="application/json")

@app.route(route="backgroundCheckResult/{jobid}", methods=["GET"])
def backgroundCheckResult(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing consult_status request')
    try:
        jobid = req.route_params.get('jobid')
        if not jobid:
            return func.HttpResponse("Job ID is required", status_code=400)
        
        # Step 1: Check the status of the background check
        status_response  = requests.get(f"{TUSDATOS_API_BASE_URL}/results/{jobid}", headers=get_headers())
        logging.info(f"Status Code: {status_response.status_code}")

        if status_response.status_code != 200:
            return func.HttpResponse(
                status_response.text, status_code=status_response.status_code, mimetype=status_response.headers.get("Content-Type", "application/json")
            )
        
        status_data = status_response.json()
        # Parse status response into the model
        status_model = CheckResultResponse(**status_data)
        logging.info(f"Status: {status_model.estado.lower()}")
        
        # If status is not completed, return only the status response
        if status_model.estado.lower() != "finalizado":
            return func.HttpResponse(
                status_model.model_dump_json(), 
                status_code=200, mimetype="application/json"
            )
        
         # Step 2: Fetch the final results if the check is complete
        results_response = requests.get(f"{TUSDATOS_API_BASE_URL}/report_json/{jobid}", headers=get_headers())
        logging.info(f"Results Status Code: {results_response.status_code}")
        
        if results_response.status_code != 200:
            return func.HttpResponse(
                json.dumps({"job_id": jobid, "status": status_model.dict(), "error": results_response.text}), 
                status_code=results_response.status_code, mimetype="application/json"
            )
        
        results_data = results_response.json()
        logging.info(f"Results Response: {results_data}")

        # Attach the final data to the response model
        status_model.data = results_data

        return func.HttpResponse(
            status_model.model_dump_json(),
            status_code=200, mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in backgroundCheckStatus endpoint: {str(e)}")
        return func.HttpResponse(f"Internal server error : {str(e)}", status_code=500)

# @app.route(route="backgroundCheckResults/{jobid}", methods=["GET"])
# def consult_results(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Processing consult_results request')
#     try:
#         jobid = req.route_params.get('jobid')
#         if not jobid:
#             return func.HttpResponse("Job ID is required", status_code=400)
        
#         response = requests.get(f"{TUSDATOS_API_BASE_URL}/report_json/{jobid}", headers=get_headers())
#         response_data = response.json()

#         if response.status_code == 400:
#         # Parse response into ErrorResponse model
            
#             error_response = ErrorResponse(**response_data)
#             return func.HttpResponse(
#                 error_response.json(), status_code=400, mimetype="application/json"
#             )
    
#         results = {'job_id': job_id, 'data': response_data}
#         consult_results_response = JobResultsResponse(**results)
#         return func.HttpResponse(
#             consult_results_response.json(), status_code=response.status_code, mimetype="application/json"
#         )
#     except Exception as e:
#         logging.error(f"Error in consult_results endpoint: {str(e)}")
#         return func.HttpResponse("Internal server error", status_code=500)