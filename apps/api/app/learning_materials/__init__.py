"""Owner-scoped learning material discovery and delivery."""

from .repository import SupabaseLearningMaterialRepository
from .service import LearningMaterialService

__all__ = ["LearningMaterialService", "SupabaseLearningMaterialRepository"]
