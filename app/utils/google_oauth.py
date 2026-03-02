"""Google OAuth utilities for authentication"""
from typing import Dict, Optional
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status

from app.core.config import settings


async def verify_google_token(token: str) -> Dict[str, str]:
    """
    Verify Google OAuth token and extract user information
    
    Args:
        token: Google ID token from frontend
        
    Returns:
        Dict with user info: {
            "google_id": str,
            "email": str,
            "full_name": str,
            "avatar_url": str
        }
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        # Verify the issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        # Extract user information
        return {
            "google_id": idinfo['sub'],
            "email": idinfo['email'],
            "full_name": idinfo.get('name', ''),
            "avatar_url": idinfo.get('picture', '')
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to verify Google token: {str(e)}"
        )
