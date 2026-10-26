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
if __name__ == "__main__":
    # print("Bucket:", R2_BUCKET_NAME)
    # print("Endpoint:", R2_ENDPOINT)
    file_path = "test-photo.jpg"
    object_key = "test/test-photo.jpg"

    r2.upload_file(
        file_path,
        R2_BUCKET_NAME,
        object_key
    )
    # response = r2.list_objects_v2(
    #     Bucket=R2_BUCKET_NAME
    # )

    print("Photo uploaded successfully!")
    # print(response)
