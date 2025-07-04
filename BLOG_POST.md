# Migrando uma API FastAPI de SQLite para PostgreSQL com Docker: Um Guia Passo a Passo

Muitos projetos de software começam com uma base de dados simples como o SQLite. É leve, não requer um servidor e é perfeito para prototipagem e desenvolvimento inicial. No entanto, à medida que uma aplicação cresce, a necessidade de um sistema de banco de dados mais robusto, escalável e com suporte a concorrência se torna evidente. O PostgreSQL é uma escolha fantástica para esse próximo passo.

Neste guia, vamos documentar a jornada completa de migração de uma API FastAPI que usava SQLite para o PostgreSQL, tudo isso orquestrado com Docker e Docker Compose para criar um ambiente de desenvolvimento limpo, reproduzível e pronto para produção.

## Passo 1: Trocando o Conector do Banco

A primeira etapa é ensinar nossa aplicação, que usa o ORM SQLAlchemy, a "falar" com o PostgreSQL. Para isso, precisamos de um *driver* de banco de dados.

A biblioteca mais comum e recomendada para essa tarefa é a **`psycopg2`**.

Adicionamos `psycopg2-binary` e `python-dotenv` (que usaremos para gerenciar nossas credenciais) ao nosso arquivo `requirements.txt`.

```
# requirements.txt
...
psycopg2-binary==2.9.2
python-dotenv==1.1.1
```

## Passo 2: Configurando a Conexão de Forma Segura

Com o driver pronto, precisamos alterar a forma como o SQLAlchemy se conecta ao banco. Em vez de apontar para um arquivo local (`escola.db`), vamos apontar para um servidor PostgreSQL. É uma prática de segurança fundamental não deixar credenciais (usuário, senha) diretamente no código. Usaremos variáveis de ambiente.

Alteramos nosso arquivo `database.py`:

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

## Passo 3: Orquestrando Tudo com Docker Compose

Agora, a mágica da orquestração. Vamos configurar o `docker-compose.yml` para subir não apenas nossa API, mas também um contêiner com o banco de dados PostgreSQL.

```yaml
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/docker-compose.yml
services:
  api:
    build: .
    container_name: api
    ports: 
      - "8000:8000"
    volumes:
      - .:/app
    command: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
    env_file:
      - .env # Carrega as variáveis de ambiente para a API
    depends_on:
      db:
        condition: service_healthy # Garante que a API só inicie quando o DB estiver saudável

  db:
    image: postgres:13-alpine
    container_name: postgres_db
    volumes:
      - postgres_data:/var/lib/postgresql/data/ # Persiste os dados do banco
    ports:
      - "5432:5432"
    env_file:
      - .env # Usa as mesmas variáveis para configurar o banco
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Pontos de Destaque no `docker-compose.yml`:
- **Serviço `db`:** Usa a imagem oficial `postgres:13-alpine`. Ele carrega as variáveis do `.env` para se autoconfigurar, criando o banco de dados e o usuário na primeira inicialização.
- **Volume `postgres_data`:** Garante que nossos dados não sejam perdidos quando os contêineres são recriados.
- **`healthcheck`:** Uma adição crucial! Ele verifica se o PostgreSQL está realmente pronto para aceitar conexões antes de permitir que a API inicie.
- **`depends_on` com `condition: service_healthy`:** Conecta o `healthcheck` do banco ao início da API, evitando erros de conexão durante a inicialização.

## Passo 4: A Jornada do Build - Resolvendo o Erro `pg_config`

Com tudo configurado, era hora de construir a imagem com `docker-compose up --build`. E então, o primeiro obstáculo:

```
ERROR: pg_config executable not found.
```

Esse erro acontece porque o `pip` não encontrou um binário pré-compilado (`wheel`) do `psycopg2` para a nossa imagem base (`python:3.11-alpine`) e tentou compilá-lo do zero. A imagem Alpine, por ser minimalista, não tem as ferramentas de compilação necessárias.

A solução foi editar nosso `Dockerfile` para instalar essas dependências manualmente.

```dockerfile
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/Dockerfile
# Use a imagem oficial do Python na versão Alpine, que é extremamente leve.
FROM python:3.11-alpine

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de requirements para o diretório de trabalho
COPY requirements.txt .

# Instala as dependências do sistema (para Alpine) necessárias para compilar o psycopg2
# postgresql-dev: Contém os arquivos de desenvolvimento do PostgreSQL (incluindo pg_config)
# build-base: Contém o compilador C (gcc) e outras ferramentas de build
RUN apk add --no-cache postgresql-dev build-base

# Instala as dependências do projeto usando pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação para o diretório de trabalho
COPY . .

# Expõe a porta 8000 para que a aplicação possa ser acessada
EXPOSE 8000

# Define o comando a ser executado quando o container for iniciado
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```
A linha `RUN apk add --no-cache postgresql-dev build-base` foi a chave. Ela usa o gerenciador de pacotes do Alpine (`apk`) para instalar as ferramentas de desenvolvimento do PostgreSQL e o compilador C. Com isso, o `pip` conseguiu compilar o `psycopg2` com sucesso.

## Perguntas que Surgiram no Caminho

Durante o processo, algumas dúvidas importantes foram esclarecidas:

- **Preciso alterar meus `models.py`?** Não! Uma das maiores vantagens de um ORM como o SQLAlchemy é a abstração. Os modelos são definidos de forma agnóstica, e o SQLAlchemy, junto com o driver `psycopg2`, se encarrega de traduzir tudo para o SQL específico do PostgreSQL.

- **Quem cria o banco de dados e as tabelas?** O **banco de dados** (`escola_db`) é criado pelo script de inicialização da imagem `postgres` do Docker, que lê a variável de ambiente `POSTGRES_DB`. As **tabelas** (`alunos`, `cursos`, etc.) são criadas pela nossa aplicação FastAPI na inicialização, graças à linha `Base.metadata.create_all(bind=engine)` no arquivo `app.py`.

- **Por que um `Dockerfile` para a API, mas não para o Postgres?** Porque nossa API é um software customizado. Precisamos de uma "receita" (`Dockerfile`) para construir uma imagem que contenha nosso código e dependências. Já o PostgreSQL é um software padrão; podemos simplesmente usar a imagem oficial e pré-construída, como pegar um produto pronto da prateleira.

## Passo 5: O Toque Final na Conexão - Resolvendo o Erro 'Connection Refused'

Com o build funcionando, um novo desafio surgiu ao iniciar os contêineres:

```
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
```

Este é um erro clássico de rede no Docker. Dentro de um contêiner, `localhost` se refere ao próprio contêiner, e não a outros serviços na mesma rede Docker. Nossa API estava tentando se conectar a um banco de dados dentro de si mesma, onde não havia nenhum.

A solução é usar o nome do serviço definido no `docker-compose.yml` como o hostname. No nosso caso, o serviço do banco de dados se chama `db`. Garantimos que nosso arquivo `.env` estava configurado corretamente para refletir isso:

```
# .env
...
POSTGRES_HOST=db
...
```

Com essa alteração, a API passou a procurar pelo host `db`, que o Docker Compose resolve corretamente para o endereço IP do contêiner do PostgreSQL, estabelecendo a conexão com sucesso.

## Passo 6: Bônus - Refatorando para um Código Mais Limpo (Princípio DRY)

Com a aplicação totalmente funcional, identificamos uma oportunidade de melhoria no código. Em `routers/alunos.py`, a lógica para buscar um aluno pelo ID e verificar se ele existe estava repetida em três endpoints diferentes.

Para seguir o princípio **DRY (Don't Repeat Yourself - Não se Repita)** e tornar o código mais limpo e fácil de manter, criamos uma função de dependência reutilizável no FastAPI.

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

Essa pequena refatoração centralizou a lógica de busca, limpou os endpoints e tornou o código mais robusto.

## Passo 7: Otimização Avançada - Criando Imagens Enxutas com Multi-Stage Builds

Com a aplicação funcional e refatorada, demos um passo adiante na otimização do nosso ambiente Docker. Nossa imagem final, embora funcional, continha ferramentas de compilação (`build-base`, `postgresql-dev`) que são necessárias apenas durante o *build*, mas não para a *execução* da API. Isso aumenta o tamanho da imagem e sua superfície de ataque.

A solução para isso é uma técnica poderosa chamada **multi-stage builds**.

Reescrevemos nosso `Dockerfile` para usar dois estágios:

1.  **Estágio "Builder"**: Um ambiente temporário onde instalamos todas as dependências pesadas e compilamos nossos pacotes Python.
2.  **Estágio Final**: Uma imagem nova e limpa, para a qual copiamos apenas o código da nossa aplicação e os pacotes já compilados do estágio anterior.

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

O resultado é uma imagem Docker final drasticamente menor, mais segura e mais rápida para ser distribuída, contendo apenas o essencial para a execução da nossa API.

## Passo 8: Implementando Logging Estruturado para Observabilidade

Uma aplicação pronta para produção precisa ser observável. Precisamos de uma maneira de entender o que ela está fazendo, diagnosticar erros e monitorar seu comportamento. É aqui que entra o logging.

Para nossa aplicação em contêiner, a melhor prática é enviar logs para a saída padrão (`stdout`) em um **formato estruturado (JSON)**. Isso permite que ferramentas de agregação de logs (como ELK Stack, Datadog, Grafana Loki) capturem, processem e analisem esses logs facilmente.

### Entendendo os Componentes do Módulo `logging` do Python

Antes de implementar, é crucial entender os quatro pilares do módulo `logging`:

1.  **Loggers (Os Emissores):** Objetos que usamos em nosso código para enviar mensagens (`logger.info(...)`).
2.  **Handlers (Os Destinos):** Decidem para onde as mensagens vão (console, arquivo, rede, etc.).
3.  **Formatters (Os Estilistas):** Definem o formato da mensagem de log (texto simples, JSON, etc.).
4.  **Levels (Os Filtros):** Controlam a severidade das mensagens a serem processadas (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

O fluxo é simples: um **Logger** emite uma mensagem, que é filtrada por seu **Level**. Se passar, ela é enviada para um **Handler**, que usa um **Formatter** para estilizar a mensagem antes de enviá-la ao destino final.

### Analisando a Configuração na Prática

Para entender como essas peças se conectam, vamos analisar nosso próprio arquivo `logging_config.py`:

```python
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {  # <-- 3. FORMATTERS (Os Estilistas)
        "json": { "()": JsonFormatter },
    },
    "handlers": {    # <-- 2. HANDLERS (Os Destinos)
        "console": {
            "class": "logging.StreamHandler", "formatter": "json", "stream": "ext://sys.stdout",
        },
    },
    "root": {        # <-- 1. LOGGER (O Emissor Principal)
        "level": "INFO", "handlers": ["console"], # <-- 4. LEVEL (O Filtro)
    },
}
```

-   **Logger (`root`):** A seção `root` define o comportamento do logger principal. Qualquer logger criado com `logging.getLogger()` herdará essa configuração. A linha `"handlers": ["console"]` conecta o logger ao nosso handler, dizendo: "Envie todas as mensagens processadas para o handler chamado `console`".
-   **Handler (`console`):** Este handler é configurado para enviar os logs para o console (`stdout`). Ele usa o `"formatter": "json"` para estilizar a mensagem, conectando-o ao nosso formatador customizado.
-   **Formatter (`json`):** Aqui, instruímos o Python a usar nossa classe `JsonFormatter` para transformar cada registro de log em uma string JSON.
-   **Level (`INFO`):** Este é o filtro de severidade. O logger `root` só processará mensagens de nível `INFO` ou superior (`WARNING`, `ERROR`, `CRITICAL`), ignorando as de `DEBUG`.

### Implementando o Logging Estruturado

Primeiro, criamos um novo arquivo `logging_config.py` para centralizar nossa configuração:

```python
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/logging_config.py
import logging
from logging.config import dictConfig

class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format."""
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }
        return str(log_record).replace("'", '"')

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": { "json": { "()": JsonFormatter } },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "root": { "level": "INFO", "handlers": ["console"] },
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)
```

Em seguida, integramos essa configuração em nosso `app.py` para que ela seja carregada na inicialização:

```python
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/app.py
...
from logging_config import setup_logging
...
# Setup custom logging
setup_logging()
...
```

Com isso, podemos usar o logger em qualquer lugar da nossa aplicação. Por exemplo, para registrar a criação de um novo aluno em `routers/alunos.py`:

```python
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/routers/alunos.py
import logging

# Get a logger instance for this module
logger = logging.getLogger(__name__)

...

@alunos_router.post("/alunos", response_model=Aluno)
def create_aluno(aluno: Aluno, db: Session = Depends(get_db)):
    ...
    db.commit()
    db.refresh(db_aluno)
    logger.info(f"Student created successfully with ID: {db_aluno.id}")
    return Aluno.from_orm(db_aluno)
```

Agora, todos os logs da aplicação, incluindo os logs de acesso do Uvicorn, serão exibidos no console do Docker em um formato JSON limpo e estruturado, pronto para ser coletado e analisado.

## Passo 9: Bônus - Níveis de Log Dinâmicos para Desenvolvimento e Produção

Uma prática essencial é ter níveis de log diferentes para cada ambiente. Em desenvolvimento, queremos o máximo de detalhes (`DEBUG`), mas em produção, queremos menos ruído e logs mais concisos (`INFO` ou `WARNING`) para reduzir custos e facilitar a identificação de problemas reais.

Conseguimos isso tornando nossa configuração de logging dinâmica, lendo o nível de log de uma variável de ambiente.

Alteramos o `logging_config.py` para ler a variável `LOG_LEVEL`:

```python
# /home/agnus/Documents/Pessoal/Alura/devOps/imersao-devops/logging_config.py
import os
...
# Read log level from environment variable, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
...
LOGGING_CONFIG = {
    ...
    "root": { "level": log_level, "handlers": ["console"] },
}
```

Agora, para desenvolvimento, simplesmente adicionamos `LOG_LEVEL=DEBUG` ao nosso arquivo `.env`. Para produção, podemos omitir a variável (usando o padrão `INFO`) ou configurá-la para `INFO` ou `WARNING`, nos dando controle total sobre a verbosidade dos logs em cada ambiente.

## Conclusão

A migração foi um sucesso! Passamos de uma configuração simples com SQLite para um ambiente de desenvolvimento robusto, containerizado e muito mais próximo de um ambiente de produção real.

A jornada nos ensinou sobre:
- Drivers de banco de dados em Python.
- Gerenciamento seguro de credenciais com variáveis de ambiente.
- Orquestração de múltiplos serviços com Docker Compose.
- A importância dos `healthchecks` para a inicialização de serviços dependentes.
- Como resolver problemas de compilação de pacotes em imagens Docker minimalistas como a Alpine.
- Como a rede do Docker funciona e por que `localhost` não funciona entre contêineres.
- Como refatorar código FastAPI usando dependências para evitar repetição (DRY).
- Como otimizar o tamanho e a segurança das imagens Docker com a técnica de multi-stage builds.
- A importância da observabilidade e como implementar logging estruturado (JSON) para ambientes de produção.
- Como configurar níveis de log dinâmicos para diferentes ambientes usando variáveis de ambiente.

Com essa nova estrutura, o projeto está pronto para crescer com uma base de dados sólida e um ambiente de desenvolvimento confiável.
