from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Union
import structlog

import auth
from schemas import Aluno, AlunoCreate
from models import Aluno as ModelAluno
from database import get_db

# Get a structlog logger instance
logger = structlog.get_logger(__name__)

alunos_router = APIRouter()

# Função auxiliar para obter um aluno ou levantar uma exceção 404
def get_aluno_or_404(aluno_id: int, db: Session = Depends(get_db)) -> ModelAluno:
    """
    Busca um aluno pelo ID no banco de dados.
    Levanta uma exceção HTTPException 404 se o aluno não for encontrado.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return db_aluno

@alunos_router.get("/alunos", response_model=List[Aluno])
def read_alunos(
    db: Session = Depends(get_db), current_user: Aluno = Depends(auth.get_current_active_user)
):
    """
    Retorna uma lista de todos os alunos cadastrados.

    """
    alunos = db.query(ModelAluno).all()
    return [Aluno.from_orm(aluno) for aluno in alunos]

@alunos_router.get("/alunos/{aluno_id}", response_model=Aluno)
def read_aluno(db_aluno: ModelAluno = Depends(get_aluno_or_404)):
    """
    Retorna os detalhes de um aluno específico com base no ID fornecido.

    Args:
        aluno_id: O ID do aluno.

    Raises:
        HTTPException: Se o aluno não for encontrado.
    """
    return Aluno.from_orm(db_aluno)

@alunos_router.post("/alunos", response_model=Aluno, status_code=201)
def create_aluno(aluno: AlunoCreate, db: Session = Depends(get_db)):
    """
    Cria um novo aluno com os dados fornecidos.

    Args:
        aluno: Dados do aluno a ser criado.

    Returns:
        Aluno: aluno criado.
    """ 
    db_aluno_exists = db.query(ModelAluno).filter(ModelAluno.email == aluno.email).first()
    if db_aluno_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Cria um Aluno sem senha. O campo hashed_password será NULL.
    db_aluno = ModelAluno(**aluno.dict()) 
    db.add(db_aluno)
    db.commit()
    db.refresh(db_aluno)
    logger.info(
        "Student created successfully", 
        student_id=db_aluno.id, 
        student_email=db_aluno.email
    )
    return Aluno.from_orm(db_aluno)

@alunos_router.put("/alunos/{aluno_id}", response_model=Aluno)
def update_aluno(aluno: Aluno, db_aluno: ModelAluno = Depends(get_aluno_or_404), db: Session = Depends(get_db)):
    """
    Atualiza os dados de um aluno existente.

    Args:
        aluno_id: O ID do aluno a ser atualizado.
        aluno: Os novos dados do aluno.

    Raises:
        HTTPException: 404 - Aluno não encontrado.

    Returns:
        Aluno: O aluno atualizado.
    """
    for key, value in aluno.dict(exclude_unset=True).items():
        setattr(db_aluno, key, value)

    db.commit()
    db.refresh(db_aluno)
    return Aluno.from_orm(db_aluno)

@alunos_router.delete("/alunos/{aluno_id}", response_model=Aluno)
def delete_aluno(db_aluno: ModelAluno = Depends(get_aluno_or_404), db: Session = Depends(get_db)):
    """
    Exclui um aluno.

    Args:
        aluno_id: O ID do aluno a ser excluído.

    Raises:
        HTTPException: 404 - Aluno não encontrado.

    Returns:
        Aluno: O aluno excluído.
    """
    aluno_deletado = Aluno.from_orm(db_aluno)

    db.delete(db_aluno)
    db.commit()
    return aluno_deletado

@alunos_router.get("/alunos/nome/{nome_aluno}", response_model=Union[Aluno, List[Aluno]]) 
def read_aluno_por_nome(nome_aluno: str, db: Session = Depends(get_db)):
    """
    Busca alunos pelo nome (parcial ou completo).
    
    Args:
        nome_aluno: O nome (ou parte do nome) do aluno a ser buscado.
    
    Raises:
        HTTPException: 404 - Nenhum aluno encontrado com esse nome.
        
    Returns:
        Union[Aluno, List[Aluno]]: Um único objeto `Aluno` se houver apenas uma correspondência, 
        ou uma lista de `Aluno` se houver várias correspondências.
    """
    db_alunos = db.query(ModelAluno).filter(ModelAluno.nome.ilike(f"%{nome_aluno}%")).all() # ilike para case-insensitive

    if not db_alunos:
        raise HTTPException(status_code=404, detail="Nenhum aluno encontrado com esse nome")

    if len(db_alunos) == 1:  # Retorna um único Aluno se houver apenas uma correspondência
        return Aluno.from_orm(db_alunos[0])

    return [Aluno.from_orm(aluno) for aluno in db_alunos]

@alunos_router.get("/alunos/email/{email_aluno}", response_model=Aluno)
def read_aluno_por_email(email_aluno: str, db: Session = Depends(get_db)):
    """
    Busca um aluno pelo email.

    Args:
        email_aluno: O email do aluno a ser buscado.
        
    Raises:
         HTTPException: 404 - Nenhum aluno encontrado com esse email.

    Returns:
        Aluno: O aluno encontrado.
    """
    db_aluno = db.query(ModelAluno).filter(ModelAluno.email == email_aluno).first()

    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Nenhum aluno encontrado com esse email")
    
    return Aluno.from_orm(db_aluno)
