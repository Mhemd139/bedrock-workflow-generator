import boto3
import base64
from typing import Optional
from botocore.exceptions import ClientError


class S3Client:
    def __init__(self, bucket_name: str = "bedrock-workflow-screenshots", region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.region = region
        self.client = boto3.client("s3", region_name=region)
    
    def upload_screenshot(self, image_bytes: bytes, key: str) -> str:
        """Upload screenshot to S3, return the S3 key"""
        
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=image_bytes,
            ContentType="image/png"
        )
        
        return key
    
    def upload_screenshot_base64(self, image_base64: str, key: str) -> str:
        """Upload base64 encoded screenshot to S3"""
        
        image_bytes = base64.b64decode(image_base64)
        return self.upload_screenshot(image_bytes, key)
    
    def download_screenshot(self, key: str) -> bytes:
        """Download screenshot from S3"""
        
        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=key
        )
        
        return response["Body"].read()
    
    def download_screenshot_base64(self, key: str) -> str:
        """Download screenshot and return as base64"""
        
        image_bytes = self.download_screenshot(key)
        return base64.b64encode(image_bytes).decode("utf-8")
    
    def delete_screenshot(self, key: str) -> bool:
        """Delete screenshot from S3"""
        
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError:
            return False
    
    def list_screenshots(self, prefix: str = "") -> list[str]:
        """List all screenshots in bucket with optional prefix"""
        
        response = self.client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix
        )
        
        if "Contents" not in response:
            return []
        
        return [obj["Key"] for obj in response["Contents"]]
    
    def test_connection(self) -> bool:
        """Test S3 bucket access"""
        
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            print(f"S3 connection failed: {e}")
            return False