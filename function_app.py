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
from db_operations import create_user, get_user_id

from tusdatos_client import launch_verify, sync_pending_checks, launch_check_results

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="backgroundCheck", methods=["POST"])
def backgroundCheck(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing consult request')
    try:
        req_body = req.get_json()['checks']
        user_id = -1  # Replace with actual user ID retrieval logic
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
            _ = sync_pending_checks(user_id)

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
        if not check_id:
            return func.HttpResponse("check_id is required", status_code=400)
        check_results = get_check_results(check_id)

        if not check_results:
            check = get_check(check_id)

            if check['status'] == 'finalizado':
                mocked_jobid = "651c2ede72476080772781f5"
            else: 
                mocked_jobid = check['jobid']   
            results_response = launch_check_results(mocked_jobid) #get_check_results(check_id)
            
            if results_response.status_code != 200:
                return func.HttpResponse(
                    results_response.text, status_code=results_response.status_code, mimetype=results_response.headers.get("Content-Type", "application/json")
                )
            
            results_data = results_response.json()
            # Save data to db
            save_backgroundCheck_result(check_id, 
                                    doc=check['document'],
                                    hallazgos_altos=len(results_data['dict_hallazgos']['altos']) if 'dict_hallazgos' in results_data else 0,
                                    hallazgos_medios=len(results_data['dict_hallazgos']['medios']) if 'dict_hallazgos' in results_data else 0,
                                    hallazgos_bajos=len(results_data['dict_hallazgos']['bajos']) if 'dict_hallazgos' in results_data else 0,
                                    response_payload=results_data)
            results_data = json.dumps(results_data)
        else: 
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
        if not req_body or 'username' not in req_body:
            return func.HttpResponse("username Email is required", status_code=400)

        username = req_body['username']
        user_id = get_user_id(username)

        if user_id:
            return func.HttpResponse(
                json.dumps({'status': 'User already exists.'}),
                status_code=400, mimetype="application/json"
            )
        
        # Create a new user
        user_id = create_user(username)
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

@app.route(route="getUserId", methods=["POST"])
def getUserId(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing getUserId request')
    try:
        req_body = req.get_json()
        if not req_body or 'username' not in req_body:
            return func.HttpResponse("Email is required", status_code=400)

        username = req_body['username']
        user_id = get_user_id(username)

        if not user_id:
            return func.HttpResponse(
                json.dumps({'status': 'failed', 'message': 'User not found'}),
                status_code=404, mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({'status': 'success', 'user_id': user_id}),
            status_code=200, mimetype="application/json"
        )

    except Exception as e:
        logging.error(traceback.format_exc())   
        logging.error(f"Error in getUserId endpoint: {str(e)}")
        return func.HttpResponse(f"Internal server error : {str(e)}", status_code=500)