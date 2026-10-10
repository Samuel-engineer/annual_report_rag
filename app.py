import aws_cdk as cdk

from config import get_environment_account
from stacks.ingestion_stack import IngestionStack
from stacks.knowledge_base_stack import KnowledgeBaseStack
from stacks.opensearch_stack import OpenSearchStack

env = cdk.Environment(**get_environment_account())

app = cdk.App()

aoss_stack = OpenSearchStack(app, "OpenSearchStack", env=env)
ingestion_stack = IngestionStack(app, "IngestionStack", env=env)

KnowledgeBaseStack(
    app,
    "KnowledgeBaseStack",
    collection=aoss_stack.collection,
    bucket=ingestion_stack.excel_bucket,
    env=env,
)

app.synth()
