from typing import List
from datetime import datetime
import json

from model import call, Message, Text
from prompt_utils import Prompt
from config import load_path_config, load_agent_config
from .memory_bank import MemoryBank, Memory, MemorySearchResult, load_memory_bank

class MemorySearchRequestor:
    def __init__(self, memory_bank: MemoryBank):
        path_config = load_path_config()
        agent_config = load_agent_config()
        self.model_name = agent_config.CONTEXT_MANAGER_MODEL.model_name
        prompt_path = path_config.PROMPTS_PATH / 'context_manager' / 'memory_search_requestor'
        self.prompt = Prompt.load_prompt_from_file(
            system_prompt_file_path=prompt_path / 'system.md',
            user_prompt_file_path=prompt_path / 'user.md'
        )
        self.message_format = '- {role}：{content}'
        self.memory_bank = memory_bank
    def _format_messages(self, messages: List[Message]):
        formatted_messages = []
        for message in messages:
            formatted_messages.append(
                self.message_format.format(
                    role=message.role,
                    content=message.content
                )
            )
        return '\n'.join(formatted_messages)
    def request_memory_search(self, messages: List[Message]) -> List[MemorySearchResult]:
        context = self._format_messages(messages[:-1])
        user_message = messages[-1].content
        time = datetime.now()
        self.prompt.user_prompt.format(
            context=context,
            user_message=user_message,
            time=time
        )

        response = call(
            self.model_name,
            self.prompt.to_messages(),
            thinking=False
        )

        queries = json.loads(response.content.content)['queries']
        results = []
        for query in queries:
            search_result = self.memory_bank.search(query)
            if search_result.summary:
                results.append(search_result.summary)
        return results

    
class MessageContext:
    def __init__(
        self, 
        messages: List[Message], 
        memory_bank: MemoryBank,
        sliding_window_size: int = 0
    ):
        self.messages = messages
        self.memory_bank = memory_bank
        self.sliding_window_size = sliding_window_size
        self._improtant_message_indexes = []
        self._search_requestor = MemorySearchRequestor(memory_bank)
        self._save_memories_buffer = []

    def sliding(self):
        if self.sliding_window_size == 0:
            return
        for i, message in enumerate(self.messages):
            if i in self._improtant_message_indexes:
                pass
            else:
                del message
            if len(self.messages) - len(self._improtant_message_indexes) <= self.sliding_window_size:
                break
    def add_message(self, message: Message, isimportant: bool = False):
        self.messages.append(message)
        if message.role in ['assistant', 'user']:
            self._save_memories_buffer.append(message)
        if message.role == 'user':
            results = self._search_requestor.request_memory_search(self.messages)
            if results:
                text = '\n'.join(results)
                if isinstance(message.content, Text):
                    message.content.content += f'\n相关记忆：\n{text}'
                elif isinstance(message.content, list):
                    message.content.append(Text(f'\n相关记忆：\n{text}'))
        if isimportant:
            self._improtant_message_indexes.append(len(self.messages) - 1)
        if len(self.messages) > self.sliding_window_size:
            self.sliding()
    def save_memories(self):
        memory_to_save = Memory(messages=self._save_memories_buffer)
        self.memory_bank.add(memory_to_save)
        self._save_memories_buffer = []