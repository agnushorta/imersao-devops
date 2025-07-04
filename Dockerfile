# Palavras Chaves: MARVEL ELLIS YAML

# --- Estágio 1: O Construtor (Builder) ---
# Usamos uma imagem base para compilar as dependências.
# Damos a este estágio um nome "builder" para referenciá-lo mais tarde.
FROM python:3.11-alpine AS builder

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala as dependências do sistema (para Alpine) necessárias para compilar o psycopg2
# postgresql-dev: Contém os arquivos de desenvolvimento do PostgreSQL (incluindo pg_config)
# build-base: Contém o compilador C (gcc) e outras ferramentas de build
RUN apk add --no-cache postgresql-dev build-base

# Copia o arquivo de requirements e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- Estágio 2: A Imagem Final ---
# Começamos do zero com uma imagem limpa e leve.
FROM python:3.11-alpine

# Define o diretório de trabalho
WORKDIR /app

# Instala APENAS as dependências de tempo de execução (runtime) do psycopg2.
# Não precisamos mais do compilador ou dos arquivos de desenvolvimento (-dev).
RUN apk add --no-cache libpq

# Copia as dependências Python instaladas do estágio "builder" para a imagem final.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia todo o código da aplicação para o diretório de trabalho
COPY . .

# Expõe a porta 8000 para que a aplicação possa ser acessada
EXPOSE 8000

# Define o comando para executar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
