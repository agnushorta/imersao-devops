# Part 3: Improving Code Quality with Refactoring

With a functional, containerized application running smoothly, our focus shifted inward to the quality and maintainability of the code itself. A clean codebase is just as important as a functional one for the long-term health of a project.

---

### The Problem: Repetitive Code

While reviewing our code, we identified a pattern in `routers/alunos.py`. The endpoints for reading, updating, and deleting a single student all started with the exact same block of logic:

1.  Query the database for a student by their ID.
2.  Check if the student exists.
3.  If not, raise a 404 `HTTPException`.

This repetition violated a core software engineering principle: **DRY (Don't Repeat Yourself)**. While functional, this approach meant that any change to this logic (like modifying the error message) would need to be done in multiple places, increasing the risk of bugs and making maintenance more difficult.

### The Solution: The DRY Principle and FastAPI Dependencies

To solve this, we leveraged one of FastAPI's most powerful features: **Dependencies**. We created a single, reusable function, `get_aluno_or_404`, that encapsulates this entire lookup-and-validate logic.

By defining this function and using it as a dependency in our path operations, we delegate the task of fetching and validating the student to FastAPI. The endpoint function only runs if the dependency is successful (i.e., the student is found), and it receives the fetched student object directly as an argument.


```python
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/routers/alunos.py

# Função auxiliar para obter um aluno ou levantar uma exceção 404
def get_aluno_or_404(aluno_id: int, db: Session = Depends(get_db)) -> ModelAluno:
    db_aluno = db.query(ModelAluno).filter(ModelAluno.id == aluno_id).first()
    if db_aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return db_aluno

# Exemplo de uso nos endpoints
@alunos_router.get("/alunos/{aluno_id}", response_model=Aluno)
def read_aluno(db_aluno: ModelAluno = Depends(get_aluno_or_404)):
    return Aluno.from_orm(db_aluno)

@alunos_router.put("/alunos/{aluno_id}", response_model=Aluno)
def update_aluno(aluno: Aluno, db_aluno: ModelAluno = Depends(get_aluno_or_404), db: Session = Depends(get_db)):
    # ... lógica de atualização ...

@alunos_router.delete("/alunos/{aluno_id}", response_model=Aluno)
def delete_aluno(db_aluno: ModelAluno = Depends(get_aluno_or_404), db: Session = Depends(get_db)):
    # ... lógica de exclusão ...
```

This refactoring centralized our data access logic, making our endpoints cleaner, more declarative, and significantly easier to read and maintain.

---

Now that our code is cleaner and more robust, we're ready to tackle the final piece of a production-ready application: observability. Stay tuned for Part 4, where we'll implement a comprehensive logging system.
