"""Generated DTOs derived from flask/openapi.yaml.

To regenerate after updating openapi.yaml:

    datamodel-codegen \\
      --input flask/openapi.yaml \\
      --input-file-type openapi \\
      --output flask/dtos/models.py \\
      --output-model-type pydantic_v2.BaseModel

Commit the updated models.py. Manual edits to models.py are a red flag
that openapi.yaml is incomplete.
"""
from .models import *  # noqa: F401, F403
