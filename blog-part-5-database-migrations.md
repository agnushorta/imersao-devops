# Part 5: Evolving Your Database with Alembic Migrations

Welcome to a special deep-dive post! So far, our application has been creating its database schema using a simple command: `Base.metadata.create_all(bind=engine)`. While great for getting started, this approach has a major limitation: it cannot handle changes to your existing tables. This is where a true database migration tool becomes essential.

---

### The Problem: Why `create_all` Isn't Enough

The `create_all` command is a blunt instrument. It checks if a table exists, and if it doesn't, it creates it based on your current models. However, what happens when you need to add a new column, remove an old one, or change a data type? `create_all` will not detect or apply these changes to an existing table.

Attempting to manage schema changes manually across different environments (development, staging, production) is a recipe for disaster. You need a systematic, version-controlled way to evolve your database schema alongside your application code.

### The Solution: Alembic, the SQLAlchemy Migration Tool

**Alembic** is the standard, battle-tested database migration tool for SQLAlchemy. It treats your database schema like source code, allowing you to:

1.  **Generate Migration Scripts:** Alembic can compare your SQLAlchemy models against the current state of the database and automatically generate a Python script that contains the necessary changes.
2.  **Version Control Your Schema:** Each migration script is a file that can be committed to Git, creating a versioned history of your database schema.
3.  **Upgrade and Downgrade:** You can apply migrations to move your database to a newer version (`upgrade`) or revert changes to return to a previous state (`downgrade`).

### Integrating Alembic into Our Project: A Step-by-Step Guide

Here’s the detailed, real-world process we followed to integrate Alembic, including the common pitfalls and their solutions.

#### 1. Installation and Initialization

First, we added `alembic` to our `requirements.txt`. Then, from the root directory of our project, we ran the initialization command:

```bash
alembic init alembic
```

This command is the starting point. It creates:
-   `alembic.ini`: The main configuration file.
-   `alembic/`: A new directory containing the migration environment, including `env.py` (the heart of the configuration) and a `versions/` subdirectory for the migration scripts.

#### 2. Configuration (`alembic/env.py`): The Bridge to Your Application

Out of the box, Alembic doesn't know anything about our application. We need to configure `alembic/env.py` to teach it two crucial things:
-   **What our schema should look like:** By pointing it to our SQLAlchemy models.
-   **How to connect to the database:** By providing our database URL.

We made the following changes to `alembic/env.py`:

```python
# alembic/env.py

# ... (imports)
# Add these lines to give Alembic access to our app's modules
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import Base
from database import DATABASE_URL
# ...

# Find this line:
# target_metadata = None
# And change it to:
target_metadata = Base.metadata

# ...

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # We simplified this section to connect directly using our DATABASE_URL,
    # which is more robust and avoids potential configuration parsing errors.
    connectable = create_engine(DATABASE_URL)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

#### 3. Generating Migrations: The Local Developer Workflow

This is a critical concept: generating migrations with `alembic revision --autogenerate` is a **developer task performed on your local machine**, not inside the container. This command compares your code to the running database and creates the migration script (the "blueprint").

When we first tried to run it, we hit a classic Docker networking error:

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not translate host name "db" to address...
```

This happens because our `.env` file correctly sets `POSTGRES_HOST=db` for communication *inside* the Docker network. However, our local machine doesn't know what `db` means. From our local machine, the database is accessible at `localhost`.

The solution is to temporarily override the environment variable just for this command:

```bash
POSTGRES_HOST=localhost alembic revision --autogenerate -m "Add data_nascimento to Aluno table"
```

This command connects to the database via `localhost`, compares the schema to our updated `models.py`, and generates the new migration file in `alembic/versions/`. This new file is then committed to Git.

#### 4. Automating Migrations on Startup: The Production Workflow

With the migration script generated and committed, we need to ensure it's applied automatically when the application starts. This is the job of the container.

First, we removed the now-redundant `Base.metadata.create_all(bind=engine)` line from `app.py`. Alembic is now the sole manager of our schema.

Then, we updated the `command` in our `docker-compose.yml`:

    ```yaml
    # docker-compose.yml
    services:
      api:
        # ...
    command: sh -c "alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
        # ...
    ```

    This command ensures that every time the API container starts, it first runs `alembic upgrade head`. This command applies any pending migrations, bringing the database schema to the latest version before the application server starts.

### The Daily Workflow in Action: Adding the `data_nascimento` Field

To see how this works in practice, let's walk through the exact steps we took to add a `data_nascimento` (birth date) field to our `Aluno` model.

#### Step 1: Update the Code

First, we update our code to reflect the new field. This involves two files:

*   **The SQLAlchemy Model (`models.py`):** We declare the new column in the database table.

    ```python
    # models.py
    from sqlalchemy import Column, Date, ...

    class Aluno(Base):
        __tablename__ = "alunos"
        # ... existing columns
        data_nascimento = Column(Date, nullable=True)
    ```

*   **The Pydantic Schema (`schemas.py`):** We add the field to our API data structure so it can be sent and received.

    ```python
    # schemas.py
    from datetime import date
    from typing import Optional
    
    class Aluno(BaseModel):
        # ... existing fields
        data_nascimento: Optional[date] = None
    ```

#### Step 2: Generate the Migration Script

With the code updated, we run the `autogenerate` command on our local machine to create the migration "blueprint":

```bash
POSTGRES_HOST=localhost alembic revision --autogenerate -m "Add data_nascimento to Aluno table"
```
Alembic compares our updated models to the database schema, detects the new `data_nascimento` column, and creates a new Python script in `alembic/versions/` with the `upgrade()` and `downgrade()` functions to add and remove the column.

#### Step 3: Commit and Apply

We commit this new migration script to Git. The next time the application starts (via `docker-compose up` or a CI/CD deployment), the `alembic upgrade head` command in our `docker-compose.yml` will automatically find and apply this new script, bringing the database schema in sync with our code.

With this setup, our database schema evolves reliably and automatically alongside our application code, a fundamental practice for professional software development.
