import os
from dotenv import load_dotenv
from brevo import Brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)
from brevo.core.api_error import ApiError
# to show where python is = where python
# to show where brevo_python = pip show brevo_python

load_dotenv()

# This allows us to fetch and store our brevo api key 
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

#This was our old brevo config but had issues, due to brevo_python. ----------------------------------------------------------
#This creates our brevo connection 
# configuration = brevo_python.Configuration()
# This gives our configuration our api key 
# configuration.api_key["api-key"] = BREVO_API_KEY

# Creates the client that will communicate with brevo()
# api_client = brevo_python.ApiClient(configuration)

# Gives us part of the SDK specifically for transactional emails for codes
# transactional_api = brevo_python.TransactionalEmailsApi(api_client)
# ----------------------------------------------------------

client = Brevo(api_key=BREVO_API_KEY)
try :
    def send_verification_email(email, verification_code,username):
        response = client.transactional_emails.send_transac_email(
        subject="Verify your Church Media Hub account",
        html_content= f"""
        <html>
            <body>
                <h1>Hi {username}, </h1>
                <h2>Welcome to Church Media Hub!</h2>
                <p>We are glad to have you hear with us.To finish setting up your account, enter the verification code below :</p>
                <h1>{verification_code}</h1>
                <p>This code will expire in 10 minutes.</p>
                <p>If you did not create this account, you can safely ignore this email.
                </p>

                <p> The Church Media Hub Team</p>
            </body>
        </html>
        """,
        sender= SendTransacEmailRequestSender(
            name= " Eugene from Church Media Hub",
            email="churchmediahb@gmail.com"
        ),

        to=[SendTransacEmailRequestToItem(
            # email="eugenemuthenya@gmail.com"
            email=email
         )
        ]
    )
    
        return response
except ApiError as e:
    print(e.status_code)
    print(e.body)

if __name__ == "__main__":
    response = send_verification_email(
        "eugenemuthenya@gmail.com",
        "482913"
    )

    print("Email sent successfully!")
    print("Message ID:", response.message_id)




# print("Brevo API client initialized successfully!")
# print("Brevo API key loaded:", bool(BREVO_API_KEY))

