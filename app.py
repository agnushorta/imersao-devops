from fastapi import FastAPI
from database import engine, Base
from logging_config import setup_logging
from routers.alunos import alunos_router
from routers.cursos import cursos_router
from routers.matriculas import matriculas_router

# Setup custom logging
setup_logging()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Gestão Escolar", 
    description="""
        This API provides endpoints to manage students, courses, and classes in an educational institution.
        It allows performing different operations on each of these entities.
    """, 
    version="1.0.0",
)

app.include_router(alunos_router, tags=["alunos"])
app.include_router(cursos_router, tags=["cursos"])
app.include_router(matriculas_router, tags=["matriculas"])
