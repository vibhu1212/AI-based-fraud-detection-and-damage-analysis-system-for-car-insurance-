"""
Base Module — Abstract interface for all pipeline modules (M0-M7).
Every module implements process(), health_check(), and get_info().
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import time
import logging

logger = logging.getLogger(__name__)


class ModuleInput(BaseModel):
    """Standard input for any pipeline module."""
    claim_id: str = ""
    images: List[str] = Field(default_factory=list, description="File paths or base64-encoded images")
    image_arrays: List[Any] = Field(default_factory=list, description="numpy arrays (not serialized)")
    context: Dict[str, Any] = Field(default_factory=dict, description="Outputs from prior modules")
    config: Dict[str, Any] = Field(default_factory=dict, description="Track, toggles, etc.")

    class Config:
        arbitrary_types_allowed = True


class ModuleOutput(BaseModel):
    """Standard output from any pipeline module."""
    module_id: str
    status: str = "success"  # "success", "error", "skipped", "fallback"
    output: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)
    audit: Dict[str, str] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class BaseModule(ABC):
    """Abstract base class for all pipeline modules."""

    module_id: str = "BASE"
    module_name: str = "Base Module"
    version: str = "0.1.0"

    @abstractmethod
    def process(self, module_input: ModuleInput) -> ModuleOutput:
        """Process input through this module."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if module is ready (models loaded, dependencies available)."""
        return False

    def get_info(self) -> Dict[str, Any]:
        """Return module metadata."""
        return {
            "module_id": self.module_id,
            "module_name": self.module_name,
            "version": self.version,
            "healthy": self.health_check(),
        }

    def _create_output(
        self,
        output: Dict[str, Any],
        status: str = "success",
        start_time: Optional[float] = None,
        errors: Optional[List[str]] = None,
    ):
        """Helper to create a standardized ModuleOutput."""
        # Note: We return dictionary to avoid BaseModel instantiation type checks in subclasses
        # until the pipeline framework is fully typed.
        metrics = {}
        if start_time is not None:
            metrics["inference_time_ms"] = round((time.time() - start_time) * 1000)

        return {
            "module_id": self.module_id,
            "status": status,
            "output": output,
            "metrics": metrics,
            "audit": {
                "module_version": self.version,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "errors": errors or [],
        }

    def _create_error(self, error_msg: str, start_time: Optional[float] = None):
        """Helper for error responses."""
        logger.error(f"[{self.module_id}] {error_msg}")
        return self._create_output(
            output={},
            status="error",
            start_time=start_time,
            errors=[error_msg],
        )
