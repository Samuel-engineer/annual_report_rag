import json

from aws_cdk import (
    Stack,
)
from aws_cdk import (
    aws_bedrock as bedrock,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_opensearchserverless as oss,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct

from .config import Settings


class KnowledgeBaseStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        collection: oss.CfnCollection,
        bucket: s3.Bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        collection_name = collection.name
        collection_arn = collection.attr_arn
        cfg = Settings()

        # 2. Rôle IAM de service Bedrock Knowledge Base
        self.kb_role = iam.Role(
            self,
            "BedrockKBExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        # Permissions S3
        bucket.grant_read(self.kb_role)

        # Permissions d'invocation du modèle Titan Embeddings V2
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:*::foundation-model/{cfg.embedding_model_id}",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/us.{cfg.embedding_model_id}",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/global.{cfg.embedding_model_id}",
                ],
            )
        )

        # Permissions IAM OpenSearch Serverless
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["aoss:APIAccessAll"], resources=[collection_arn]
            )
        )

        # 3. Data Access Policy OpenSearch Serverless
        data_access_policy = oss.CfnAccessPolicy(
            self,
            "KbAossAccessPolicy",
            name=f"{collection_name}-kb-access",
            type="data",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "ResourceType": "collection",
                                "Resource": [f"collection/{collection_name}"],
                                "Permission": [
                                    "aoss:CreateCollectionItems",
                                    "aoss:DescribeCollectionItems",
                                    "aoss:UpdateCollectionItems",
                                ],
                            },
                            {
                                "ResourceType": "index",
                                # Format attendu: index/<collection>/<index-ou-wildcard>
                                "Resource": [f"index/{collection_name}/*"],
                                "Permission": [
                                    "aoss:CreateIndex",
                                    "aoss:DescribeIndex",
                                    "aoss:ReadDocument",
                                    "aoss:WriteDocument",
                                ],
                            },
                        ],
                        "Principal": [self.kb_role.role_arn],
                    }
                ]
            ),
        )

        # 4. Knowledge Base Bedrock
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "EnterpriseReportKnowledgeBase",
            name="report-rag-kb",
            role_arn=self.kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/{cfg.embedding_model_id}"
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=collection_arn,
                    vector_index_name=f"{collection_name}-index",
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        vector_field="vector",
                        text_field="text",
                        metadata_field="metadata",
                    ),
                ),
            ),
        )

        # La KB attend à la fois la ressource et la politique
        self.knowledge_base.add_resource_dependency(data_access_policy)
        # Utilise try_find_child pour éviter un crash si l'ID interne change ou n'est pas encore instancié
        default_policy = self.kb_role.node.try_find_child("DefaultPolicy")
        if default_policy:
            self.knowledge_base.node.add_dependency(default_policy)

        # 5. Source de données rattachée au bucket S3
        self.data_source = bedrock.CfnDataSource(
            self,
            "S3DataSource",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
            name="report-s3-datasource",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=bucket.bucket_arn
                ),
            ),
        )
