from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

class TokenData(BaseModel):
    username: str
    user_id: str
    role: str
    is_guardian: int


SECRET_KEY = "super-secret-key"  # Use environment variable in prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# def decode_token(token: str):
#     return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def decode_token(token: str) -> TokenData:
    try:
        print("Decoding token")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Getting info from token {payload}")
        username = payload.get("username")
        # user_id = payload.get("user_id")
        role = payload.get("role")
        is_guardian = payload.get("is_guardian")

# add userid? TODO
        return TokenData(
            username=username,
            user_id="",
            role=role,
            is_guardian=is_guardian
        )
    except JWTError:
        raise Exception(status_code=401, detail="Could not validate credentials")
