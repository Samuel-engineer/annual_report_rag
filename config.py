import os

from dotenv import load_dotenv

load_dotenv()

account = os.getenv("DEFAULT_AWS_ACCOUNT_ID")
region = os.getenv("DEFAULT_AWS_REGION")


def get_environment_account():
    return {"account": account, "region": region}
