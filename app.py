from flask import Flask
from datetime import timedelta

from dotenv import load_dotenv
import os
import psycopg
from extensions import bcrypt,limiter,jwt

from routes.auth import auth_bp

load_dotenv()
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
# expiration of our tokens
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=10)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
bcrypt.init_app(app)
limiter.init_app(app)
jwt.init_app(app)


DATABASE_URL = os.getenv("DATABASE_URL")

app.register_blueprint(auth_bp, url_prefix = "/api/auth")

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