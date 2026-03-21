# Dockerfile para deploy no GCP Cloud Run
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema (MySQL + Playwright + imagens)
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libmariadb-dev \
    libmariadb-dev-compat \
    # Imagens (Pillow)
    libjpeg-dev \
    zlib1g-dev \
    # Dependências do Chromium/Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libwayland-client0 \
    fonts-noto-color-emoji \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Instalar Chromium para Playwright
RUN playwright install --with-deps chromium

# Copiar código do projeto
COPY . .


# Expor porta
EXPOSE 8080

# Comando de execução
CMD ["gunicorn", "vendaslinkstopsml.wsgi:application", "--bind", "0.0.0.0:8080"]
