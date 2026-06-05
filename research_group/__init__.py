"""ResearchGroup: Multi-agent hierarchical optimization framework."""

from .evaluator import Evaluator
from .orchestrator import ResearchGroupResult, ResearchGroupV2
from .researcher import Researcher
from .supervisor import ROLE_SKILLS, SUPERVISOR_ROLES, Supervisor

__all__ = [
    "ResearchGroupV2",
    "ResearchGroupResult",
    "Researcher",
    "Supervisor",
    "SUPERVISOR_ROLES",
    "ROLE_SKILLS",
    "Evaluator",
]
