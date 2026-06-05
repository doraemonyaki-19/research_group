"""Skill loader for ResearchGroup."""
import os
from pathlib import Path

def load_skill_content(skill_name: str) -> str:
    """Load the content of a skill's SKILL.md file.
    
    Tries the bundled skills in research_group/skills/ first.
    Falls back to ~/.claude/skills/ if not found.
    """
    if not skill_name:
        return ""
        
    # Try bundled skills first
    bundled_path = Path(__file__).parent / "skills" / skill_name / "SKILL.md"
    if bundled_path.exists():
        return bundled_path.read_text(encoding="utf-8")
        
    # Try ~/.claude/skills fallback
    user_home_path = Path.home() / ".claude" / "skills" / skill_name / "SKILL.md"
    if user_home_path.exists():
        return user_home_path.read_text(encoding="utf-8")
        
    return f"(Warning: Skill '{skill_name}' content could not be loaded)"
