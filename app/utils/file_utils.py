"""
File utility functions for secure file handling
"""
import uuid
from pathlib import Path
from typing import Tuple


def generate_secure_filename(original_filename: str) -> str:
    """
    Generate a secure filename with UUID to prevent duplicates and conflicts
    
    Format: {uuid}_{original_name}_sdmodels.{ext}
    Example: 550e8400-e29b-41d4-a716-446655440000_model_sdmodels.fbx
    
    Args:
        original_filename: Original filename from upload
        
    Returns:
        Secure filename with UUID prefix and sdmodels suffix
    """
    # Get file extension
    path = Path(original_filename)
    extension = path.suffix.lower()  # .fbx, .jpg, etc.
    name_without_ext = path.stem
    
    # Clean the filename (remove special characters, keep alphanumeric and basic chars)
    clean_name = "".join(c for c in name_without_ext if c.isalnum() or c in ('-', '_'))
    
    # Limit length to prevent issues
    if len(clean_name) > 50:
        clean_name = clean_name[:50]
    
    # Generate UUID
    file_uuid = str(uuid.uuid4())
    
    # Create secure filename
    secure_filename = f"{file_uuid}_{clean_name}_sdmodels{extension}"
    
    return secure_filename


def parse_secure_filename(secure_filename: str) -> Tuple[str, str, str]:
    """
    Parse a secure filename to extract UUID, original name, and extension
    
    Args:
        secure_filename: Filename in format {uuid}_{name}_sdmodels.{ext}
        
    Returns:
        Tuple of (uuid, original_name, extension)
    """
    path = Path(secure_filename)
    extension = path.suffix
    name_without_ext = path.stem
    
    # Split by underscore
    parts = name_without_ext.split('_')
    
    if len(parts) >= 3 and parts[-1] == 'sdmodels':
        file_uuid = parts[0]
        original_name = '_'.join(parts[1:-1])
        return file_uuid, original_name, extension
    
    # Fallback if format doesn't match
    return "", name_without_ext, extension


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase"""
    return Path(filename).suffix.lower()


def get_content_type(filename: str) -> str:
    """Get content type based on file extension"""
    ext = get_file_extension(filename)
    
    content_types = {
        # Images
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        
        # 3D Models
        '.fbx': 'application/octet-stream',
        '.glb': 'model/gltf-binary',
        '.gltf': 'model/gltf+json',
        '.obj': 'application/octet-stream',
        '.stl': 'application/octet-stream',
        '.3ds': 'application/octet-stream',
        '.dae': 'model/vnd.collada+xml',
        '.blend': 'application/octet-stream',
        
        # Documents
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
    }
    
    return content_types.get(ext, 'application/octet-stream')
