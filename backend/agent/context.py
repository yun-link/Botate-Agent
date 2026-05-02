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
<<<<<<< HEAD
            search_result = self.memory_bank.search(query)
            if search_result.summary:
                results.append(search_result.summary)
        return results

=======
            results.extend(self.memory_bank.search(query))
        return results

class MemoryExtractor:
    def __init__(self):
        path_config = load_path_config()
        agent_config = load_agent_config()
        self.model_name = agent_config.CONTEXT_MANAGER_MODEL.model_name
        prompt_path = path_config.PROMPTS_PATH / 'context_manager' / 'memory_extractor'
        self.prompt = Prompt.load_prompt_from_file(
            system_prompt_file_path=prompt_path / 'system.md',
            user_prompt_file_path=prompt_path / 'user.md'
        )
        self.message_format = 'index: {index}\n role: {role}\n content: {content}'
        self.memory_format = 'id: {id}\n summary: {summary}\n messages: {messages}'
        self.memory_bank = load_memory_bank()
    def _format_messages(self, messages: List[Message]):
        formatted_messages = []
        for i, message in enumerate(messages):
            formatted_messages.append(
                self.message_format.format(
                    index=i,
                    role=message.role,
                    content=message.content
                )
            )
        return '\n'.join(formatted_messages)
    def _format_memories(self, memories: List[Memory]):
        formatted_memories = []
        for memory in memories:
            formatted_memories.append(
                self.memory_format.format(
                    id=memory.id,
                    summary=memory.summary,
                    messages=memory.messages
                )
            )
        return '\n'.join(formatted_memories)
    def extract(self, messages: List[Message], related_memories: List[Memory] = []):
        messages_formatted = self._format_messages(messages)
        memories_formatted = self._format_memories(related_memories)
        self.prompt.user_prompt.format(
            messages=messages_formatted,
            related_memories=memories_formatted
        )

        response = call(
            self.model_name,
            self.prompt.to_messages(),
            thinking=False
        )

        memories_json = json.loads(response.content.content)
        results = []
        for memory_json in memories_json:
            memory = Memory(
                messages=[messages[i] for i in memory_json['messages_index']],
                weight=memory_json['weight']
            )
            results.append(memory)
        return results
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
    
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
<<<<<<< HEAD
        self._save_memories_buffer = []

=======
        self._extractor = MemoryExtractor()
        self._save_memories_buffer = []

    def _formatted_memories(self, results: List[MemorySearchResult]):
        formatted = []
        for result in results:
            if result.memory.summary:
                formatted.append(
                    f"记忆摘要：{result.memory.summary}\n置信度：{result.score}"
                )
            else:
                formatted.append(
                    f"记忆内容：{result.memory.summary}\n置信度：{result.score}"
                )
        return '\n'.join(formatted)
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
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
<<<<<<< HEAD
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
=======
        self._save_memories_buffer.append(message)
        if message.role == 'user':
            memories = self._search_requestor.request_memory_search(self.messages)
            if memories:
                memories_text = self._formatted_memories(memories)

                if isinstance(message.content, Text):
                    message.content.content += f'\n相关记忆：\n{memories_text}'
                elif isinstance(message.content, list):
                    message.content.append(Text(f'\n相关记忆：\n{memories_text}'))
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
        if isimportant:
            self._improtant_message_indexes.append(len(self.messages) - 1)
        if len(self.messages) > self.sliding_window_size:
            self.sliding()
    def save_memories(self):
<<<<<<< HEAD
        memory_to_save = Memory(messages=self._save_memories_buffer)
        self.memory_bank.add(memory_to_save)
=======
        related_memories = [
            result.memory
            for result in
            self.memory_bank.search(str(self.messages))
        ]
        memories_to_save = self._extractor.extract(self._save_memories_buffer, related_memories)
        for memory in memories_to_save:
            self.memory_bank.add(memory)
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
        self._save_memories_buffer = []