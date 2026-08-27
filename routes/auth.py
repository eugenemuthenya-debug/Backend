# This is our blueprint for any authentication related to our app.
# We will write them here and call them in our app.py
from datetime import datetime,timedelta,timezone
from flask import Blueprint,request,jsonify
import secrets
import traceback
from extensions import bcrypt
from database import get_db_connection
# import psycopg

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
                    verification_code
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
            email_verified_at
            FROM users
            WHERE email = %s
                """,
                (email,))
        user = cursor.fetchone()
        if not user :
            return jsonify({"error":"Invalid verification request."}),400

        user_id,email_verification_code_hash,email_verification_expires_at,email_verified_at = user
        if email_verified_at is not None:
            return jsonify({"message":"Email already verified."}),409
        if email_verification_code_hash is None or email_verification_expires_at is None:
            return jsonify({"error":"No active verification code exists."}),400
        if datetime.now(timezone.utc) > email_verification_expires_at:
            return jsonify({"error":"Verification code has expired."}),400

        # check verification code
        if not bcrypt.check_password_hash(
            email_verification_code_hash,
            verification_code
        ):
            return jsonify({"error":"Invalid verification code."})

        # if user passes all then we declare them verified 
        cursor.execute("""
            UPDATE users
            SET 
                email_verified_at = NOW(),
                email_verification_code_hash = NULL
                email_verification_expires_at = NULL
            WHERE user_id = %s
                """,(user_id,))
        conn.commit()

        return jsonify({"message":"Account created .Redirecting to log in.Please Wait."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}),500
    # finally:
    #     conn.close()



# -------------Resend verification code-----------------
@auth_bp.post("/resend-verification")
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
                email_verified_at
            FROM users
            WHERE email = %s
            """,(email,))

        user = cursor.fetchone()
        # if user doesn't exist
        if not user:
            return jsonify({"error":"Invalid request."}),400

        # return if the user does exist
        user_id ,email_verified_at = user

        # validate them
        if email_verified_at is not None:
            return jsonify({"error":"Email has already been verified."}),409

        return jsonify({"message":"Ready to get a new verification code."})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}),500
    # finally:
    #     conn.close()
       
 







    # return{"message":"signup endpoint working",
    #        "data":data}