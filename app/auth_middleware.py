# app/auth_middleware.py
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional
from app.auth_helper import verify_token
from data.db.database import SessionLocal
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
class ConfigurableHTTPBearer(HTTPBearer):
    def __init__(self):
        super().__init__(auto_error=False)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        # Always attempt to get credentials, but don't raise an error if they're missing
        credentials = await super().__call__(request)
        if credentials is not None:
            # Remove curly brackets from the token if present
            token = credentials.credentials
            token = token.replace('{', '').replace('}', '')
            return HTTPAuthorizationCredentials(scheme=credentials.scheme, credentials=token)
        return credentials

class AuthMiddleware:
    def __init__(self):
        self.security = ConfigurableHTTPBearer()
        # Get from environment variable, default to True (strict auth)
        self.require_auth = os.getenv('REQUIRE_AUTH', 'true').lower() == 'true'

    async def check_auth(
        self, 
        request: Request, 
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(ConfigurableHTTPBearer()),
        db: Session = Depends(get_db)
    ):
        if not self.require_auth:
            # If auth is not required, always pass
            return credentials

        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail="Missing authentication credentials"
            )

        # Verify the token and get client info
        client_info = verify_token(credentials.credentials, db)
        
        # Add client info to request state for use in endpoints
        request.state.client_info = client_info
        
        return credentials

import os  # Add this import at the top
auth_middleware = AuthMiddleware()