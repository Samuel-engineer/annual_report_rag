import json

from aws_cdk import (
    Stack,
)
from aws_cdk import (
    aws_opensearchserverless as oss,
)
from constructs import Construct

from .config import Settings


class OpenSearchStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        collection_name = "report-rag-col"
        index_name = "report-rag-col-index"
        cfg = Settings

        # 1. Encryption policy
        self.encryption_policy = oss.CfnSecurityPolicy(
            self,
            "AossEncryptionPolicy",
            name=f"{collection_name}-enc",
            type="encryption",
            policy=json.dumps(
                {
                    "Rules": [
                        {
                            "Resource": [f"collection/{collection_name}"],
                            "ResourceType": "collection",
                        }
                    ],
                    "AWSOwnedKey": True,
                }
            ),
        )

        # 2. Network policy
        self.network_policy = oss.CfnSecurityPolicy(
            self,
            "AossNetworkPolicy",
            name=f"{collection_name}-net",
            type="network",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "Resource": [f"collection/{collection_name}"],
                                "ResourceType": "collection",
                            },
                            {
                                "Resource": [f"collection/{collection_name}"],
                                "ResourceType": "dashboard",
                            },
                        ],
                        "AllowFromPublic": True,
                    }
                ]
            ),
        )

        # 3. Collection
        self.collection = oss.CfnCollection(
            self,
            "AossCollection",
            name=collection_name,
            type="VECTORSEARCH",
            description="Vector collection for Bedrock Knowledge Base",
        )

        self.collection.add_resource_dependency(self.encryption_policy)
        self.collection.add_resource_dependency(self.network_policy)

        # 4. Data access policy: requise pour que CloudFormation puisse créer l'index
        self.index_data_access_policy = oss.CfnAccessPolicy(
            self,
            "AossIndexCreationAccessPolicy",
            name=f"{collection_name}-deploy-access",
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
                                ],
                            },
                            {
                                "ResourceType": "index",
                                "Resource": [f"index/{collection_name}/*"],
                                "Permission": [
                                    "aoss:CreateIndex",
                                    "aoss:DescribeIndex",
                                    "aoss:UpdateIndex",
                                ],
                            },
                        ],
                        # Root du compte: couvre le rôle/l'utilisateur qui exécute le déploiement CDK
                        "Principal": [f"arn:aws:iam::{self.account}:root"],
                    }
                ]
            ),
        )
        self.index_data_access_policy.add_resource_dependency(self.collection)

        self.index = oss.CfnIndex(
            self,
            "AossVectorIndex",
            collection_endpoint=self.collection.attr_collection_endpoint,
            index_name=index_name,
            settings=oss.CfnIndex.IndexSettingsProperty(
                index=oss.CfnIndex.IndexProperty(
                    knn=True, knn_algo_param_ef_search=100
                ),
                analysis=oss.CfnIndex.AnalysisProperty(
                    analyzer={
                        "analyser_key": oss.CfnIndex.AnalyzerItemsProperty(
                            char_filter=["html_strip"],
                            filter=["lowercase", "asciifolding"],
                            tokenizer="standard",
                            type="custom",
                        )
                    }
                ),
            ),
            mappings=oss.CfnIndex.MappingsProperty(
                properties={
                    "vector": oss.CfnIndex.PropertyMappingProperty(
                        type="knn_vector",
                        dimension=cfg.embedding_dimension,
                        method=oss.CfnIndex.MethodProperty(
                            name="hnsw",
                            engine="faiss",
                            space_type="cosinesimil",
                        ),
                    ),
                    "text": oss.CfnIndex.PropertyMappingProperty(
                        type="text", analyzer="analyser_key"
                    ),
                    "metadata": oss.CfnIndex.PropertyMappingProperty(
                        type="text",
                        index=False,
                    ),
                }
            ),
        )

        # Collection must exist before index
        self.index.add_resource_dependency(self.collection)
        self.index.add_resource_dependency(self.index_data_access_policy)
