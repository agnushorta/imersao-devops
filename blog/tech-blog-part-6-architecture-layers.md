# Tech Deep Dive Part 6: A Arquitetura em Camadas de uma API Robusta

Bem-vindo a mais um mergulho técnico! Hoje, vamos dissecar a espinha dorsal da nossa aplicação FastAPI: a separação de responsabilidades entre os arquivos `models.py`, `schemas.py` e `database.py`.

Entender essa estrutura não é apenas uma boa prática; é o segredo para construir APIs que são escaláveis, seguras e, acima de tudo, fáceis de manter. Pense nesses três arquivos como as camadas de especialização da sua aplicação:

1.  **`models.py`**: A planta baixa do seu banco de dados.
2.  **`schemas.py`**: O cardápio da sua API (o que entra e o que sai).
3.  **`database.py`**: A central de conexões que liga tudo.

Vamos detalhar cada um.

---

### 1. `models.py`: A Planta Baixa do Banco de Dados (SQLAlchemy)

Este arquivo define **como seus dados são armazenados no banco de dados**. Ele usa o ORM (Mapeamento Objeto-Relacional) do SQLAlchemy para mapear classes Python diretamente para tabelas em um banco de dados SQL.

*   **Responsabilidade Principal:** Descrever a estrutura das tabelas, colunas, tipos de dados (`Integer`, `String`) e os relacionamentos entre elas.
*   **Tecnologia:** SQLAlchemy.

```python
# models.py
class Aluno(Base):
    __tablename__ = "alunos" # Nome da tabela no banco

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # A senha criptografada vive aqui

    matriculas = relationship("Matricula", back_populates="aluno")
```

Em resumo: se você precisar adicionar uma nova coluna ou criar uma nova tabela, é no `models.py` que você vai trabalhar. Ele é o "molde" do seu banco de dados.

---

### 2. `schemas.py`: O Cardápio da API (Pydantic)

Este arquivo define **a forma dos dados que sua API espera receber e que promete enviar**. Ele atua como uma camada de validação e serialização, garantindo que os dados que entram e saem da sua API sigam um formato específico.

*   **Responsabilidade Principal:** Definir o "contrato" de dados para os endpoints da API. O que é obrigatório? Qual o tipo de cada campo?
*   **Tecnologia:** Pydantic.

```python
# schemas.py
class Aluno(BaseModel): # Note que herda de BaseModel do Pydantic
    id: int
    nome: str
    email: EmailStr # Validação de e-mail gratuita!
    # Note a ausência do hashed_password!

    class Config:
        from_attributes = True # Permite que o Pydantic leia dados de um objeto SQLAlchemy
```

**A Grande Diferença:** Compare o schema `Aluno` com o model `Aluno`. O schema **não tem** o campo `hashed_password`. Isso é intencional e crucial para a segurança! Nós nunca queremos que a senha, mesmo criptografada, seja exposta pela API. O schema define a **visão pública** dos seus dados, enquanto o model define a **estrutura interna e privada**.

---

### 3. `database.py`: A Central de Conexões

Este arquivo é o "encanamento" do projeto. Ele é responsável por criar e gerenciar a conexão com o banco de dados e fornecer sessões para que os endpoints possam interagir com ele.

*   **Responsabilidade Principal:** Configurar a conexão com o banco de dados e fornecer uma maneira de obter uma sessão de banco de dados para cada requisição.
*   **Tecnologia:** SQLAlchemy.

```python
# database.py
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db(): # A dependência que os endpoints usam
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### Como Tudo se Conecta: O Fluxo de uma Requisição

Imagine que um cliente faz um `GET` para `/alunos/1`:

1.  A requisição chega ao endpoint `read_aluno`.
2.  O endpoint declara que depende de `get_db`. O FastAPI executa a função `get_db` (de `database.py`) e obtém uma sessão (`db`).
3.  O código do endpoint usa a sessão para fazer uma query no banco: `db.query(ModelAluno)...`. Note que ele usa o **Model** (`ModelAluno` de `models.py`) para interagir com o banco.
4.  O banco de dados retorna um objeto `ModelAluno`.
5.  O endpoint retorna esse objeto.
6.  O FastAPI, vendo que o `response_model` é o **Schema** `Aluno` (de `schemas.py`), usa o Pydantic para converter o objeto `ModelAluno` em um JSON, garantindo que apenas os campos definidos no schema (sem `hashed_password`) sejam enviados na resposta.

Essa separação clara torna seu código muito mais organizado, seguro e fácil de evoluir: `models.py` cuida do banco, `schemas.py` cuida da API e `database.py` cuida da conexão.
