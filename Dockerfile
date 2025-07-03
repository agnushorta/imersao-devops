# Palavras Chaves: MARVEL ELLIS YAML
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
# O argumento --no-cache-dir evita o armazenamento de cache para reduzir o tamanho da imagem
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação para o diretório de trabalho
COPY . .

# Expõe a porta 8000 para que a aplicação possa ser acessada
EXPOSE 8000

# Define o comando a ser executado quando o container for iniciado
# Usa uvicorn para servir a aplicação FastAPI
# O argumento app:app especifica o módulo e o objeto da aplicação
# O argumento --host 0.0.0.0 permite que a aplicação seja acessada de fora do container
# O argumento --port 8000 define a porta em que a aplicação será executada
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
