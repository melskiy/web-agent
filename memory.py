from typing import List, Dict, Any
from pydantic import BaseModel, Field
import json
import asyncio
from datetime import datetime


class MemoryItem(BaseModel):
    """Represents a single memory item with timestamp and content"""
    id: str
    timestamp: datetime
    content: str
    metadata: Dict[str, Any]
    importance: float = 1.0 # 0.0 to 1.0, where 1.0 is most important


class ShortTermMemory(BaseModel):
    """Short-term memory for current session"""
    history: List[MemoryItem] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    max_items: int = 50


class LongTermMemory(BaseModel):
    """Long-term memory using vector storage"""
    memories: List[MemoryItem] = Field(default_factory=list)
    embedding_model: str | None = None
    
    async def save_memory(self, item: MemoryItem):
        """Save a memory item to long-term storage"""
        # In a real implementation, this would store in a vector database
        # For now, we'll just keep it in memory
        self.memories.append(item)
    
    async def search_memories(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Search for relevant memories based on query"""
        # In a real implementation, this would use vector similarity search
        # For now, we'll do a simple keyword search
        results = []
        query_lower = query.lower()
        
        for memory in self.memories:
            if query_lower in memory.content.lower():
                results.append(memory)
        
        # Sort by importance and return top_k
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:top_k]
    
    async def update_memory_importance(self, memory_id: str, importance: float):
        """Update the importance of a memory item"""
        for memory in self.memories:
            if memory.id == memory_id:
                memory.importance = importance
                break


class AgentMemory:
    """Main memory manager combining short and long-term memory"""
    def __init__(self, short_term_max_items: int = 50, embedding_model: str | None = None):
        self.short_term = ShortTermMemory(max_items=short_term_max_items)
        self.long_term = LongTermMemory(embedding_model=embedding_model)
    
    def add_to_short_term(self, item: MemoryItem):
        """Add item to short-term memory"""
        self.short_term.history.append(item)
        
        # Keep memory size manageable
        if len(self.short_term.history) > self.short_term.max_items:
            self.short_term.history.pop(0)  # Remove oldest item
    
    async def add_to_long_term(self, item: MemoryItem):
        """Add item to long-term memory"""
        await self.long_term.save_memory(item)
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context from short-term memory"""
        return self.short_term.context.copy()
    
    def update_context(self, key: str, value: Any):
        """Update context in short-term memory"""
        self.short_term.context[key] = value
    
    def get_recent_history(self, count: int = 10) -> List[MemoryItem]:
        """Get recent history from short-term memory"""
        return self.short_term.history[-count:]
    
    async def search_long_term(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Search long-term memory"""
        return await self.long_term.search_memories(query, top_k)
    
    async def save_interaction_to_long_term(
        self,
        user_input: str,
        agent_response: str,
        page_state: str = "",
        importance: float = 0.5
    ):
        """Save an interaction to long-term memory"""
        import uuid
        
        memory_item = MemoryItem(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            content=f"User: {user_input}\nAgent: {agent_response}\nPage: {page_state}",
            metadata={
                "user_input": user_input,
                "agent_response": agent_response,
                "page_state": page_state
            },
            importance=importance
        )
        
        await self.add_to_long_term(memory_item)
    
    async def save_task_result_to_long_term(
        self,
        task: str,
        result: str,
        success: bool,
        importance: float = 0.8
    ):
        """Save a task result to long-term memory"""
        import uuid
        
        memory_item = MemoryItem(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            content=f"Task: {task}\nResult: {result}\nSuccess: {success}",
            metadata={
                "task": task,
                "result": result,
                "success": success
            },
            importance=importance
        )
        
        await self.add_to_long_term(memory_item)
    
    async def get_user_preferences(self) -> Dict[str, Any]:
        """Retrieve user preferences from long-term memory"""
        preferences = {}
        
        # Search for preference-related memories
        pref_memories = await self.search_long_term("preference", top_k=10)
        
        for memory in pref_memories:
            if "preference" in memory.content.lower():
                # Extract preference information
                preferences.update(memory.metadata.get("preferences", {}))
        
        return preferences
    
    async def get_common_tasks(self) -> List[str]:
        """Retrieve commonly performed tasks from long-term memory"""
        task_memories = await self.search_long_term("task", top_k=20)
        
        tasks = []
        for memory in task_memories:
            if "task" in memory.metadata:
                tasks.append(memory.metadata["task"])
        
        return list(set(tasks))  # Return unique tasks


# Example usage:
async def example_usage():
    # Create memory manager
    memory = AgentMemory()
    
    # Add to short-term memory
    item = MemoryItem(
        id="1",
        timestamp=datetime.now(),
        content="User asked to book a flight",
        metadata={"intent": "flight_booking", "destination": "Paris"},
        importance=0.7
    )
    memory.add_to_short_term(item)
    
    # Add to long-term memory
    await memory.save_interaction_to_long_term(
        user_input="Book a flight to Paris",
        agent_response="Searching for flights to Paris...",
        page_state="Flight search page",
        importance=0.6
    )
    
    # Search long-term memory
    relevant_memories = await memory.search_long_term("Paris", top_k=5)
    print(f"Found {len(relevant_memories)} relevant memories")
    
    # Get user preferences
    preferences = await memory.get_user_preferences()
    print(f"User preferences: {preferences}")


if __name__ == "__main__":
    asyncio.run(example_usage())