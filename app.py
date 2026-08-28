from flask import Flask

from dotenv import load_dotenv
import os
import psycopg
from extensions import bcrypt,limiter

from routes.auth import auth_bp

load_dotenv()
app = Flask(__name__)
bcrypt.init_app(app)
limiter.init_app(app)

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