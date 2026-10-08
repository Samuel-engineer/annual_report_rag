FROM public.ecr.aws/lambda/python:3.13

RUN pip install --no-cache-dir boto3 openpyxl

COPY . ${LAMBDA_TASK_ROOT}/ingestion_doc/

CMD ["ingestion_doc.main.lambda_handler"]