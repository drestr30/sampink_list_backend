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
def save_backgroundCheck_request(userid: int, document: str, typedoc: str, payload: dict, jobid:str, status: str , response_code:int, response_content:str) -> int:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO backgroundcheck_requests (userid, document, typedoc, payload, jobid, status, timestamp, response_code, response_content)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s)
                RETURNING id
                """,
                (userid, document, typedoc, json.dumps(payload), jobid, status, response_code, response_content)
            )
            request_id = cursor.fetchone()["id"]
        conn.commit()
        return request_id
    finally:
        conn.close()

# Function to save a response
def save_backgroundCheck_result(check_id: int, doc: str, hallazgos_altos:int, hallazgos_medios: int, hallazgos_bajos: int, response_payload: dict):
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            # Get the request_id from the requests table where jobid matches
            cursor.execute(
                """
                SELECT document, jobid  FROM backgroundcheck_requests WHERE id = %s
                """,
                (check_id,)
            )
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"No request found with checkid {check_id}")
            
            doc = result["document"]
            job_id = result["jobid"]

            # Insert the response into the responses table
            cursor.execute(
                """
                INSERT INTO backgroundcheck_results (checkid, document, jobid, hallazgos_altos, hallazgos_medios, hallazgos_bajos, response_payload, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (check_id, doc, job_id, hallazgos_altos, hallazgos_medios, hallazgos_bajos, json.dumps(response_payload))
            )
        conn.commit()
    finally:
        conn.close()

def get_user_credits(user_id: int) -> int:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT credits FROM backgroundcheck_user WHERE id = %s
                """,
                (user_id,)
            )
            result = cursor.fetchone()
            if result:
                return result["credits"]
            else:
                raise ValueError(f"No user found with id {user_id}")
    finally:
        conn.close()    

def update_user_credits(user_id: int, credits: int) -> bool:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE backgroundcheck_user SET credits = %s WHERE id = %s
                """,
                (credits, user_id)
            )
            if cursor.rowcount == 0:
                return False  # No rows were updated, user might not exist
        conn.commit()
        return True  # Successfully updated credits
    finally:
        conn.close()

def get_pending_checks(user_id: int) -> list:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM backgroundcheck_requests WHERE userid = %s AND status = 'procesando'
                """,
                (user_id,)
            )
            return cursor.fetchall()
    finally:
        conn.close()


def get_user_checks(user_id: int) -> list:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *, to_char(timestamp, 'YYYY-MM-DD HH24:MI:SS') as timestamp 
                FROM backgroundcheck_requests 
                WHERE userid = %s
                """,
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def update_check_status(check_id: int, status) -> bool:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE backgroundcheck_requests SET status = %s WHERE id = %s
                """,
                (status, check_id)
            )
            if cursor.rowcount == 0:
                return False  # No rows were updated, check might not exist
        conn.commit()
        return True  # Successfully updated check status
    finally:
        conn.close()

def get_user_processing_status(user_id: int) -> list:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FROM backgroundcheck_requests WHERE userid = %s AND status = 'procesando'
                """,
                (user_id,)
            )
            result = cursor.fetchone()
            return result["count"] > 0
    finally:
        conn.close()

def get_check(check_id: int) -> dict:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM backgroundcheck_requests WHERE id = %s
                """,
                (check_id,)
            )
            return cursor.fetchone()
    finally:
        conn.close()

def get_check_results(check_id: int) -> dict:
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM backgroundcheck_results WHERE checkid = %s
                """,
                (check_id,)
            )
            return cursor.fetchone()
    finally:
        conn.close()

def create_user(username, password= None):
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO backgroundcheck_user (username, password, credits) 
                VALUES (%s, %s, %s) RETURNING id
                """,
                (username, password, 0)
            )
            user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id
    finally:
        conn.close()

def get_user_id(username):
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM backgroundcheck_user WHERE username = %s
                """,
                (username,)
            )
            result = cursor.fetchone()
            if result:
                return result["id"]
            else:
                raise ValueError("Invalid email or password")
    finally:
        conn.close()    
        
if __name__ == '__main__': 
    print(get_user_id('test'))

