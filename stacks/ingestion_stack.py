from aws_cdk import (
    Duration,
    RemovalPolicy,
    Size,
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
    aws_logs as logs,
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

        log_group = logs.LogGroup(
            self,
            "IngestionLogGroup",
            log_group_name="/aws/lambda/ingestion-log-group",
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.raw_bucket = s3.Bucket(
            self,
            "RawBucket",
            bucket_name=f"annual-report-bucket-{self.account}-{self.region}",  # Remplacez par un nom unique
            removal_policy=RemovalPolicy.DESTROY,  # Supprime le bucket lors de la destruction du stack
            auto_delete_objects=True,  # Supprime les objets lors de la destruction du bucket*
        )

        self.excel_bucket = s3.Bucket(
            self,
            "ExcelBucket",
            bucket_name=f"excel-bucket-{self.account}-{self.region}",  # Remplacez par un nom unique
            removal_policy=RemovalPolicy.DESTROY,  # Supprime le bucket lors de la destruction du stack
            auto_delete_objects=True,  # Supprime les objets lors de la destruction du bucket*
        )

        # The first Lambda saves SEC submissions JSON files to S3.
        self.ingestion_json_lambda = _lambda.Function(
            self,
            "IngestionHandler1",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ingestion_json.main.lambda_handler",
            code=_lambda.Code.from_asset("function/"),
            environment={
                "EXCEL_BUCKET_NAME": self.excel_bucket.bucket_name,
            },
            timeout=Duration.minutes(15),
            ephemeral_storage_size=Size.mebibytes(1028),
            memory_size=2048,
            log_group=log_group,
        )
        self.excel_bucket.grant_put(self.ingestion_json_lambda)

        # The second Lambda downloads supported filings from submissions JSON.
        self.ingestion_doc_lambda = _lambda.Function(
            self,
            "IngestionHandler2",
            code=_lambda.Code.from_asset("function/"),
            handler="ingestion_doc.main.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            environment={
                "RAW_BUCKET_NAME": self.raw_bucket.bucket_name,
            },
            timeout=Duration.minutes(15),
            ephemeral_storage_size=Size.mebibytes(1028),
            memory_size=1024,
            log_group=log_group,
            reserved_concurrent_executions=1,
        )
        self.excel_bucket.grant_read(self.ingestion_doc_lambda)
        self.raw_bucket.grant_put(self.ingestion_doc_lambda)
        self.excel_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(self.ingestion_doc_lambda),
            s3.NotificationKeyFilter(suffix=".json"),
        )

        # The scheduled invocation uses the same payload shape as manual invocations.
        rule = events.Rule(
            self,
            "IngestionScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(2)),
        )
        rule.add_target(
            targets.LambdaFunction(
                self.ingestion_json_lambda,
                event=events.RuleTargetInput.from_object(
                    {"enterprises": {"Amazon": "1018724"}}
                ),
            )
        )
