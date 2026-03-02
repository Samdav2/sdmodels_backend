"""
Storage Factory - Unified interface for different storage backends
"""
from typing import Optional, Protocol
from app.core.config import settings


class StorageBackend(Protocol):
    """Protocol defining the storage backend interface"""
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str = "models"
    ) -> Optional[str]:
        """Upload file and return URL"""
        ...
    
    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """Generate presigned/expiring URL"""
        ...
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete file"""
        ...


def get_storage() -> StorageBackend:
    """Get the configured storage backend"""
    backend = settings.STORAGE_BACKEND.lower()
    
    if backend == "azure":
        from app.utils.storage import AzureStorageWrapper
        return AzureStorageWrapper()
    elif backend == "opendrive":
        from app.utils.opendrive_storage import opendrive_storage
        return opendrive_storage
    else:
        # Default to S3
        from app.utils.storage import storage
        return storage


# Singleton instance
storage = get_storage()
