"""
OpenDrive Storage Integration
Based on OpenDrive REST API v1.1.7
"""
import httpx
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from app.core.config import settings


class OpenDriveStorage:
    """OpenDrive cloud storage handler"""
    
    BASE_URL = "https://dev.opendrive.com/api/v1"
    
    def __init__(self):
        self.username = settings.OPENDRIVE_USERNAME
        self.password = settings.OPENDRIVE_PASSWORD
        self.partner_id = settings.OPENDRIVE_PARTNER_ID or "OpenDrive"
        self.session_id: Optional[str] = None
        self.folder_ids: Dict[str, str] = {}  # Cache folder IDs
    
    async def _ensure_session(self) -> str:
        """Ensure we have a valid session, create if needed"""
        if self.session_id:
            # Check if session is still valid with timeout
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/session/exists.json",
                        json={"session_id": self.session_id}
                    )
                    if response.status_code == 200:
                        return self.session_id
            except (httpx.TimeoutException, httpx.ConnectError):
                # Session check failed, will create new session
                pass
        
        # Create new session
        return await self._login()
    
    async def _login(self) -> str:
        """Create a login session with retry logic"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/session/login.json",
                        json={
                            "username": self.username,
                            "passwd": self.password,
                            "partner_id": self.partner_id
                        }
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"OpenDrive login failed: {response.text}")
                    
                    data = response.json()
                    self.session_id = data["SessionID"]
                    return self.session_id
                    
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    print(f"Connection timeout (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise Exception(f"Failed to connect to OpenDrive after {max_retries} attempts: {str(e)}")
            except Exception as e:
                raise Exception(f"OpenDrive login error: {str(e)}")
    
    async def _get_or_create_folder(self, folder_name: str, parent_id: str = "0") -> str:
        """Get or create a folder, return folder ID"""
        # Check cache
        cache_key = f"{parent_id}:{folder_name}"
        if cache_key in self.folder_ids:
            return self.folder_ids[cache_key]
        
        session_id = await self._ensure_session()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # List folders to check if it exists
            response = await client.get(
                f"{self.BASE_URL}/folder/list.json/{session_id}/{parent_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                folders = data.get("Folders", [])
                for folder in folders:
                    if folder["Name"] == folder_name:
                        folder_id = folder["FolderID"]
                        self.folder_ids[cache_key] = folder_id
                        return folder_id
            
            # Create folder if it doesn't exist - PUBLIC for file sharing
            response = await client.post(
                f"{self.BASE_URL}/folder.json",
                json={
                    "session_id": session_id,
                    "folder_name": folder_name,
                    "folder_sub_parent": parent_id,
                    "folder_is_public": 1,  # Public folder
                    "folder_public_upl": 0,  # No public upload
                    "folder_public_display": 1,  # Public display
                    "folder_public_dnl": 1  # Public download
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to create folder: {response.text}")
            
            data = response.json()
            folder_id = data["FolderID"]
            self.folder_ids[cache_key] = folder_id
            return folder_id
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str = "models"
    ) -> Optional[str]:
        """
        Upload file to OpenDrive
        Returns the file's download link
        """
        try:
            session_id = await self._ensure_session()
            
            # Get or create folder structure
            # Create year/month/day structure
            now = datetime.utcnow()
            year_folder = await self._get_or_create_folder(str(now.year))
            month_folder = await self._get_or_create_folder(
                f"{now.month:02d}", 
                year_folder
            )
            day_folder = await self._get_or_create_folder(
                f"{now.day:02d}", 
                month_folder
            )
            type_folder = await self._get_or_create_folder(folder, day_folder)
            
            # Calculate file hash
            file_hash = hashlib.md5(file_content).hexdigest()
            file_size = len(file_content)
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Step 1: Create file
                create_response = await client.post(
                    f"{self.BASE_URL}/upload/create_file.json",
                    json={
                        "session_id": session_id,
                        "folder_id": type_folder,
                        "file_name": file_name,
                        "file_size": file_size,
                        "file_hash": file_hash,
                        "open_if_exists": 1
                    }
                )
                
                if create_response.status_code != 200:
                    raise Exception(f"Failed to create file: {create_response.text}")
                
                file_data = create_response.json()
                file_id = file_data["FileId"]
                
                # Check if file already exists (RequireHashOnly)
                if file_data.get("RequireHashOnly") == 1:
                    print(f"File already exists (deduplication), FileID: {file_id}")
                    print(f"Getting public streaming link for existing file...")
                    # File already exists, just close upload
                    close_response = await client.post(
                        f"{self.BASE_URL}/upload/close_file_upload.json",
                        json={
                            "session_id": session_id,
                            "file_id": file_id,
                            "file_size": file_size,
                            "file_hash": file_hash
                        }
                    )
                    
                    if close_response.status_code == 200:
                        # ALWAYS get public streaming link for existing file
                        public_link = await self._get_public_link(file_id)
                        if public_link:
                            print(f"✓ Got public streaming link for deduplicated file: {public_link[:60]}...")
                            return public_link
                        else:
                            print(f"❌ ERROR: Could not get public link for existing file!")
                            print(f"   This should not happen. Falling back to DownloadLink.")
                            close_data = close_response.json()
                            fallback_link = close_data.get("DownloadLink")
                            print(f"   Fallback link: {fallback_link}")
                            return fallback_link
                    else:
                        print(f"❌ ERROR: Failed to close deduplicated file upload: {close_response.text}")
                        return None
                
                # Step 2: Open file upload
                open_response = await client.post(
                    f"{self.BASE_URL}/upload/open_file_upload.json",
                    json={
                        "session_id": session_id,
                        "file_id": file_id,
                        "file_size": file_size,
                        "file_hash": file_hash
                    }
                )
                
                if open_response.status_code != 200:
                    raise Exception(f"Failed to open file upload: {open_response.text}")
                
                open_data = open_response.json()
                temp_location = open_data.get("TempLocation", "")
                
                # Step 3: Upload file chunks (using version 2 for better stability)
                chunk_size = 1024 * 1024  # 1MB chunks
                offset = 0
                
                while offset < file_size:
                    chunk = file_content[offset:offset + chunk_size]
                    
                    # Prepare multipart form data
                    files = {"file_data": ("chunk", chunk, "application/octet-stream")}
                    
                    chunk_response = await client.post(
                        f"{self.BASE_URL}/upload/upload_file_chunk2.json/{session_id}/{file_id}",
                        params={
                            "temp_location": temp_location,
                            "chunk_offset": offset,
                            "chunk_size": len(chunk)
                        },
                        files=files
                    )
                    
                    if chunk_response.status_code != 200:
                        raise Exception(f"Failed to upload chunk: {chunk_response.text}")
                    
                    offset += len(chunk)
                
                # Step 4: Close file upload
                close_response = await client.post(
                    f"{self.BASE_URL}/upload/close_file_upload.json",
                    json={
                        "session_id": session_id,
                        "file_id": file_id,
                        "file_size": file_size,
                        "temp_location": temp_location,
                        "file_hash": file_hash
                    }
                )
                
                if close_response.status_code != 200:
                    raise Exception(f"Failed to close file upload: {close_response.text}")
                
                close_data = close_response.json()
                
                # Step 5: Get public download link (REQUIRED for public access)
                public_link = await self._get_public_link(file_id)
                if public_link:
                    print(f"✓ Got public streaming link")
                    return public_link
                else:
                    print(f"⚠️  Warning: Could not get public streaming link, using fallback")
                    # Fallback to regular download link (may not be publicly accessible)
                    fallback_link = close_data.get("DownloadLink")
                    print(f"   Fallback link: {fallback_link}")
                    return fallback_link
        
        except Exception as e:
            print(f"Failed to upload file to OpenDrive: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _get_public_link(self, file_id: str, retry_count: int = 3) -> Optional[str]:
        """Get public download link for a file with retry logic"""
        for attempt in range(retry_count):
            try:
                session_id = await self._ensure_session()
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # First, make file public
                    if attempt == 0:
                        print(f"Setting file {file_id} to public...")
                    access_response = await client.post(
                        f"{self.BASE_URL}/file/access.json",
                        json={
                            "session_id": session_id,
                            "file_id": file_id,
                            "file_ispublic": "1"  # Make public (note: string "1", not int)
                        }
                    )
                    
                    if access_response.status_code != 200:
                        if attempt == 0:
                            print(f"⚠️  Could not set file access: {access_response.text}")
                    else:
                        if attempt == 0:
                            print(f"✓ File set to public")
                    
                    # Small delay to let OpenDrive process the access change
                    if attempt > 0:
                        await asyncio.sleep(1)
                    
                    # Get file info to extract streaming links
                    if attempt == 0:
                        print(f"Getting file info for {file_id}...")
                    info_response = await client.get(
                        f"{self.BASE_URL}/file/info.json/{file_id}",
                        params={"session_id": session_id}
                    )
                    
                    if info_response.status_code == 200:
                        file_info = info_response.json()
                        if attempt == 0:
                            print(f"✓ Got file info")
                        
                        # Prefer TempStreamingLink for direct API access
                        temp_stream = file_info.get("TempStreamingLink")
                        if temp_stream:
                            print(f"✓ Found TempStreamingLink: {temp_stream[:60]}...")
                            return temp_stream
                        
                        # Try StreamingLink
                        stream_link = file_info.get("StreamingLink")
                        if stream_link:
                            print(f"✓ Found StreamingLink: {stream_link[:60]}...")
                            return stream_link
                        
                        # If no streaming links found and we have retries left, try again
                        if attempt < retry_count - 1:
                            print(f"⚠️  No streaming links found, retrying (attempt {attempt + 1}/{retry_count})...")
                            continue
                        
                        # Fallback to DownloadLink
                        download_link = file_info.get("DownloadLink")
                        if download_link:
                            print(f"⚠️  Only DownloadLink available: {download_link[:60]}...")
                            return download_link
                        
                        print(f"❌ No links found in file info")
                    else:
                        print(f"❌ Failed to get file info: {info_response.status_code} - {info_response.text}")
                        if attempt < retry_count - 1:
                            print(f"   Retrying (attempt {attempt + 1}/{retry_count})...")
                            continue
                    
                    return None
                    
            except Exception as e:
                print(f"❌ Failed to get public link (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(1)
                    continue
                import traceback
                traceback.print_exc()
                return None
        
        return None
    
    async def generate_presigned_url(
        self,
        file_id: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate expiring link for file download
        expiration: seconds until link expires
        """
        try:
            session_id = await self._ensure_session()
            
            # Calculate expiration date
            from datetime import datetime, timedelta
            expire_date = datetime.utcnow() + timedelta(seconds=expiration)
            expire_str = expire_date.strftime("%Y-%m-%d")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/file/expiringlink.json/{session_id}/{expire_str}/0/{file_id}/1"
                )
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                return data.get("DownloadLink")
        
        except Exception as e:
            print(f"Failed to generate presigned URL: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from OpenDrive (move to trash first, then delete)"""
        try:
            session_id = await self._ensure_session()
            
            async with httpx.AsyncClient() as client:
                # First, move to trash
                trash_response = await client.post(
                    f"{self.BASE_URL}/file/trash.json",
                    json={
                        "session_id": session_id,
                        "file_id": file_id
                    }
                )
                
                if trash_response.status_code != 200:
                    return False
                
                # Then permanently delete
                delete_response = await client.delete(
                    f"{self.BASE_URL}/file.json/{session_id}/{file_id}"
                )
                
                return delete_response.status_code == 200
        
        except Exception as e:
            print(f"Failed to delete file: {e}")
            return False
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information"""
        try:
            session_id = await self._ensure_session()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/file/info.json/{file_id}",
                    params={"session_id": session_id}
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
        
        except Exception as e:
            print(f"Failed to get file info: {e}")
            return None
    
    async def logout(self):
        """Logout and cleanup session"""
        if self.session_id:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.BASE_URL}/session/logout.json",
                        json={"session_id": self.session_id}
                    )
            except:
                pass
            finally:
                self.session_id = None


# Singleton instance
opendrive_storage = OpenDriveStorage()
