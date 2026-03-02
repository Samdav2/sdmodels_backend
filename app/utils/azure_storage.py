"""
Azure Blob Storage integration for file uploads
"""
import os
import mimetypes
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.core.exceptions import AzureError

from app.core.config import settings


class AzureStorage:
    """Azure Blob Storage handler"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client"""
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.account_name = settings.AZURE_STORAGE_ACCOUNT_NAME
        self.account_key = settings.AZURE_STORAGE_ACCOUNT_KEY
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        
        # Initialize blob service client
        if self.connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        elif self.account_name and self.account_key:
            account_url = f"https://{self.account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=self.account_key
            )
        else:
            raise ValueError(
                "Azure Storage credentials not configured. "
                "Provide either AZURE_STORAGE_CONNECTION_STRING or "
                "AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY"
            )
        
        # Get or create container
        self.container_client = self.blob_service_client.get_container_client(
            self.container_name
        )
        
        # Create container if it doesn't exist
        try:
            if not self.container_client.exists():
                self.container_client.create_container(public_access='blob')
                print(f"✅ Created Azure container: {self.container_name}")
        except AzureError as e:
            print(f"⚠️  Azure container check/create failed: {e}")
    
    def upload_file(
        self,
        file_data: BinaryIO,
        blob_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload file to Azure Blob Storage
        
        Args:
            file_data: File binary data
            blob_name: Name/path for the blob (e.g., "models/uuid/file.fbx")
            content_type: MIME type of the file
            metadata: Optional metadata dictionary
            
        Returns:
            Public URL of the uploaded blob
        """
        try:
            # Auto-detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(blob_name)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Upload blob with content settings
            from azure.storage.blob import ContentSettings
            
            content_settings = ContentSettings(content_type=content_type)
            
            blob_client.upload_blob(
                file_data,
                overwrite=True,
                content_settings=content_settings,
                metadata=metadata or {}
            )
            
            # Return public URL
            return blob_client.url
            
        except AzureError as e:
            raise Exception(f"Azure upload failed: {str(e)}")
    
    def upload_file_from_path(
        self,
        file_path: str,
        blob_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload file from local path to Azure Blob Storage
        
        Args:
            file_path: Local file path
            blob_name: Name/path for the blob
            content_type: MIME type of the file
            metadata: Optional metadata dictionary
            
        Returns:
            Public URL of the uploaded blob
        """
        with open(file_path, 'rb') as file_data:
            return self.upload_file(file_data, blob_name, content_type, metadata)
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete file from Azure Blob Storage
        
        Args:
            blob_name: Name/path of the blob to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except AzureError as e:
            print(f"⚠️  Azure delete failed: {e}")
            return False
    
    def get_file_url(self, blob_name: str, expires_in: int = 3600) -> str:
        """
        Get public URL for a blob
        
        Args:
            blob_name: Name/path of the blob
            expires_in: Expiration time in seconds (for SAS token)
            
        Returns:
            Public URL or SAS URL if container is private
        """
        blob_client = self.container_client.get_blob_client(blob_name)
        
        # If container is public, return direct URL
        if self.is_public_container():
            return blob_client.url
        
        # Otherwise, generate SAS token for private access
        return self.generate_sas_url(blob_name, expires_in)
    
    def generate_sas_url(self, blob_name: str, expires_in: int = 3600) -> str:
        """
        Generate SAS (Shared Access Signature) URL for private blob access
        
        Args:
            blob_name: Name/path of the blob
            expires_in: Expiration time in seconds
            
        Returns:
            SAS URL with temporary access
        """
        try:
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in)
            )
            
            # Construct SAS URL
            blob_client = self.container_client.get_blob_client(blob_name)
            return f"{blob_client.url}?{sas_token}"
            
        except AzureError as e:
            raise Exception(f"Failed to generate SAS URL: {str(e)}")
    
    def is_public_container(self) -> bool:
        """Check if container has public access"""
        try:
            properties = self.container_client.get_container_properties()
            return properties.get('public_access') is not None
        except AzureError:
            return False
    
    def file_exists(self, blob_name: str) -> bool:
        """
        Check if file exists in Azure Blob Storage
        
        Args:
            blob_name: Name/path of the blob
            
        Returns:
            True if file exists
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            return blob_client.exists()
        except AzureError:
            return False
    
    def get_file_size(self, blob_name: str) -> Optional[int]:
        """
        Get file size in bytes
        
        Args:
            blob_name: Name/path of the blob
            
        Returns:
            File size in bytes or None if not found
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            properties = blob_client.get_blob_properties()
            return properties.size
        except AzureError:
            return None
    
    def list_blobs(self, prefix: Optional[str] = None, limit: int = 100):
        """
        List blobs in container
        
        Args:
            prefix: Filter blobs by prefix (folder path)
            limit: Maximum number of blobs to return
            
        Returns:
            List of blob names
        """
        try:
            blobs = self.container_client.list_blobs(
                name_starts_with=prefix,
                results_per_page=limit
            )
            return [blob.name for blob in blobs]
        except AzureError as e:
            print(f"⚠️  Failed to list blobs: {e}")
            return []
    
    def copy_blob(self, source_blob: str, dest_blob: str) -> bool:
        """
        Copy blob within the same container
        
        Args:
            source_blob: Source blob name
            dest_blob: Destination blob name
            
        Returns:
            True if copied successfully
        """
        try:
            source_client = self.container_client.get_blob_client(source_blob)
            dest_client = self.container_client.get_blob_client(dest_blob)
            
            # Start copy operation
            dest_client.start_copy_from_url(source_client.url)
            return True
        except AzureError as e:
            print(f"⚠️  Failed to copy blob: {e}")
            return False


# Global instance
azure_storage = None

def get_azure_storage() -> AzureStorage:
    """Get or create Azure Storage instance"""
    global azure_storage
    if azure_storage is None:
        azure_storage = AzureStorage()
    return azure_storage
