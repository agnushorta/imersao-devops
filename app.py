from fastapi import FastAPI, Request
from fastapi.responses import Response
from database import engine, Base
from logging_config import setup_logging, request_id_var
from routers.alunos import alunos_router
from routers.cursos import cursos_router
from routers.matriculas import matriculas_router
from routers.auth import auth_router
from routers.users import users_router

import structlog
import uuid

# Setup custom logging
setup_logging()

# It's better to handle database schema creation and migrations with a dedicated
# tool like Alembic, rather than on application startup.
# Base.metadata.create_all(bind=engine)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="API de Gestão Escolar", 
    description="""
        This API provides endpoints to manage students, courses, and classes in an educational institution.
        It allows performing different operations on each of these entities.
    """, 
    version="1.0.0",
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Middleware to add a unique request ID to each incoming request.
    The ID is taken from the 'X-Request-ID' header if present,
    otherwise a new UUID is generated.
    """
    # Use existing request ID from header or generate a new one
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Store the request ID in the context variable
    token = request_id_var.set(request_id)
    
    logger.info("Request started", method=request.method, url=str(request.url))
    
    response = await call_next(request)
    
    # Add the request ID to the response headers for client-side tracking
    response.headers["X-Request-ID"] = request_id
    
    # Reset the context variable
    request_id_var.reset(token)
    
    return response

app.include_router(alunos_router, tags=["alunos"])
app.include_router(cursos_router, tags=["cursos"])
app.include_router(matriculas_router, tags=["matriculas"])
app.include_router(auth_router, tags=["Autenticação"])
app.include_router(users_router, tags=["Usuários"])
