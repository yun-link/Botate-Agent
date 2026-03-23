from dataclasses import dataclass

from model import Message

@dataclass
class _BasePrompt:
    prompt_text: str
    def __post_init__(self):
        self._formatted_prompt_text: str = self.prompt_text
    def to_message(self):
        pass
    def format(self,*args, **kwargs):
        self._formatted_prompt_text = self.prompt_text.format(*args, **kwargs)
    @classmethod
    def load_prompt_file(cls, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return cls(f.read())
@dataclass
class UserPrompt(_BasePrompt):
    def to_message(self):
        return Message(
            role='user',
            content=self._formatted_prompt_text
        )

@dataclass
class SystemPrompt(_BasePrompt):
    def to_message(self):
        return Message(
            role='system',
            content=self._formatted_prompt_text
        )

class Prompt:
    def __init__(
        self, 
        system_prompt: SystemPrompt=None,
        user_prompt: UserPrompt=None
    ):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
    
    def to_messages(self):
        messages = []
        if self.system_prompt:
            messages.append(self.system_prompt.to_message())
        if self.user_prompt:
            messages.append(self.user_prompt.to_message())
        return messages
    
    @classmethod
    def load_prompt_from_file(
        cls,
        system_prompt_file_path: str=None,
        user_prompt_file_path: str=None
    ):
        system_prompt = None
        user_prompt = None
        if system_prompt_file_path:
            system_prompt = SystemPrompt.load_prompt_file(system_prompt_file_path)
        if user_prompt_file_path:
            user_prompt = UserPrompt.load_prompt_file(user_prompt_file_path)
        return cls(system_prompt, user_prompt)
