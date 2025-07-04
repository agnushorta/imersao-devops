# Part 2: Dockerization and Image Optimization

With our database successfully containerized, the next challenge was to build an efficient and lean Docker image for our FastAPI application. This post details our journey from a basic build to a highly optimized, production-ready image.

---

### The Build Journey: Solving the `pg_config` Error

During our first attempt to build the image with `docker-compose up --build`, we hit a common but frustrating roadblock: `ERROR: pg_config executable not found.`

This error occurred because `pip`, the Python package installer, couldn't find a pre-compiled binary (`wheel`) for the `psycopg2` database driver that matched our minimal `python:3.11-alpine` base image. As a fallback, it tried to build the driver from source code. However, the lean Alpine image lacked the necessary system-level build tools (like a C compiler and the PostgreSQL development headers) to do so.

The solution was to explicitly install these tools within our `Dockerfile` using Alpine's package manager, `apk`. By adding the line `RUN apk add --no-cache postgresql-dev build-base`, we provided the build environment with everything it needed to compile `psycopg2` successfully.

### Advanced Optimization: Creating Lean Images with Multi-Stage Builds

Our image was now functional, but it was bloated. It contained build tools (`build-base`, `postgresql-dev`) that are necessary for compiling dependencies but are completely unnecessary—and a potential security risk—for simply *running* the application.

To solve this, we implemented a powerful Docker feature: **multi-stage builds**.

1.  **Stage 1 (The "builder"):** We defined a temporary build environment based on `python:3.11-alpine`. In this stage, we installed all the heavy build tools and compiled our Python dependencies.
2.  **Stage 2 (The "final" image):** We started fresh with a new, clean `python:3.11-alpine` image. Into this pristine environment, we installed *only* the lightweight runtime library for PostgreSQL (`libpq`). Then, we used the `COPY --from=builder` command to copy the pre-compiled Python packages from the "builder" stage and our application code.


```dockerfile
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/Dockerfile

# --- Estágio 1: O Construtor (Builder) ---
FROM python:3.11-alpine AS builder
WORKDIR /app
RUN apk add --no-cache postgresql-dev build-base
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Estágio 2: A Imagem Final ---
FROM python:3.11-alpine
WORKDIR /app
# Instala APENAS as dependências de tempo de execução
RUN apk add --no-cache libpq
# Copia as dependências Python instaladas do estágio "builder"
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# Copia o código da aplicação
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

This technique resulted in a final image that was drastically smaller and more secure, as it contained only the bare essentials required to run the application.

---

Now that our application is running in a lean, optimized container, the next step is to look inward and improve the quality of the code itself. Stay tuned for Part 3, where we'll refactor our code for better maintainability.
