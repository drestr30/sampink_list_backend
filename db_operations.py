import psycopg2
import json
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
load_dotenv('.env')

# Database connection function
def connect_db():
    connection_string = os.getenv("DB_CONNECTION_STRING")
    return psycopg2.connect(
        connection_string,
        cursor_factory=RealDictCursor
    )

# Function to save a request
def save_request(jobid, request_payload: dict) -> int:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lists_requests (job_id, user_id,  request_payload, timestamp)
                VALUES (%s, %s, NOW())
                RETURNING id
                """,
                (jobid, json.dumps(request_payload))
            )
            request_id = cursor.fetchone()["id"]
        conn.commit()
        return request_id
    finally:
        conn.close()

# Function to save a response
def save_response(jobid: int, response_payload: dict):
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            # Get the request_id from the requests table where jobid matches
            cursor.execute(
                """
                SELECT id FROM requests WHERE job_id = %s
                """,
                (jobid,)
            )
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"No request found with jobid {jobid}")
            
            request_id = result["id"]

            # Insert the response into the responses table
            cursor.execute(
                """
                INSERT INTO lists_responses (request_id, response_payload, timestamp)
                VALUES (%s, %s, NOW())
                """,
                (request_id, json.dumps(response_payload))
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == '__main__': 
    conn =  connect_db()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM requests")
        rows = cursor.fetchall()
        for row in rows:
            print(row)

