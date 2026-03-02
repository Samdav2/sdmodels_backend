import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from typing import Optional, BinaryIO

from app.core.config import settings


class S3Storage:
    """S3/CloudFlare R2 storage handler"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str = "models"
    ) -> Optional[str]:
        """Upload file to S3"""
        try:
            key = f"{folder}/{datetime.utcnow().strftime('%Y/%m/%d')}/{file_name}"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            
            # Return CDN URL
            return f"{settings.CDN_URL}/{key}"
        except ClientError as e:
            print(f"Failed to upload file: {e}")
            return None
    
    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """Generate presigned URL for file download"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Failed to generate presigned URL: {e}")
            return None
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return True
        except ClientError as e:
            print(f"Failed to delete file: {e}")
            return False


class AzureStorageWrapper:
    """Azure Blob Storage wrapper for unified interface"""
    
    def __init__(self):
        from app.utils.azure_storage import get_azure_storage
        self.azure = get_azure_storage()
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str = "models"
    ) -> Optional[str]:
        """Upload file to Azure Blob Storage"""
        try:
            from io import BytesIO
            blob_name = f"{folder}/{datetime.utcnow().strftime('%Y/%m/%d')}/{file_name}"
            file_data = BytesIO(file_content)
            return self.azure.upload_file(file_data, blob_name, content_type)
        except Exception as e:
            print(f"Failed to upload file to Azure: {e}")
            return None
    
    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """Generate SAS URL for Azure blob"""
        try:
            return self.azure.generate_sas_url(file_key, expiration)
        except Exception as e:
            print(f"Failed to generate SAS URL: {e}")
            return None
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete file from Azure Blob Storage"""
        try:
            return self.azure.delete_file(file_key)
        except Exception as e:
            print(f"Failed to delete file from Azure: {e}")
            return False


class OpenDriveStorageWrapper:
    """OpenDrive storage wrapper for unified interface"""
    
    def __init__(self):
        from app.utils.opendrive_storage import get_opendrive_storage
        self.opendrive = get_opendrive_storage()
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str = "models"
    ) -> Optional[str]:
        """Upload file to OpenDrive"""
        try:
            from io import BytesIO
            file_data = BytesIO(file_content)
            file_data.name = file_name
            return self.opendrive.upload_file(file_data, folder)
        except Exception as e:
            print(f"Failed to upload file to OpenDrive: {e}")
            return None
    
    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """Get public URL from OpenDrive"""
        try:
            return self.opendrive.get_file_url(file_key)
        except Exception as e:
            print(f"Failed to get OpenDrive URL: {e}")
            return None
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete file from OpenDrive"""
        try:
            return self.opendrive.delete_file(file_key)
        except Exception as e:
            print(f"Failed to delete file from OpenDrive: {e}")
            return False


def get_storage():
    """Get storage instance based on configuration"""
    backend = settings.STORAGE_BACKEND.lower()
    
    if backend == "azure":
        return AzureStorageWrapper()
    elif backend == "opendrive":
        return OpenDriveStorageWrapper()
    else:  # default to s3
        return S3Storage()


# Singleton instance
storage = get_storage()

