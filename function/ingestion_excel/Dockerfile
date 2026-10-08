FROM public.ecr.aws/lambda/python:3.12

# Fixe le chemin des navigateurs hors de /root
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Dépendances système C/C++ strictement nécessaires au démarrage de Chromium
RUN dnf install -y \
    atk \
    gtk3 \
    libX11 \
    libXcomposite \
    libXdamage \
    libXext \
    libXfixes \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    libdrm \
    libxkbcommon \
    mesa-libgbm \
    nss \
    pango \
    && dnf clean all

# Installation de Playwright et téléchargement de Chromium
RUN pip install --no-cache-dir boto3 "playwright==1.55.0" \
    && python -m playwright install chromium \
    && chmod -R a+rX /ms-playwright

# Copie du code applicatif
COPY . ${LAMBDA_TASK_ROOT}\ingestion_excel

# Point d'entrée
CMD ["ingestion_excel.main.lambda_handler"]