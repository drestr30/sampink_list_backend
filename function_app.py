import azure.functions as func
import logging
import json
from models import BackgroundCheckRequest
import traceback
from db_operations import (save_backgroundCheck_request, 
                        get_user_credits, 
                        update_user_credits, 
                        get_user_checks, 
                        get_user_processing_status, 
                        get_check, get_check_results,
                        save_backgroundCheck_result)
from db_operations import create_user, get_user_id, get_user_password
from tusdatos_client import launch_verify, sync_pending_checks, update_pending_results

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="backgroundCheck", methods=["POST"])
def backgroundCheck(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing consult request')
    try:
        req_body = req.get_json()['checks']
        user_id = req.get_json()['user_id']
        if not req_body or not user_id:
            return func.HttpResponse("User ID and checks are required", status_code=400)
        
        request_ids = []
        current_user_credits = get_user_credits(user_id)
        logging.info(f"User {user_id} has {current_user_credits} credits.")

        for item in req_body:
            if current_user_credits <= 0:
                logging.warning(f"User {user_id} has insufficient credits to process further requests.")
                break
            current_user_credits = current_user_credits -1

            request_data = BackgroundCheckRequest(**item)
            status_code, response = launch_verify(request_data)   
            logging.info(f"Response: {response}")

            if status_code != 200:
                status = 'failed'
                jobid = None
                response_text = response
            else:
                status = 'procesando' #if response.validado == True else 'error'
                jobid = str(response.jobid)
                response_text = str(response.model_dump())

            # Save the request to the database
            request_id = save_backgroundCheck_request(userid=user_id,
                                                        document=request_data.doc,
                                                        typedoc=request_data.typedoc,
                                                        payload=request_data.model_dump(),
                                                        jobid=jobid,
                                                        status=status,
                                                        response_code=status_code,
                                                        response_content=response_text)
            request_ids.append({'id': request_id,'doc': request_data.doc,  'status': status, 'response': response_text})

            # Update user credits in the database
            # logging.info(f"User {user_id} has {current_user_credits} credits after processing requests.")   
            update_user_credits(user_id, current_user_credits)

        if not request_ids:
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'No requests processed due to insufficient credits'}),
                status_code=400, mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({'status': 'success', 'request_ids': request_ids}),
            status_code=200, mimetype="application/json"
        )

    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(f"Error in consult endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error {str(e)}"}), 
            status_code=500, mimetype="application/json"
        )

@app.route(route="getUserChecks/{user_id}", methods=["GET"])
def getUserChecks(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing getUserChecks request')

    try:
        user_id = req.route_params.get('user_id')
        if not user_id:
            return func.HttpResponse("User ID is required", status_code=400)
        
        # Step 1: Check the status of the background check
        checks_list = get_user_checks(user_id)

        if not checks_list:
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'No pending checks found'}),
                status_code=404, mimetype="application/json"
            )

        return func.HttpResponse(
                json.dumps({'status': 'success', 'checks': checks_list}),
                status_code=200, mimetype="application/json"
            )

    except Exception as e:
        logging.error(f"Error in getUserChecks endpoint: {str(e)}")
        return func.HttpResponse(f"Internal server error : {str(e)}", status_code=500)

@app.route(route="backgroundCheckSyncStatus/{user_id}", methods=["GET"])
def backgroundCheckSyncStatus(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing userIsProcessing request')

    try:
        user_id = req.route_params.get('user_id')
        if not user_id:
            return func.HttpResponse("User ID is required", status_code=400)
        
        # Step 1: Check the status of the background check
        needs_sync = get_user_processing_status(user_id)
        logging.info(f"User {user_id} is processing: {needs_sync}")    
        if needs_sync:
            _state_changed = sync_pending_checks(user_id)
            if _state_changed:
                update_pending_results(user_id)

        return func.HttpResponse(
                json.dumps({'status': 'success', 'processing': needs_sync}),
                status_code=200, mimetype="application/json"
            )
    except Exception as e:
        logging.error(traceback.format_exc())   
        logging.error(f"Error in userIsProcessing endpoint: {str(e)}")
        return func.HttpResponse(f"Internal server error : {str(e)}", status_code=500)

@app.route(route="backgroundCheckResults/{check_id}", methods=["GET"])
def backgroundCheckResults(req: func.HttpRequest) -> func.HttpResponse:
        
    try: 
        check_id = req.route_params.get('check_id')
        logging.info(f"Processing backgroundCheckResults request for check_id: {check_id}")
        if not check_id:
            return func.HttpResponse("check_id is required", status_code=400)
        check_results = get_check_results(check_id)

        if not check_results:
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'No results found for the given check_id'}),
                status_code=404, mimetype="application/json"
            )

        results_data = check_results['response_payload']

        return func.HttpResponse(
            results_data,
            status_code=200, mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(traceback.format_exc())   
        logging.error(f"Error in backgroundCheckResults endpoint: {str(e)}")
        return func.HttpResponse(f"Internal server error : {str(e)}", status_code=500)
    
@app.route(route="registerUser", methods=["POST"])
def registerUser(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing registerUser request')
    try:
        req_body = req.get_json()
        if not req_body or 'username' not in req_body or 'password' not in req_body:
            return func.HttpResponse("Username and password are required", status_code=400)

        username = req_body['username']
        password = req_body['password']
        user_id = get_user_id(username)

        if user_id:
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'User already exists'}),
                status_code=400, mimetype="application/json"
            )
        
        # Hash the password securely
        hashed_password = generate_password_hash(password)

        # Create a new user with the hashed password
        user_id = create_user(username, hashed_password)
        if not user_id:
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'Failed to create user'}),
                status_code=500, mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({'status': 'success', 'user_id': user_id}),
            status_code=200, mimetype="application/json"
        )

    except Exception as e:
        logging.error(traceback.format_exc())   
        logging.error(f"Error in registerUser endpoint: {str(e)}")
        return func.HttpResponse(f"Internal server error : {str(e)}", status_code=500)

@app.route(route="login", methods=["POST"])
def login(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing login request')
    try:
        req_body = req.get_json()
        if not req_body or 'username' not in req_body or 'password' not in req_body:
            return func.HttpResponse("Username and password are required", status_code=400)

        username = req_body['username']
        password = req_body['password']
        user_id = get_user_id(username)

        if not user_id:
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'Invalid username or password'}),
                status_code=401, mimetype="application/json"
            )

        # Retrieve the stored hashed password for the user
        stored_hashed_password = get_user_password(user_id)  # Implement this function to fetch the hashed password

        # Validate the provided password against the stored hash
        if not check_password_hash(password, stored_hashed_password):
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'Invalid username or password'}),
                status_code=401, mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({'status': 'success', 'user_id': user_id}),
            status_code=200, mimetype="application/json"
        )

    except Exception as e:
        logging.error(traceback.format_exc())   
        logging.error(f"Error in login endpoint: {str(e)}")
        return func.HttpResponse(f"Internal server error : {str(e)}", status_code=500)
    
import hashlib
def check_password_hash(password, hashed_password):
    # Hash the provided password using SHA-256
    hashed_input_password = hashlib.sha256(password.encode()).hexdigest()

    # Compare the hashed input password with the stored hashed password
    return hashed_input_password == hashed_password

def generate_password_hash(password):
    # Hash the password using SHA-256
    return hashlib.sha256(password .encode()).hexdigest()   