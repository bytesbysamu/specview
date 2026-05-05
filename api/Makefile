.PHONY: dev test lint generate-dtos check-dtos install docker-build docker-up docker-down docker-logs docker-smoke

PYTHON = python3

## Install production and development dependencies
install:
	pip install -r requirements.txt -r requirements-dev.txt

## Run the Flask development server (port from PORT env var, default 3101)
dev:
	$(PYTHON) app.py

## Run the full test suite
test:
	$(PYTHON) -m pytest

## Lint with flake8 (generated dtos/models.py excluded)
lint:
	flake8 . --max-line-length=120 --exclude=__pycache__,dtos/models.py

## Regenerate dtos/models.py from openapi.yaml
generate-dtos:
	$(PYTHON) -m datamodel_code_generator \
		--input openapi.yaml \
		--output dtos/models.py \
		--output-model-type pydantic_v2.BaseModel \
		--input-file-type openapi \
		--target-python-version 3.10 \
		--disable-timestamp

## Fail non-zero if committed dtos/models.py does not match what would be generated
check-dtos:
	@TMPFILE=$$(mktemp /tmp/models_check_XXXXXX); \
	$(PYTHON) -m datamodel_code_generator \
		--input openapi.yaml \
		--output $$TMPFILE \
		--output-model-type pydantic_v2.BaseModel \
		--input-file-type openapi \
		--target-python-version 3.10 \
		--disable-timestamp; \
	GEN_EXIT=$$?; \
	if [ $$GEN_EXIT -ne 0 ]; then \
		echo "error: datamodel-codegen failed with exit code $$GEN_EXIT" >&2; \
		rm -f $$TMPFILE; \
		exit $$GEN_EXIT; \
	fi; \
	diff dtos/models.py $$TMPFILE; \
	EXIT=$$?; \
	rm -f $$TMPFILE; \
	exit $$EXIT

## Build the Docker image
docker-build:
	docker compose build

## Start the containerized API (detached; use docker-logs to follow output)
docker-up:
	docker compose up -d

## Stop and remove the containerized API
docker-down:
	docker compose down

## Tail API container logs (Ctrl-C to stop)
docker-logs:
	docker compose logs -f api

## Smoke test the running container — mirrors the CI docker-build job
## Requires: container started with make docker-up and CHAIN_PROVIDER=mock
docker-smoke:
	@curl -sf http://localhost:3101/health | grep -q 'ok' && echo "✓ /health OK"
	@curl -sf http://localhost:3101/api/projects > /dev/null && echo "✓ /api/projects OK"
