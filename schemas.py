from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date

# --- Schemas for Authentication ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    password: str
    telefone: str
    data_nascimento: Optional[date] = None

# --- Existing Schemas (with modifications) ---

class Matricula(BaseModel):
    aluno_id: int
    curso_id: int

    class Config:
        from_attributes = True

Matriculas = List[Matricula]

class AlunoCreate(BaseModel):
    nome: str
    email: EmailStr
    telefone: str
    data_nascimento: Optional[date] = None

    class Config:
        from_attributes = True
class Aluno(BaseModel):
    id: int
    nome: str
    email: EmailStr
    telefone: str
    data_nascimento: Optional[date] = None

    class Config:
        from_attributes = True

Alunos = List[Aluno]

class Curso(BaseModel):
    nome: str
    codigo: str
    descricao: str

    class Config:
        from_attributes = True

Cursos = List[Curso]
