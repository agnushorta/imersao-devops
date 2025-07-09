# Part 6: Securing the API with JWT Authentication

With a robust, observable, and well-structured application, the final frontier is security. An API without authentication is a house without doors. In this post, we'll implement a modern, secure authentication system using JSON Web Tokens (JWT) with the RS256 algorithm.

---

### Why JWT and RS256?

We chose JWT for its stateless nature, which is perfect for scalable APIs. A client logs in once, receives a token, and sends that token with every subsequent request. The server can verify this token without needing to look up a session in the database.

We specifically chose the **RS256 (RSA with SHA-256)** signing algorithm over the simpler HS256. RS256 uses an asymmetric key pair (a private key to sign, a public key to verify). This is a major security advantage:

-   **The private key** is kept as an absolute secret on the authentication server. It is the only key that can create new, valid tokens.
-   **The public key** can be safely distributed to other services. They can verify that a token is legitimate, but they cannot create new ones.

This separation is ideal for microservice architectures and enhances overall security.

### The Implementation Strategy

Our implementation involved several key components working together:

1.  **Password Hashing with `passlib`:** We never store passwords in plain text. We use the `passlib` library with the `bcrypt` algorithm to create a strong, salted hash of the user's password, which is what we store in the new `hashed_password` column in our database.

2.  **Key Generation and Management:** We used `openssl` to generate a 2048-bit RSA key pair (`private_key.pem` and `public_key.pem`). The private key is kept out of version control (via `.gitignore`) and loaded securely into the application using environment variables.

3.  **A Central `auth.py` Module:** We encapsulated all security logic here. This module contains functions to:
    -   Verify a plain password against a stored hash.
    -   Create a new JWT, signing it with the private key.
    -   Decode and verify an incoming JWT using the public key.

4.  **User Creation and Login Endpoints:** We created two new routers:
    -   `routers/users.py`: Provides a `POST /users` endpoint for new users to register.
    -   `routers/auth.py`: Contains the `POST /token` endpoint. This endpoint follows the OAuth2 standard, accepting a `username` (our user's email) and `password`. If the credentials are valid, it returns a signed JWT access token.

5.  **FastAPI's Security Dependencies:** We leveraged FastAPI's dependency injection system to protect our routes. We created a `get_current_user` dependency in our `auth.py` module. This function:
    -   Expects an `Authorization: Bearer <token>` header.
    -   Decodes and validates the token.
    -   Fetches the corresponding user from the database.
    -   If any step fails, it automatically raises a `401 Unauthorized` error.

By adding `current_user: Aluno = Depends(auth.get_current_active_user)` to any path operation function's parameters, we can lock it down. This not only ensures that only authenticated users can access the endpoint but also injects the current user's data directly into our function, making it available for further logic.

```python
# Example of a protected route in routers/alunos.py

@alunos_router.get("/alunos", response_model=List[Aluno])
def read_alunos(
    db: Session = Depends(get_db), 
    current_user: Aluno = Depends(auth.get_current_active_user)
):
    """
    Retorna uma lista de todos os alunos cadastrados.
    """
    alunos = db.query(ModelAluno).all()
    return [Aluno.from_orm(aluno) for aluno in alunos]
