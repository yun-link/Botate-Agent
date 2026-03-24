"""
Skill Manager module for loading and managing skills.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import skillkit
from skillkit import SkillMetadata, SkillManager as _SkillManager

from model.message_schemas import Message
from config import PATH_CONFIG


@dataclass
class SkillResult:
    """技能加载结果，包含技能返回的消息和相关信息"""
    success: bool
    name: str
    messages: List[Message] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class SkillManager:

    def __init__(self, skills_dir: str = None):
        config_skills_dir = PATH_CONFIG.SKILL_PATH
        self.skills_dir = skills_dir or config_skills_dir
        self._manager = _SkillManager(project_skill_dir=str(self.skills_dir))
        self._manager.discover()

    def get_skill_metadata(self, name: str):
        return self._manager.get_skill(name)

    def get_all_skills_metadata(self):
        return self._manager.list_skills()
        
    def get_skill(self, name: str) -> SkillResult:
        prompt = self._manager.invoke_skill(name)
        meta_data = self._manager.get_skill(name)
        return SkillResult(
            success=True,
            name=name,
            messages=[Message(role='user', content=prompt)],
            allowed_tools=meta_data.allowed_tools
        )

    def run_skill_script(self, skill_name: str, script_name: str, arguments: Dict):
        return self._manager.execute_skill_script(
            skill_name,
            script_name,
            arguments=arguments
        )