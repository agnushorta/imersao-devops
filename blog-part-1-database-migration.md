# Part 1: Migrating from SQLite to PostgreSQL

Welcome to the first deep-dive of our series! This post covers the foundational steps of upgrading our application's database from a simple file-based SQLite to a robust, containerized PostgreSQL server.

---

### Switching the Database Connector

The first step is to teach our SQLAlchemy-based application to "speak" PostgreSQL. This requires a specific database driver. We chose the most common and reliable one, `psycopg2`, and added `psycopg2-binary` to our `requirements.txt` to make it available to our application.

### Secure Connection Configuration

With the driver in place, we shifted from pointing to a local file to a database server. To do this securely and avoid hard-coding credentials, we adopted environment variables, managed by `python-dotenv`.

Our `database.py` was updated to build the `DATABASE_URL` dynamically from variables like `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_HOST`, which are loaded from a `.env` file. This is a critical security practice.

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
