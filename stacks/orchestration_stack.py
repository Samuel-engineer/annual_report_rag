from aws_cdk import Duration, Stack, TimeZone
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_scheduler as scheduler
from aws_cdk import aws_scheduler_targets as scheduler_targets
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct


class OrchestrationStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        ingestion_json_lambda: _lambda.Function,
        ingestion_doc_lambda: _lambda.Function,
        knowledge_base: bedrock.CfnKnowledgeBase,
        data_source: bedrock.CfnDataSource,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        knowledge_base_id = knowledge_base.attr_knowledge_base_id
        data_source_id = data_source.attr_data_source_id
        self.sync_lambda = _lambda.Function(
            self,
            "KnowledgeBaseSyncHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="knowledge_base_sync.main.lambda_handler",
            code=_lambda.Code.from_asset("function/"),
            environment={
                "KNOWLEDGE_BASE_ID": knowledge_base_id,
                "DATA_SOURCE_ID": data_source_id,
            },
            timeout=Duration.minutes(1),
            memory_size=256,
        )
        self.sync_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:StartIngestionJob",
                    "bedrock:GetIngestionJob",
                ],
                resources=[knowledge_base.attr_knowledge_base_arn],
            )
        )

        retry_lambda_errors = [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException",
        ]

        run_ingestion_json = tasks.LambdaInvoke(
            self,
            "RunIngestionJson",
            lambda_function=ingestion_json_lambda,
            payload=sfn.TaskInput.from_object(
                {"enterprises": sfn.JsonPath.object_at("$.enterprises")}
            ),
            result_path="$.ingestionResult",
        )

        run_ingestion_doc_after_json = tasks.LambdaInvoke(
            self,
            "RunIngestionDocAfterJson",
            lambda_function=ingestion_doc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "submissions": sfn.JsonPath.list_at(
                        "$.ingestionResult.Payload.submissions"
                    )
                }
            ),
            result_path="$.documentResult",
        )

        run_ingestion_doc_manually = tasks.LambdaInvoke(
            self,
            "RunIngestionDocManually",
            lambda_function=ingestion_doc_lambda,
            payload=sfn.TaskInput.from_object(
                {"submissions": sfn.JsonPath.list_at("$.submissions")}
            ),
            result_path="$.documentResult",
        )
        for task in (
            run_ingestion_json,
            run_ingestion_doc_after_json,
            run_ingestion_doc_manually,
        ):
            task.add_retry(
                errors=retry_lambda_errors,
                interval=Duration.seconds(2),
                max_attempts=3,
                backoff_rate=2,
            )

        start_sync = tasks.LambdaInvoke(
            self,
            "StartKnowledgeBaseSync",
            lambda_function=self.sync_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "operation": "start",
                    "executionId": sfn.JsonPath.execution_id,
                }
            ),
            result_path="$.syncStart",
        )
        start_sync.add_retry(
            errors=retry_lambda_errors,
            interval=Duration.seconds(2),
            max_attempts=3,
            backoff_rate=2,
        )

        check_sync = tasks.LambdaInvoke(
            self,
            "CheckKnowledgeBaseSync",
            lambda_function=self.sync_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "operation": "status",
                    "jobId": sfn.JsonPath.string_at("$.syncStart.Payload.jobId"),
                }
            ),
            result_path="$.syncStatus",
        )
        check_sync.add_retry(
            errors=retry_lambda_errors,
            interval=Duration.seconds(2),
            max_attempts=3,
            backoff_rate=2,
        )
        wait_before_sync_check = sfn.Wait(
            self,
            "WaitForSyncStatus",
            time=sfn.WaitTime.duration(Duration.seconds(60)),
        )
        sync_succeeded = sfn.Succeed(self, "KnowledgeBaseSyncSucceeded")
        sync_failed = sfn.Fail(
            self,
            "KnowledgeBaseSyncFailed",
            cause="The Bedrock knowledge base ingestion job did not complete.",
        )

        status_choice = sfn.Choice(self, "EvaluateKnowledgeBaseSyncStatus")
        status_choice.when(
            sfn.Condition.string_equals("$.syncStatus.Payload.status", "COMPLETE"),
            sync_succeeded,
        )
        status_choice.when(
            sfn.Condition.string_equals("$.syncStatus.Payload.status", "FAILED"),
            sync_failed,
        )
        status_choice.when(
            sfn.Condition.string_equals("$.syncStatus.Payload.status", "STOPPED"),
            sync_failed,
        )

        status_choice.otherwise(wait_before_sync_check)
        check_sync.next(status_choice)
        wait_before_sync_check.next(check_sync)
        start_sync.next(wait_before_sync_check)

        mode_choice = sfn.Choice(self, "SelectIngestionWorkflow")
        mode_choice.when(
            sfn.Condition.string_equals("$.mode", "full"),
            run_ingestion_json,
        )
        mode_choice.when(
            sfn.Condition.string_equals("$.mode", "documents_sync"),
            run_ingestion_doc_manually,
        )
        mode_choice.when(
            sfn.Condition.string_equals("$.mode", "sync_only"),
            start_sync,
        )
        mode_choice.otherwise(
            sfn.Fail(
                self,
                "InvalidWorkflowMode",
                cause="mode must be full, documents_sync, or sync_only.",
            )
        )
        run_ingestion_json.next(run_ingestion_doc_after_json)
        run_ingestion_doc_after_json.next(start_sync)
        run_ingestion_doc_manually.next(start_sync)

        self.state_machine = sfn.StateMachine(
            self,
            "AnnualReportWorkflow",
            state_machine_name="annual-report-ingestion",
            definition_body=sfn.DefinitionBody.from_chainable(mode_choice),
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=Duration.days(1),
        )

        scheduler.Schedule(
            self,
            "AnnualIngestionSchedule",
            schedule=scheduler.ScheduleExpression.cron(
                minute="0",
                hour="0",
                day="6",
                month="1",
                year="*",
                time_zone=TimeZone.EUROPE_PARIS,
            ),
            target=scheduler_targets.StepFunctionsStartExecution(
                self.state_machine,
                input=scheduler.ScheduleTargetInput.from_object(
                    {
                        "mode": "full",
                        "enterprises": {"Amazon": "1018724"},
                    }
                ),
            ),
            description="Run the annual SEC ingestion on January 6 at midnight Paris time.",
            enabled=True,
        )
