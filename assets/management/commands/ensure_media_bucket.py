import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates the S3 bucket for uploaded files if it doesn't exist yet (for local development)"

    def handle(self, *args, **kwargs):
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        if not bucket:
            self.stdout.write("No S3 bucket configured, uploads use local disk")
            return
        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError:
            client.create_bucket(Bucket=bucket)
            self.stdout.write(f"Created bucket {bucket}")
        else:
            self.stdout.write(f"Bucket {bucket} already exists")
