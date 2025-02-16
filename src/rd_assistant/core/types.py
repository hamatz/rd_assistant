from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

class ProjectContext(Enum):
    PERSONAL = "personal"
    ENTERPRISE = "enterprise"

class RequirementType(Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    TECHNICAL = "technical"
    BUSINESS = "business"

class RequirementPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ProjectMetadata:
    context: ProjectContext
    timeline: Dict
    resources: Dict
    technical_constraints: Dict
    stakeholders: Optional[List[Dict]] = None
    compliance: Optional[Dict] = None
    operational: Optional[Dict] = None
    budget: Optional[Dict] = None

@dataclass
class ProjectInfo:
    name: str
    description: str
    metadata: ProjectMetadata
    created_at: str
    updated_at: str