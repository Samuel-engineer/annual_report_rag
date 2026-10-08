import aws_cdk as cdk

from config import get_environment_account
from stacks.ingestion_stack import IngestionStack

env = cdk.Environment(**get_environment_account())

app = cdk.App()

IngestionStack(app, "IngestionStack", env=env)

app.synth()
