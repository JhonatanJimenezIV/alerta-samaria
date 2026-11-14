# Imagen base: Python 3.11 slim (mismo runtime que las Lambdas)
FROM python:3.11-slim

# Node.js, npm, curl y git (necesarios para AWS CDK)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# AWS CDK y cdklocal (redirige el despliegue al emulador en :4566)
RUN npm install -g aws-cdk aws-cdk-local

WORKDIR /app

# Dependencias Python (se copian antes que el código para aprovechar la caché de capas)
COPY app/requirements.txt .
COPY app/layers/dependencias/requirements.txt layers/dependencias/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Credenciales dummy: el emulador acepta cualquier valor
ENV AWS_ACCESS_KEY_ID=test
ENV AWS_SECRET_ACCESS_KEY=test
ENV AWS_DEFAULT_REGION=us-east-1

CMD ["bash"]
