import hashlib
import logging
import os
from typing import Any, cast

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_client = cast(Any, boto3.client("bedrock-agent"))


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, str]:
    knowledge_base_id = os.environ["KNOWLEDGE_BASE_ID"]
    data_source_id = os.environ["DATA_SOURCE_ID"]
    operation = event.get("operation")

    if operation == "start":
        request: dict[str, str] = {
            "knowledgeBaseId": knowledge_base_id,
            "dataSourceId": data_source_id,
        }
        execution_id = event.get("executionId")
        if execution_id is not None:
            if not isinstance(execution_id, str) or not execution_id:
                raise ValueError("executionId must be a non-empty string.")
            request["clientToken"] = hashlib.sha256(execution_id.encode()).hexdigest()
        response = bedrock_client.start_ingestion_job(**request)
        job = response.get("ingestionJob")
        job_id = job.get("ingestionJobId") if isinstance(job, dict) else None
        if not isinstance(job_id, str) or not job_id:
            raise RuntimeError("Bedrock did not return an ingestion job ID.")
        logger.info("Started Bedrock ingestion job %s", job_id)
        return {"jobId": job_id}

    if operation == "status":
        job_id = event.get("jobId")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("jobId must be provided to check ingestion status.")
        response = bedrock_client.get_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            ingestionJobId=job_id,
        )
        job = response.get("ingestionJob")
        status = job.get("status") if isinstance(job, dict) else None
        if not isinstance(status, str) or not status:
            raise RuntimeError(
                f"Bedrock returned no status for ingestion job {job_id}."
            )
        logger.info("Bedrock ingestion job %s is %s", job_id, status)
        return {"jobId": job_id, "status": status}

    raise ValueError("operation must be either 'start' or 'status'.")
