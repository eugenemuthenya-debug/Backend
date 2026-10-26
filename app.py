from flask import Flask,jsonify
from datetime import timedelta

from dotenv import load_dotenv
from database import get_db_connection
import os
import psycopg
from extensions import bcrypt,limiter,jwt

# import of blueprints
from routes.photos import photos_bp
from routes.auth import auth_bp



load_dotenv()
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
# expiration of our tokens
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=10)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

# adding safe upload limits
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
# 1024*1024 = 1MiB so *10 = 10MB

bcrypt.init_app(app)
limiter.init_app(app)
jwt.init_app(app)

# this is for revoked tokens
# we create our block list callback
# _jwt_header -> this means the argument isn't being used at that specific point.
@jwt.token_in_blocklist_loader
def check_if_token_revoked(_jwt_header,jwt_payload):
    jti = jwt_payload["jti"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT 1 
            FROM revoked_tokens
            WHERE jti = %s
            """,(jti,))
    token = cursor.fetchone()

    cursor.close()
    conn.close()
    return token is not None
# if we find the jti in our database we return true = this token is revoked, reject it.

# this is for checking account status.
# tells flask-jwt to run a verification on the protected request
@jwt.token_verification_loader
def check_account_status(_jwt_header,jwt_payload):
    # we get our user_id from the entire jwt under sub
    user_id = jwt_payload["sub"]

    # our db connection
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT account_status
            FROM users
            WHERE user_id = %s
            """,(
                user_id,
            ))
    # if the user exists
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    # if user doesn't exist
    if not user :
        return False
    # if there is a user
    return user[0] == "ACTIVE"

# Custom response for failed events 
@jwt.token_verification_failed_loader
def token_verification_failed_callback(jwt_header,jwt_payload):
    user_id = jwt_payload.get("sub")

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
                    SELECT account_status
                    FROM users
                    WHERE user_id = %s
                    """,(user_id,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            return jsonify({"error":"This account is unavailable"}),403

        account_status = user[0]
        # this goes through every account status,stores them and compare them to the values we will define.
        messages = {
            "PENDING_VERIFICATION":
            "Please verify your email before using Church Media Hub.",

            "SUSPENDED":
            "Your account is temporarily suspended. Please contact your church administrator for assistance",

            "BANNED":
            "Your account has been disabled. Please contact your church administrator if you believe this is a mistake.",

            "DEACTIVATED":
            "Your account is deactivated. Please contact support for assistance."
        }

        # we use the custom messages depending on the account status
        message = messages.get(
            account_status,
            "Your account is not currently active.Please contact support for assistance."
        )
        return jsonify({"error":message}),403

    finally:
        if conn:
            conn.close()


DATABASE_URL = os.getenv("DATABASE_URL")

# --------------------------------------------------------
# photo blueprint
app.register_blueprint(photos_bp,url_prefix='/api/photos')

# authentication blueprint
app.register_blueprint(auth_bp, url_prefix = "/api/auth")
# --------------------------------------------------------
@app.get("/")
def Home():
    return{
        "message":"Church media hub api is running"
    }

@app.get("/test-db")
def test_db():

    try:
        with psycopg.connect(DATABASE_URL) as conn:

            with conn.cursor() as cursor:
                cursor.execute("SELECT NOW();")
                result = cursor.fetchone()

        return {
            "message": "Database connection successful!",
            "database_time": str(result[0])
        }

    except Exception as e:

        return {
            "message": "Database connection failed!",
            "error": str(e)
        }, 500

if __name__ == "__main__":
    app.run(debug=True)