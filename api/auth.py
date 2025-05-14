# api/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from datetime import timedelta
from data.datamodels import Credentials, CredentialsCheckResult
from app.auth_helper import check_credentials, create_access_token
from app.auth_middleware import auth_middleware, get_db
from sqlalchemy.orm import Session
from api.app import app, ACCESS_TOKEN_EXPIRE_HOURS

@app.post("/get_token")
async def get_token(credentials: Credentials, db: Session = Depends(get_db)):
    """
    Generate authentication token for API access.

    - **credentials**: Client credentials (client_id and client_secret)
    """
    if not auth_middleware.require_auth:
        # If auth is not required, return a dummy token
        return {
            "access_token": "dummy_token_for_testing",
            "token_type": "bearer"
        }
    
    credentials_check_result = check_credentials(credentials, db)

    if credentials_check_result.is_valid:
        access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        access_token = create_access_token(
            data={"sub": credentials.client_id}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail=credentials_check_result.message)