# Part 1: Migrating from SQLite to PostgreSQL

Welcome to the first deep-dive of our series! This post covers the foundational steps of upgrading our application's database from a simple file-based SQLite to a robust, containerized PostgreSQL server.

---

### Switching the Database Connector

The first step is to teach our SQLAlchemy-based application to "speak" PostgreSQL. This requires a specific database driver. We chose the most common and reliable one, `psycopg2`, and added `psycopg2-binary` to our `requirements.txt` to make it available to our application.

```
# requirements.txt
...
psycopg2-binary==2.9.2
python-dotenv==1.1.1
```

### Secure Connection Configuration

With the driver in place, we shifted from pointing to a local file to a database server. To do this securely and avoid hard-coding credentials, we adopted environment variables, managed by `python-dotenv`.

Our `database.py` was updated to build the `DATABASE_URL` dynamically from variables like `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_HOST`, which are loaded from a `.env` file. This is a critical security practice.


```python
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração da URL de conexão com o PostgreSQL a partir das variáveis de ambiente
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
Para que isso funcione localmente, criamos um arquivo `.env` na raiz do projeto:

```
# .env
POSTGRES_USER=meu_usuario_dev
POSTGRES_PASSWORD=minha_senha_super_secreta
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=escola_db
```
*Nota: O `POSTGRES_HOST` está como `db` porque esse será o nome do nosso serviço de banco de dados dentro da rede do Docker Compose.*

### Orchestration with Docker Compose

We used `docker-compose.yml` to define and run our multi-container application. This file orchestrates our two main services: `api` (our FastAPI application) and `db` (the PostgreSQL database).

Key features of our `docker-compose.yml`:
-   **`db` Service:** Uses the official `postgres:13-alpine` image and is configured via the same `.env` file.
-   **Named Volume:** A volume named `postgres_data` ensures our database data persists even if the container is recreated.
-   **Healthcheck & `depends_on`:** This is a critical combination for a reliable startup. A simple `depends_on` only ensures that the `db` container *starts* before the `api` container, not that the PostgreSQL service *inside* is ready.
    -   The `healthcheck` block in the `db` service tells Docker to periodically run the `pg_isready` command inside the container. This command specifically checks if the PostgreSQL server is ready to accept connections.
    -   The `api` service then uses `depends_on: db: condition: service_healthy`. This instructs Docker Compose to wait until the `db` container's healthcheck passes before starting the API. This elegant solution prevents race conditions and connection errors on startup.

### Solving the 'Connection Refused' Error

A classic Docker networking issue appeared: `connection refused` to `localhost`. This is because, inside a container, `localhost` refers to the container itself, not other services on the Docker network.

The fix was simple but fundamental: we set the `POSTGRES_HOST` environment variable in our `.env` file to `db`, which is the service name of our database in the Docker Compose network. Docker's internal DNS resolves this name to the correct container IP address, establishing a successful connection.

---

With the database successfully migrated and containerized, our next step is to build and optimize the Docker image for our API. Stay tuned for Part 2!
