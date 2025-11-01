"""Data Cataloguer Agent - discover and maintain data catalog."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json
import re

from libs.common.types import GraphState, RunStatus, DataLineage
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class DataCataloguer:
    """
    Data Cataloguer Agent.

    Responsibilities:
    - Discover data in S3 buckets
    - Maintain AWS Glue catalog with up-to-date metadata
    - Generate schema cards for each table
    - Track data lineage
    - Detect PII automatically
    - Create searchable index in OpenSearch
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # PII patterns for detection
        self.pii_patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"\+?[\d\s\-\(\)]{10,}",
            "postcode": r"[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}",
            "account_number": r"ACC\d{8,12}",
            "mpan": r"\d{13}",  # Meter Point Administration Number
        }

    @trace_agent("data-cataloguer")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Execute data cataloguing.

        Args:
            state: Current graph state

        Returns:
            Outputs from cataloguing
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="data-cataloguer",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting data cataloguer", task_id=state.task_id)

        try:
            operation = state.inputs.get("operation", "discover")

            if operation == "discover":
                outputs = await self._discover_datasets(state)
            elif operation == "update_catalog":
                outputs = await self._update_catalog(state)
            elif operation == "generate_schema_card":
                outputs = await self._generate_schema_card(state)
            elif operation == "track_lineage":
                outputs = await self._track_lineage(state)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Track costs
            cost_gbp = 0.5  # Glue crawler costs
            self.cost_tracker.record_cost(
                agent_name="data-cataloguer",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="glue.crawler",
                metadata={"operation": operation, "run_id": run_id},
            )

            logger.info(
                "Data cataloguer completed",
                task_id=state.task_id,
                operation=operation,
            )

            return outputs

        except Exception as e:
            logger.error(f"Data cataloguer failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "data-cataloguer",
            }

    async def _discover_datasets(self, state: GraphState) -> Dict[str, Any]:
        """Discover datasets in S3."""
        bucket = state.inputs.get("bucket", f"aurora-data-{self.config.environment}")
        prefix = state.inputs.get("prefix", "")

        logger.info("Discovering datasets", bucket=bucket, prefix=prefix)

        # In production: use boto3 to list S3 objects
        # and AWS Glue crawlers to discover schema

        # Simulate discovery
        discovered_tables = [
            {
                "database": "bronze",
                "table": "customers_raw",
                "location": f"s3://{bucket}/bronze/customers/",
                "format": "parquet",
                "partitions": ["ds"],
                "schema": [
                    {"name": "customer_id", "type": "string"},
                    {"name": "email", "type": "string", "pii": True},
                    {"name": "signup_date", "type": "date"},
                    {"name": "ds", "type": "string"},
                ],
            },
            {
                "database": "silver",
                "table": "customers_cleansed",
                "location": f"s3://{bucket}/silver/customers/",
                "format": "parquet",
                "partitions": ["ds"],
                "schema": [
                    {"name": "customer_id", "type": "string"},
                    {"name": "email_hash", "type": "string"},
                    {"name": "signup_date", "type": "date"},
                    {"name": "ds", "type": "string"},
                ],
            },
        ]

        # Detect PII in schemas
        for table in discovered_tables:
            for column in table["schema"]:
                if self._is_pii_field(column["name"], column["type"]):
                    column["pii"] = True

        logger.info("Datasets discovered", num_tables=len(discovered_tables))

        return {
            "status": "success",
            "discovered_tables": discovered_tables,
            "catalog_coverage": 0.98,
        }

    async def _update_catalog(self, state: GraphState) -> Dict[str, Any]:
        """Update Glue catalog with metadata."""
        tables = state.inputs.get("tables", [])

        logger.info("Updating catalog", num_tables=len(tables))

        # In production: use boto3 glue client
        # glue.update_table() or glue.create_table()

        updated_tables = []
        for table in tables:
            # Simulate Glue update
            glue_table = {
                "DatabaseName": table["database"],
                "Name": table["table"],
                "StorageDescriptor": {
                    "Location": table["location"],
                    "InputFormat": "parquet" if table["format"] == "parquet" else "json",
                    "Columns": [
                        {"Name": col["name"], "Type": col["type"]}
                        for col in table.get("schema", [])
                    ],
                },
                "PartitionKeys": [{"Name": p, "Type": "string"} for p in table.get("partitions", [])],
                "UpdateTime": datetime.utcnow().isoformat(),
            }

            updated_tables.append(glue_table)

        logger.info("Catalog updated", num_updated=len(updated_tables))

        return {
            "status": "success",
            "updated_tables": updated_tables,
        }

    async def _generate_schema_card(self, state: GraphState) -> Dict[str, Any]:
        """Generate schema card for a table."""
        database = state.inputs.get("database")
        table = state.inputs.get("table")

        logger.info("Generating schema card", database=database, table=table)

        # In production: query Glue catalog, run Great Expectations profiling

        schema_card = {
            "metadata": {
                "database": database,
                "table": table,
                "owner": "data-engineering",
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
            },
            "schema": [
                {
                    "name": "customer_id",
                    "type": "string",
                    "nullable": False,
                    "description": "Unique customer identifier",
                },
                {
                    "name": "email",
                    "type": "string",
                    "nullable": True,
                    "pii": True,
                    "description": "Customer email address",
                },
            ],
            "statistics": {
                "row_count": 50000,
                "size_bytes": 5242880,
                "last_modified": datetime.utcnow().isoformat(),
            },
            "quality": {
                "completeness": 0.98,
                "freshness_hours": 2,
            },
            "lineage": {
                "upstream": ["bronze.customers_raw"],
                "downstream": ["gold.customer_features"],
            },
        }

        # Write schema card to S3 (in production)
        card_uri = f"s3://{self.config.metadata_bucket}/schemas/{database}/{table}/card.yaml"

        logger.info("Schema card generated", card_uri=card_uri)

        return {
            "status": "success",
            "schema_card": schema_card,
            "card_uri": card_uri,
        }

    async def _track_lineage(self, state: GraphState) -> Dict[str, Any]:
        """Track data lineage."""
        lineage_events = state.inputs.get("lineage_events", [])

        logger.info("Tracking lineage", num_events=len(lineage_events))

        # Build lineage graph
        lineage_graph = {
            "nodes": [],
            "edges": [],
        }

        for event in lineage_events:
            # Add source and target nodes
            source_node = {
                "id": event.get("source_uri"),
                "type": "dataset",
                "layer": self._extract_layer(event.get("source_uri")),
            }
            target_node = {
                "id": event.get("target_uri"),
                "type": "dataset",
                "layer": self._extract_layer(event.get("target_uri")),
            }

            lineage_graph["nodes"].extend([source_node, target_node])

            # Add edge
            lineage_graph["edges"].append({
                "source": event.get("source_uri"),
                "target": event.get("target_uri"),
                "transformation": event.get("transformation"),
                "agent": event.get("agent_name"),
                "timestamp": event.get("timestamp"),
            })

        # Deduplicate nodes
        seen_nodes = set()
        unique_nodes = []
        for node in lineage_graph["nodes"]:
            if node["id"] not in seen_nodes:
                seen_nodes.add(node["id"])
                unique_nodes.append(node)
        lineage_graph["nodes"] = unique_nodes

        # Write lineage graph to S3 (in production)
        ds = datetime.utcnow().strftime("%Y%m%d")
        graph_uri = f"s3://{self.config.metadata_bucket}/lineage/{ds}/graph.json"

        logger.info("Lineage tracked", num_nodes=len(lineage_graph["nodes"]))

        return {
            "status": "success",
            "lineage_graph": lineage_graph,
            "graph_uri": graph_uri,
        }

    def _is_pii_field(self, field_name: str, field_type: str) -> bool:
        """Detect if a field contains PII."""
        pii_field_names = [
            "email", "phone", "mobile", "address", "postcode", "postal_code",
            "zip_code", "national_insurance", "ni_number", "ssn",
            "credit_card", "bank_account", "iban", "sort_code",
        ]

        field_lower = field_name.lower()
        for pii_name in pii_field_names:
            if pii_name in field_lower:
                return True

        return False

    def _extract_layer(self, uri: str) -> str:
        """Extract data layer from URI."""
        if "/bronze/" in uri:
            return "bronze"
        elif "/silver/" in uri:
            return "silver"
        elif "/gold/" in uri:
            return "gold"
        else:
            return "unknown"


async def create_data_cataloguer() -> DataCataloguer:
    """Factory function to create data cataloguer."""
    return DataCataloguer()
