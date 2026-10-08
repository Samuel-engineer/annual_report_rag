FROM public.ecr.aws/lambda/python:3.12

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN dnf install -y \
    alsa-lib \
    atk \
    cups-libs \
    gtk3 \
    libX11 \
    libXcomposite \
    libXcursor \
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

RUN pip install --no-cache-dir boto3 "playwright==1.55.0" \
    && python -m playwright install chromium \
    && chmod -R a+rX /ms-playwright

COPY . ${LAMBDA_TASK_ROOT}/ingestion_excel/

CMD ["ingestion_excel.main.lambda_handler"]