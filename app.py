from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)

@app.get("/")
def Home():
    return{
        "message":"Church media hub api is running"
    }
if __name__ == "__main__":
    app.run(debug=True)