"""I/O utilities for S3, DynamoDB, and other AWS services."""

import json
import orjson
from typing import Any, Dict, Optional, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from libs.common.config import get_config
from libs.common.logging import get_logger

logger = get_logger(__name__)


class S3Client:
    """Wrapper for S3 operations."""

    def __init__(self) -> None:
        self.config = get_config()
        self.client = boto3.client("s3", region_name=self.config.aws_region)

    def read_json(self, bucket: str, key: str) -> Dict[str, Any]:
        """Read JSON object from S3."""
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read()
            return orjson.loads(content)
        except ClientError as e:
            logger.error(f"Failed to read s3://{bucket}/{key}: {e}")
            raise

    def write_json(
        self,
        data: Dict[str, Any],
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Write JSON object to S3."""
        try:
            content = orjson.dumps(data, option=orjson.OPT_INDENT_2)
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                ContentType="application/json",
                **extra_args,
            )
            uri = f"s3://{bucket}/{key}"
            logger.info(f"Wrote JSON to {uri}")
            return uri
        except ClientError as e:
            logger.error(f"Failed to write to s3://{bucket}/{key}: {e}")
            raise

    def read_text(self, bucket: str, key: str) -> str:
        """Read text file from S3."""
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except ClientError as e:
            logger.error(f"Failed to read s3://{bucket}/{key}: {e}")
            raise

    def write_text(
        self,
        content: str,
        bucket: str,
        key: str,
        content_type: str = "text/plain",
    ) -> str:
        """Write text content to S3."""
        try:
            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType=content_type,
            )
            uri = f"s3://{bucket}/{key}"
            logger.info(f"Wrote text to {uri}")
            return uri
        except ClientError as e:
            logger.error(f"Failed to write to s3://{bucket}/{key}: {e}")
            raise

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> List[str]:
        """List objects in S3 bucket with prefix."""
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            logger.error(f"Failed to list s3://{bucket}/{prefix}: {e}")
            raise

    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Failed to check s3://{bucket}/{key}: {e}")
            raise


class DynamoDBClient:
    """Wrapper for DynamoDB operations."""

    def __init__(self) -> None:
        self.config = get_config()
        self.dynamodb = boto3.resource("dynamodb", region_name=self.config.aws_region)

    def get_item(
        self,
        table_name: str,
        key: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get item from DynamoDB table."""
        try:
            table = self.dynamodb.Table(table_name)
            response = table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get item from {table_name}: {e}")
            raise

    def put_item(
        self,
        table_name: str,
        item: Dict[str, Any],
    ) -> None:
        """Put item into DynamoDB table."""
        try:
            table = self.dynamodb.Table(table_name)
            # Convert datetime objects to ISO strings
            item = self._serialize_item(item)
            table.put_item(Item=item)
            logger.debug(f"Put item into {table_name}")
        except ClientError as e:
            logger.error(f"Failed to put item into {table_name}: {e}")
            raise

    def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update item in DynamoDB table."""
        try:
            table = self.dynamodb.Table(table_name)

            # Build update expression
            update_expr_parts = []
            expr_attr_values = {}
            expr_attr_names = {}

            for i, (field, value) in enumerate(updates.items()):
                placeholder_name = f"#field{i}"
                placeholder_value = f":val{i}"
                update_expr_parts.append(f"{placeholder_name} = {placeholder_value}")
                expr_attr_names[placeholder_name] = field
                expr_attr_values[placeholder_value] = value

            update_expression = "SET " + ", ".join(update_expr_parts)

            response = table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes", {})
        except ClientError as e:
            logger.error(f"Failed to update item in {table_name}: {e}")
            raise

    def query(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        index_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query DynamoDB table."""
        try:
            table = self.dynamodb.Table(table_name)
            kwargs = {
                "KeyConditionExpression": key_condition_expression,
                "ExpressionAttributeValues": expression_attribute_values,
                "Limit": limit,
            }
            if index_name:
                kwargs["IndexName"] = index_name

            response = table.query(**kwargs)
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to query {table_name}: {e}")
            raise

    @staticmethod
    def _serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize datetime objects in item."""
        serialized = {}
        for key, value in item.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = DynamoDBClient._serialize_item(value)
            elif isinstance(value, list):
                serialized[key] = [
                    DynamoDBClient._serialize_item(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                serialized[key] = value
        return serialized
