# This is our reusable client that will communicate with cloudflare R2.
import os
import boto3
from dotenv import load_dotenv

load_dotenv()
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")

r2 = boto3.client(
    "s3",
    endpoint_url = R2_ENDPOINT,
    aws_access_key_id = R2_ACCESS_KEY_ID,
    aws_secret_access_key = R2_SECRET_ACCESS_KEY,
    region_name = "auto"
)
# We run this code to test that python can import our new module and create the R2 client

# python -c "from r2_storage import r2, R2_BUCKET_NAME; print('R2 client created:', r2 is not None); print('Bucket configured:', bool(R2_BUCKET_NAME))"

# We test if our credentials can communicate with CloudflareR2:
# python -c "from r2_storage import r2, R2_BUCKET_NAME; response = r2.list_objects_v2(Bucket=R2_BUCKET_NAME, MaxKeys=1); print('R2 connection successful'); print('HTTP status:', response['ResponseMetadata']['HTTPStatusCode'])"
