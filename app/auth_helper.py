# app/auth_helper.py
from fastapi import HTTPException
from data.datamodels import CredentialsCheckResult, Credentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from data.db import crud
from sqlalchemy.orm import Session

load_dotenv(override=True)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-please-change-in-production")
ALGORITHM = "HS256"

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def check_credentials(credentials: Credentials, db: Session):
    return authenticate_user(credentials.client_id, credentials.client_secret, db)

def authenticate_user(client_id: str, client_secret: str, db: Session):
    client_info = crud.get_client_info_by_id(db=db, client_id=client_id)

    if client_info is None:
        return CredentialsCheckResult(is_valid=False, message="client_id is invalid")
    
    if client_secret == client_info.client_secret:
        return CredentialsCheckResult(is_valid=True, message="Credentials are valid")    
    else:
        return CredentialsCheckResult(is_valid=False, message="Incorrect client_secret")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id = payload.get("sub")
        if client_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
        return client_id
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

def verify_token(token: str, db: Session):
    try:
        client_id = decode_access_token(token)
        client_info = crud.get_client_info_by_id(db=db, client_id=client_id)
        if client_info is None:
            raise HTTPException(
                status_code=401,
                detail="Client not found"
            )
        return client_info
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )