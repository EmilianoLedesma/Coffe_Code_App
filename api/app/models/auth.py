from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    correo_electronico: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    rol: str
