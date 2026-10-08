import aws_cdk as cdk
from stacks.ingestion_stack import IngestionStack
from stacks.frontend_stack import FrontendStack
from stacks.rag_stack import RagStack

from config import get_environment_account

env = cdk.Environment(**get_environment_account())

app = cdk.App()

IngestionStack(app, "IngestionStack", env=env)

app.synth()