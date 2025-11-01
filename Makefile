.PHONY: help install test lint format clean infra-plan infra-apply deploy local-e2e

# Default environment
ENV ?= dev
PIPELINE ?= churn
AGENT ?= supervisor-director

# Colours for output
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

help: ## Show this help message
	@echo "Aurora Energy Agentic Platform - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-20s${RESET} %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "${GREEN}Installing dependencies...${RESET}"
	pip install -e ".[dev,test]"
	pre-commit install

install-prod: ## Install production dependencies only
	@echo "${GREEN}Installing production dependencies...${RESET}"
	pip install -e .

test: ## Run all tests
	@echo "${GREEN}Running tests...${RESET}"
	pytest -v --cov --cov-report=term --cov-report=html

test-unit: ## Run unit tests only
	@echo "${GREEN}Running unit tests...${RESET}"
	pytest tests/unit -v

test-integration: ## Run integration tests
	@echo "${GREEN}Running integration tests...${RESET}"
	pytest tests/integration -v

test-agent: ## Test specific agent (use AGENT=name)
	@echo "${GREEN}Testing agent: ${AGENT}${RESET}"
	pytest agents/$(AGENT)/test_*.py -v

test-pipeline: ## Test specific pipeline (use PIPELINE=name)
	@echo "${GREEN}Testing pipeline: ${PIPELINE}${RESET}"
	pytest pipelines/$(PIPELINE)/test_*.py -v

lint: ## Run linting
	@echo "${GREEN}Running linters...${RESET}"
	ruff check libs agents pipelines apps
	mypy libs agents pipelines apps

format: ## Format code
	@echo "${GREEN}Formatting code...${RESET}"
	ruff format libs agents pipelines apps
	isort libs agents pipelines apps

format-check: ## Check code formatting
	@echo "${GREEN}Checking code formatting...${RESET}"
	ruff format --check libs agents pipelines apps
	isort --check-only libs agents pipelines apps

security-scan: ## Run security scans
	@echo "${GREEN}Running security scans...${RESET}"
	bandit -r libs agents pipelines apps -ll
	safety check

clean: ## Clean build artifacts
	@echo "${GREEN}Cleaning build artifacts...${RESET}"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build dist htmlcov .coverage

# Infrastructure targets
infra-init: ## Initialise Terraform
	@echo "${GREEN}Initialising Terraform for ${ENV}...${RESET}"
	cd infra/terraform/environments/$(ENV) && terraform init

infra-plan: ## Plan infrastructure changes (use ENV=dev|staging|prod)
	@echo "${GREEN}Planning infrastructure for ${ENV}...${RESET}"
	cd infra/terraform/environments/$(ENV) && terraform plan -out=tfplan

infra-apply: ## Apply infrastructure changes (use ENV=dev|staging|prod)
	@echo "${YELLOW}Applying infrastructure for ${ENV}...${RESET}"
	@echo "This will modify AWS resources. Continue? [y/N] " && read ans && [ $${ans:-N} = y ]
	cd infra/terraform/environments/$(ENV) && terraform apply tfplan

infra-destroy: ## Destroy infrastructure (use ENV=dev|staging|prod)
	@echo "${YELLOW}WARNING: This will destroy all infrastructure for ${ENV}!${RESET}"
	@echo "Are you sure? Type 'yes' to continue: " && read ans && [ "$$ans" = "yes" ]
	cd infra/terraform/environments/$(ENV) && terraform destroy

infra-output: ## Show Terraform outputs
	@echo "${GREEN}Terraform outputs for ${ENV}:${RESET}"
	cd infra/terraform/environments/$(ENV) && terraform output

# Deployment targets
deploy: ## Deploy all agents to specified environment
	@echo "${GREEN}Deploying to ${ENV}...${RESET}"
	python scripts/deploy.py --env $(ENV)

deploy-agent: ## Deploy specific agent (use AGENT=name ENV=dev|staging|prod)
	@echo "${GREEN}Deploying agent ${AGENT} to ${ENV}...${RESET}"
	python scripts/deploy_agent.py --agent $(AGENT) --env $(ENV)

# Pipeline execution
run-pipeline: ## Run specific pipeline (use PIPELINE=churn|acquisition|load)
	@echo "${GREEN}Running pipeline: ${PIPELINE}${RESET}"
	python apps/run_pipeline.py --pipeline $(PIPELINE) --env $(ENV)

pipeline-status: ## Check pipeline status
	@echo "${GREEN}Checking status for pipeline: ${PIPELINE}${RESET}"
	python apps/pipeline_status.py --pipeline $(PIPELINE) --env $(ENV)

view-report: ## View latest report for pipeline
	@echo "${GREEN}Opening report for pipeline: ${PIPELINE}${RESET}"
	python apps/view_report.py --pipeline $(PIPELINE) --env $(ENV)

# Local development & testing
local-setup: ## Set up local development environment with Docker
	@echo "${GREEN}Setting up local environment...${RESET}"
	docker-compose -f docker-compose.local.yml up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	python scripts/seed_local_data.py

local-teardown: ## Tear down local development environment
	@echo "${GREEN}Tearing down local environment...${RESET}"
	docker-compose -f docker-compose.local.yml down -v

local-e2e: ## Run end-to-end test locally with synthetic data
	@echo "${GREEN}Running local E2E test...${RESET}"
	$(MAKE) local-setup
	pytest tests/e2e/test_churn_pipeline.py -v --local
	$(MAKE) local-teardown

test-e2e: ## Run end-to-end test in AWS (small dataset)
	@echo "${GREEN}Running E2E test in ${ENV}...${RESET}"
	pytest tests/e2e/test_churn_pipeline.py -v --env $(ENV)

# Monitoring & observability
logs: ## Tail logs for specific agent
	@echo "${GREEN}Tailing logs for agent: ${AGENT}${RESET}"
	aws logs tail /aws/lambda/aurora-$(ENV)-$(AGENT) --follow --region eu-west-2

metrics: ## Open CloudWatch metrics dashboard
	@echo "${GREEN}Opening metrics dashboard for ${ENV}...${RESET}"
	python scripts/open_dashboard.py --env $(ENV) --type metrics

traces: ## Open distributed tracing UI
	@echo "${GREEN}Opening tracing UI...${RESET}"
	python scripts/open_dashboard.py --env $(ENV) --type traces

mlflow-ui: ## Start MLflow UI
	@echo "${GREEN}Starting MLflow UI...${RESET}"
	mlflow ui --backend-store-uri $(shell python scripts/get_mlflow_uri.py --env $(ENV))

# Agent & pipeline scaffolding
new-agent: ## Create new agent scaffold (use NAME=my-agent-name)
	@echo "${GREEN}Creating new agent: ${NAME}${RESET}"
	python scripts/scaffold_agent.py --name $(NAME)
	@echo "Agent created at: agents/$(NAME)/"
	@echo "Next steps:"
	@echo "  1. Edit agents/$(NAME)/contract.yaml"
	@echo "  2. Implement agents/$(NAME)/agent.py"
	@echo "  3. Add tests in agents/$(NAME)/test_agent.py"
	@echo "  4. Register in apps/supervisor/graph.py"

new-pipeline: ## Create new pipeline scaffold (use NAME=my-pipeline)
	@echo "${GREEN}Creating new pipeline: ${NAME}${RESET}"
	python scripts/scaffold_pipeline.py --name $(NAME)
	@echo "Pipeline created at: pipelines/$(NAME)/"

# Data operations
seed-data: ## Seed example data to specified environment
	@echo "${GREEN}Seeding data to ${ENV}...${RESET}"
	python scripts/seed_data.py --env $(ENV) --dataset examples/datasets/sample_customers.csv

validate-data: ## Run data validation checks
	@echo "${GREEN}Running data validation for ${ENV}...${RESET}"
	python scripts/validate_data.py --env $(ENV)

# Cost & governance
cost-report: ## Generate cost report
	@echo "${GREEN}Generating cost report for ${ENV}...${RESET}"
	python scripts/cost_report.py --env $(ENV) --days 7

audit-trail: ## View audit trail
	@echo "${GREEN}Viewing audit trail for ${ENV}...${RESET}"
	python scripts/audit_trail.py --env $(ENV) --hours 24

# Documentation
docs-serve: ## Serve documentation locally
	@echo "${GREEN}Serving documentation...${RESET}"
	mkdocs serve

docs-build: ## Build documentation
	@echo "${GREEN}Building documentation...${RESET}"
	mkdocs build

# Git hooks
pre-commit: ## Run pre-commit hooks manually
	@echo "${GREEN}Running pre-commit hooks...${RESET}"
	pre-commit run --all-files

# Docker images
docker-build: ## Build Docker images
	@echo "${GREEN}Building Docker images...${RESET}"
	docker-compose -f docker-compose.build.yml build

docker-push: ## Push Docker images to ECR
	@echo "${GREEN}Pushing Docker images to ECR...${RESET}"
	./scripts/push_images.sh $(ENV)

# Utilities
version: ## Show version information
	@echo "Aurora Energy Platform"
	@python -c "import sys; print(f'Python: {sys.version}')"
	@terraform version | head -n 1
	@echo "Environment: $(ENV)"

check-env: ## Check environment setup
	@echo "${GREEN}Checking environment setup...${RESET}"
	@python scripts/check_env.py

graph-viz: ## Visualise LangGraph agent graph
	@echo "${GREEN}Generating graph visualisation...${RESET}"
	python scripts/visualize_graph.py --output docs/graph.png
	@echo "Graph saved to: docs/graph.png"
