# This is our blueprint for any authentication related to our app.
# We will write them here and call them in our app.py
from datetime import datetime,timedelta,timezone
from flask import Blueprint,request,jsonify
import secrets
import traceback
from extensions import bcrypt,limiter
from database import get_db_connection
# import psycopg
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt

)

from services.email_service import send_verification_email
# we are creating a blueprint instead of an another app
# blueprint-a collection of routes that will eventually be attached to the flask application.
auth_bp = Blueprint("auth", __name__)
# Blueprint-it is flask's blueprint class,creating a blueprint obj
# auth-name of blueprint(our blueprint that we are creating is called a blueprint)

# @auth_bp.get("/test")
# def auth_test():
#     return{
#         "message":"Authentication routes are working"
#     }

# Sign up route
@auth_bp.post("/signup")
def signup():
    data = request.get_json()
    # prevent empty request
    if not data :
        return jsonify({"error":"Request body is required"}),400
    

    # our data
    username = data.get("username").strip()
    email = data.get("email").strip()
    password = data.get("password")
    phone_number = data.get("phone_number")


# ------------------- Validation -------------------------
    # check required fields
    if not username or not email or not password:
        return{"error":"Username,email and password are required"},400

    if len(username) < 3 :
        return{"error":"Username must be at least 3 characters long."},400
    if len(password) < 8 :
        return{"error":"Password must be at least 8 characters long."},400
    if "@" not in email :
        return{"error":"Invalid email address."},400
# ----------------------------------------------------------
# end of validation


# --------Check existing email,username-------------------
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
                    SELECT user_id
                    FROM users
                    WHERE username = %s 
                        """,
                        (username,)
                        )
        existing_username = cursor.fetchone()
        if existing_username:
                cursor.close()
                conn.close()
                return jsonify({"error":"Username already exists."}),409
        
            #Checks if email already exists 
        cursor.execute("""
                    SELECT user_id
                    FROM users
                    WHERE email = %s
                            """,
            (email,)
            )
        existing_email = cursor.fetchone()
        
        if existing_email :
                cursor.close()
                conn.close()
                return{"error":"Email already registered"},409
# --------------------------------------------------------


#------------ Password hashing----------------------------
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")


#--------------------generate verification code-----------
        # secrets.randbelow->generates a random code between (0-1000000)
        # :06d->makes sure the code generated will always be 6 digits
        verification_code = f"{secrets.randbelow(1000000):06d}"
        # we hash it
        email_verification_code_hash = bcrypt.generate_password_hash(verification_code).decode("utf-8")
        # we set the expiry date and time
        email_verification_expires_at = (
             datetime.now(timezone.utc) + timedelta(minutes=10)
             )

    
    #-------------- insert our data to our database-------
        cursor.execute("""
                    INSERT INTO users(
                    username,
                    email,
                    password_hash,
                    phone_number,
                    email_verification_code_hash,
                    email_verification_expires_at
                    )
                    VALUES(
                    %s,%s,%s,%s,%s,%s)
                    RETURNING user_id
                            """,
                            (username,
                             email,
                             password_hash,
                             phone_number,
                             email_verification_code_hash,
                             email_verification_expires_at)
                            )
        user_id = cursor.fetchone()[0]
        conn.commit()

# -----------------Send verification email----------------
# We create the account first then send the verification code to the users email.
        try:
            send_verification_email(
                    email,
                    verification_code,
                    username
               )
            return jsonify({"message":"Verification code sent to your email.",
                                    "email":email}),201
            
        except Exception as e:
         traceback.print_exc()
         print({"error":str(e)}),500
         return({"error":"Account created but verification email could not be sent."}),500
        
       
    except Exception as  e :
        traceback.print_exc()
        return jsonify({"error":str(e)}),500
        # return jsonify({"error":"Something went wrong.PLease try again."}),500


# --------------Verify - email----------------------------
@auth_bp.post("/verify-email")
@limiter.limit("5 per minute")
def verify_email():
    data = request.get_json()

# input fields we require
    email = data.get("email")
    verification_code = data.get("verification_code")

    # check empty fields
    if not email or not verification_code:
        return jsonify({"error":"Email and verification code required."}),400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
            user_id,
            email_verification_code_hash,
            email_verification_expires_at,
            email_verified_at,
            email_verification_attempts,
            email_verification_last_attempt_at
            FROM users
            WHERE email = %s
                """,
                (email,))
        user = cursor.fetchone()
        if not user :
            return jsonify({"error":"Invalid verification request."}),400

        (user_id,
         email_verification_code_hash,email_verification_expires_at,
         email_verified_at,
         email_verification_attempts,
         email_verification_last_attempt_at
         ) = user

        

        if email_verified_at is not None:
            return jsonify({"message":"Email already verified."}),409
        if email_verification_code_hash is None or email_verification_expires_at is None:
            return jsonify({"error":"No active verification code exists."}),400
        if datetime.now(timezone.utc) > email_verification_expires_at:
            return jsonify({"error":"Verification code has expired."}),400

        # our cooldown for how may attempts the user can make .
        attempt_time = datetime.now(timezone.utc)
        if email_verification_last_attempt_at is not None:
            time_since_last_attempt = (
                attempt_time - email_verification_last_attempt_at)
            if time_since_last_attempt.total_seconds() < 5:
                return jsonify({"error":"Please wait a few seconds before trying again."}),429

       
        # check verification code
        if not bcrypt.check_password_hash(
            email_verification_code_hash,
            verification_code
        ):
             #attempt record
            new_attempt_count = email_verification_attempts + 1

            # whe  max is reached, we set the max attempt, clear everything and ask for a new code.
            if new_attempt_count >= 5:
                cursor.execute("""
                    UPDATE users
                    SET
                      email_verification_attempts = %s,
                      email_verification_last_attempt_at = %s,
                      email_verification_code_hash = NULL,
                      email_verification_expires_at = NULL
                    WHERE user_id = %s
                """,(
                    new_attempt_count,
                    attempt_time,
                    user_id
                ))
                conn.commit()
                return jsonify({"error":"Too many incorrect verification attempts. Please request a new verification code."}),429

            # Fewer attempts than 5
            cursor.execute("""
                UPDATE users
                SET 
                  email_verification_attempts = %s,
                  email_verification_last_attempt_at = %s
                WHERE user_id = %s
                """,(
                    new_attempt_count,
                    attempt_time,
                    user_id
                ))
            conn.commit()
            return jsonify({"error":"Invalid verification code."}),400

        # if user passes all then we declare them verified 
        cursor.execute("""
            UPDATE users
            SET 
                email_verified = TRUE,
                email_verified_at = NOW(),
                email_verification_code_hash = NULL,
                email_verification_expires_at = NULL,
                email_verification_attempts = 0,
                email_verification_last_attempt_at = NULL
            WHERE user_id = %s
                """,(
                    user_id,))
        conn.commit()

        return jsonify({"message":"Account created .Redirecting to log in.Please Wait."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}),500
    # finally:
    #     conn.close()



# -------------Resend verification code-----------------
@auth_bp.post("/resend-verification")
@limiter.limit("1 per minute")
def resend_verification():
    data = request.get_json()

    # we only need the correct email to resend the verification code email.
    email = data.get("email")

    # check for empty fields
    if not email:
        return jsonify({"error":"Email is required"}),400

    # find the user in our database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                user_id,
                username,
                email_verified_at
            FROM users
            WHERE email = %s
            """,(email,))

        user = cursor.fetchone()
        # if user doesn't exist
        if not user:
            return jsonify({"error":"Invalid request."}),400

        # return if the user does exist
        user_id , username ,email_verified_at  = user

        # validate them
        if email_verified_at is not None:
            return jsonify({"error":"Email has already been verified."}),409

        # create another verification code
        verification_code = f"{secrets.randbelow(1000000):06d}"

        # hash the new code
        email_verification_code_hash = bcrypt.generate_password_hash(verification_code).decode("utf-8")

        # code expiration
        email_verification_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10))

        # update the users tables
        cursor.execute("""
            UPDATE users
            SET 
             email_verification_code_hash = %s,
             email_verification_expires_at = %s,
             email_verification_attempts = 0
            WHERE user_id = %s
            """,(
             email_verification_code_hash,
             email_verification_expires_at,
             user_id
             ))
        conn.commit()

        # resend the actual code
        try:
            send_verification_email(
                email,
                verification_code,
                username
            )
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error":str(e)}),500


        return jsonify({"message":"Verification code has been sent."})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}),500
    finally:
        conn.close()

# ------------------Log in--------------------------------
@auth_bp.post("/log-in")
@limiter.limit("5 per minute")
def log_in():

    # we accept data
    data = request.get_json()

    # prevent empty request
    if not data :
        return jsonify({"error":"Request body is required"}),400

    # the data we need
    email = data.get("email")
    password = data.get("password")

    # check for empty fields
    if not email or not password:
        return jsonify({"error":"All fields are required."}),400

    try:
        # this creates our db connection
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
             user_id,
             username,
             password_hash,
             email,
             email_verified
            FROM users
            WHERE email = %s
            """,(email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error":"Invalid credentials..."}),401

        # this brings the user as a list which we access via indexes.Not optimal

        # so we unpack it
        (user_id,
         username,
         password_hash,
         email,
         email_verified
         ) = user
        # return ({"our user":user})

        # check if user actually exists
        if not bcrypt.check_password_hash(password_hash,password) :
            return jsonify({"error":"Invalid credentials.."}),401

        # check if they are verified or not
        if not email_verified:
            return jsonify({"error":"Please verify your email before logging in."}),403

        # access_token creation
        # user_id is a UUID and converting it into a string make sit easy to bake our access token.
        access_token = create_access_token(identity=str(user_id))
        refresh_token = create_refresh_token(identity=str(user_id))
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}),500
    
    return jsonify({"message":"Test 3 complete & Login successfully.",
                    "access_token":access_token,
                    "refresh_token":refresh_token}),200

@auth_bp.get("/test-protected")
@jwt_required(refresh=False)
def test_protected():
    user_id = get_jwt_identity()

    return jsonify({"message":"You are authenticated",
                    "user_id":user_id}),200

# refresh endpoint
@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()

    new_access_token = create_access_token(identity= user_id)

    return jsonify({"access_token":new_access_token}),200


# Log out endpoint
# WE store the refresh token in the database so we only need refresh tokens
@auth_bp.post("/log-out")
@jwt_required(refresh= True)
def log_out():
    jwt_payload = get_jwt()
    # this gets us the payload from our current jwt

    jti = jwt_payload["jti"]
    # in the payload we have the jti(which we will store in our database) which we get it and store in our variable
    token_type = jwt_payload["type"]
    user_id = get_jwt_identity()
    expires_at = datetime.fromtimestamp(
        jwt_payload["exp"],
        tz= timezone.utc
    )

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
                INSERT INTO revoked_tokens(
                jti,
                token_type,
                user_id,
                expires_at
                )
                VALUES (%s,%s,%s,%s)
                """,(
                    jti,
                    token_type,
                    user_id,
                    expires_at
                ))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message":"Logout successful"}),200
    except Exception as e:
        traceback.print_exc()

        if conn:
            conn.rollback()
            conn.close()
            return jsonify({"error":"AN error occurred during log out"}),500


       

    # return{"message":"signup endpoint working",
    #        "data":data}