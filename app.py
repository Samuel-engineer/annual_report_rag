import aws_cdk as cdk

from config import get_environment_account
from stacks.ingestion_stack import IngestionStack
from stacks.knowledge_base_stack import KnowledgeBaseStack
from stacks.opensearch_stack import OpenSearchStack
from stacks.orchestration_stack import OrchestrationStack

env = cdk.Environment(**get_environment_account())

app = cdk.App()

aoss_stack = OpenSearchStack(app, "OpenSearchStack", env=env)
ingestion_stack = IngestionStack(app, "IngestionStack", env=env)

knowledge_base_stack = KnowledgeBaseStack(
    app,
    "KnowledgeBaseStack",
    collection=aoss_stack.collection,
    bucket=ingestion_stack.raw_bucket,
    env=env,
)

OrchestrationStack(
    app,
    "OrchestrationStack",
    ingestion_json_lambda=ingestion_stack.ingestion_json_lambda,
    ingestion_doc_lambda=ingestion_stack.ingestion_doc_lambda,
    knowledge_base=knowledge_base_stack.knowledge_base,
    data_source=knowledge_base_stack.data_source,
    env=env,
)

app.synth()
