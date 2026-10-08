import os

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_events as events,
)
from aws_cdk import (
    aws_events_targets as targets,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_s3_notifications as s3_notifications,
)
from constructs import Construct


class IngestionStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.raw_bucket = s3.Bucket(
            self,
            "RawBucket",
            bucket_name="annual-report-bucket",  # Remplacez par un nom unique
            removal_policy=RemovalPolicy.DESTROY,  # Supprime le bucket lors de la destruction du stack
            auto_delete_objects=True,  # Supprime les objets lors de la destruction du bucket*
        )

        self.excel_bucket = s3.Bucket(
            self,
            "ExcelBucket",
            bucket_name="excel-bucket",  # Remplacez par un nom unique
            removal_policy=RemovalPolicy.DESTROY,  # Supprime le bucket lors de la destruction du stack
            auto_delete_objects=True,  # Supprime les objets lors de la destruction du bucket*
        )

        # The first Lambda queries SEC and writes the resulting Excel exports.
        self.ingestion_excel_lambda = _lambda.DockerImageFunction(
            self,
            "IngestionHandler",
            code=_lambda.DockerImageCode.from_image_asset("function/ingestion_excel"),
            environment={
                "EXCEL_BUCKET_NAME": self.excel_bucket.bucket_name,
                "FILING_DATE_FROM": os.getenv("FILING_DATE_FROM", "2020-01-01"),
                "SEC_USER_AGENT": os.getenv(
                    "SEC_USER_AGENT",
                    "annual-report-rag/0.1.0 (SEC filings ingestion)",
                ),
            },
            timeout=Duration.minutes(15),
            memory_size=2048,
        )
        self.excel_bucket.grant_put(self.ingestion_excel_lambda)

        # The second Lambda is triggered for each export and ingests its filings.
        self.ingestion_doc_lambda = _lambda.DockerImageFunction(
            self,
            "IngestionHandler2",
            code=_lambda.DockerImageCode.from_image_asset("function/ingestion_doc"),
            environment={
                "RAW_BUCKET_NAME": self.raw_bucket.bucket_name,
                "SEC_USER_AGENT": os.getenv(
                    "SEC_USER_AGENT",
                    "annual-report-rag/0.1.0 (SEC filings ingestion)",
                ),
            },
            timeout=Duration.minutes(15),
            memory_size=1024,
        )
        self.excel_bucket.grant_read(self.ingestion_doc_lambda)
        self.raw_bucket.grant_put(self.ingestion_doc_lambda)
        self.excel_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(self.ingestion_doc_lambda),
            s3.NotificationKeyFilter(prefix="sec_filings/", suffix=".xlsx"),
        )

        # The scheduled invocation uses the same payload shape as manual invocations.
        rule = events.Rule(
            self,
            "IngestionScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(2)),
        )
        rule.add_target(
            targets.LambdaFunction(
                self.ingestion_excel_lambda,
                event=events.RuleTargetInput.from_object(
                    {"companies": {"Amazon": "1018724"}}
                ),
            )
        )