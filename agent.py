import asyncio
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

from browser_use.browser.views import CurrentPageState
from browser_use.agent.views import AgentOutput, AgentHistory, ActionModel, ActionResult
from browser_agent.llm_service import LLMService
from browser_use.memory.views import Memory
from browser_agent.browser_use_adapter import BrowserUseAdapter


class Action(Enum):
    """Available actions for the browser agent"""
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    GOTO = "goto"
    WAIT = "wait"
    STOP = "stop"


class AgentState(BaseModel):
    """Current state of the agent"""
    page_state: CurrentPageState
    memory: Memory
    history: AgentHistory


class ActionStep(BaseModel):
    """A single action step in the agent's plan"""
    action: Action
    parameters: Dict[str, Any]
    description: str


class BrowserAgent:
    """
    ReAct (Reasoning + Acting) based browser automation agent
    """
    
    def __init__(self, llm_service: LLMService, max_steps: int = 50, headless: bool = True):
        self.llm_service = llm_service
        self.browser = BrowserUseAdapter(headless=headless)
        self.max_steps = max_steps
        self.history = AgentHistory()
        
    async def run_task(self, task: str) -> AgentOutput:
        """
        Main method to run a task in the browser
        """
        try:
            # Initialize browser
            await self.browser.start_session()
            
            # Main loop - ReAct pattern (Reasoning + Acting)
            for step in range(self.max_steps):
                # 1. Observe current page state
                current_state = await self.browser.get_current_page_state()
                
                # 2. Reason about next action
                action_result = await self._think_and_act(task, current_state)
                
                # 3. Execute action
                execution_result = await self.browser.execute_action(action_result.action)
                
                # 4. Add to history
                # Note: We need to adapt the result format to match expected types
                self.history.add_step(action_result, ActionResult(
                    action=action_result.action,
                    success=execution_result.success,
                    result=execution_result.result
                ))
                
                # 5. Check if task is completed
                if action_result.action.action == "stop":
                    break
                    
            return AgentOutput(
                success=True,
                result="Task completed successfully",
                history=self.history
            )
            
        except Exception as e:
            return AgentOutput(
                success=False,
                result=f"Error: {str(e)}",
                history=self.history
            )
        finally:
            await self.browser.end_session()
    
    async def _think_and_act(self, task: str, current_state: CurrentPageState) -> ActionResult:
        """
        Use LLM to decide next action based on current state and task
        """
        # Create prompt for LLM
        prompt = self._create_reasoning_prompt(task, current_state)
        
        # Get action from LLM
        response = await self.llm_service.get_completion(
            prompt,
            response_format=ActionModel
        )
        
        return ActionResult(
            action=response,
            success=True,
            result="Action planned successfully"
        )
    
    def _create_reasoning_prompt(self, task: str, current_state: CurrentPageState) -> str:
        """
        Create prompt for reasoning about next action
        """
        return f"""
        You are a browser automation agent. Your task is: {task}
        
        Current page state:
        - URL: {current_state.url}
        - Title: {current_state.title}
        - Content: {current_state.content}
        
        Available actions:
        - click(element_id): Click on an element with the given ID
        - type(element_id, text): Type text into an element with the given ID
        - scroll(direction): Scroll up/down
        - goto(url): Navigate to a URL
        - wait(seconds): Wait for specified seconds
        - stop: Stop the task execution
        
        Please provide the next action to take in JSON format:
        {{
            "action": "...",
            "parameters": {{}}
        }}
        """
    
    async def _execute_action(self, action: ActionModel) -> ActionResult:
        """
        Execute the action in the browser (kept for compatibility)
        """
        # This method is now mainly for compatibility - the actual execution
        # is handled by the BrowserUseAdapter
        execution_result = await self.browser.execute_action(action)
        return ActionResult(
            action=action,
            success=execution_result.success,
            result=execution_result.result
        )


class PlanAndExecuteAgent(BrowserAgent):
    """
    Plan-and-Execute based browser automation agent
    """
    
    def __init__(self, llm_service: LLMService, max_steps: int = 50, headless: bool = True):
        super().__init__(llm_service, max_steps, headless)
        
    async def run_task(self, task: str) -> AgentOutput:
        """
        Plan the entire task first, then execute the plan
        """
        try:
            # Initialize browser
            await self.browser.start_session()
            
            # 1. Create plan
            plan = await self._create_plan(task)
            
            # 2. Execute plan
            for step_num, step in enumerate(plan.steps):
                # Get current page state
                current_state = await self.browser.get_current_page_state()
                
                # Execute action
                execution_result = await self.browser.execute_action(step.action)
                
                # Add to history
                self.history.add_step(step.action, ActionResult(
                    action=step.action,
                    success=execution_result.success,
                    result=execution_result.result
                ))
                
                # Check if execution was successful
                if not execution_result.success:
                    # Try to recover or adjust plan
                    recovery_result = await self._handle_error(step, ActionResult(
                        action=step.action,
                        success=execution_result.success,
                        result=execution_result.result
                    ), current_state)
                    if not recovery_result.success:
                        return AgentOutput(
                            success=False,
                            result=f"Failed to execute step {step_num}: {recovery_result.result}",
                            history=self.history
                        )
            
            return AgentOutput(
                success=True,
                result="Task completed successfully",
                history=self.history
            )
            
        except Exception as e:
            return AgentOutput(
                success=False,
                result=f"Error: {str(e)}",
                history=self.history
            )
        finally:
            await self.browser.end_session()
    
    async def _create_plan(self, task: str) -> 'Plan':
        """
        Create a plan for the entire task
        """
        prompt = f"""
        You are a browser automation planner. Create a detailed plan to complete this task: {task}
        
        Return the plan as a list of steps, each with an action and parameters.
        Available actions: click, type, scroll, goto, wait, stop
        
        Example format:
        {{
            "steps": [
                {{
                    "action": "goto",
                    "parameters": {{"url": "https://example.com"}},
                    "description": "Navigate to example.com"
                }},
                {{
                    "action": "click",
                    "parameters": {{"element_id": "search-box"}},
                    "description": "Click search box"
                }}
            ]
        }}
        """
        
        response = await self.llm_service.get_completion(
            prompt,
            response_format=Plan
        )
        
        return response


class PlanStep(BaseModel):
    action: ActionModel
    description: str


class Plan(BaseModel):
    steps: List[PlanStep]


class ReflectionAgent(BrowserAgent):
    """
    Reflection-based browser automation agent with self-correction
    """
    
    def __init__(self, llm_service: LLMService, max_steps: int = 50, max_reflections: int = 3, headless: bool = True):
        super().__init__(llm_service, max_steps, headless)
        self.max_reflections = max_reflections
    
    async def run_task(self, task: str) -> AgentOutput:
        """
        Run task with reflection and self-correction
        """
        try:
            # Initialize browser
            await self.browser.start_session()
            
            for step in range(self.max_steps):
                # 1. Observe current page state
                current_state = await self.browser.get_current_page_state()
                
                # 2. Reason about next action
                action_result = await self._think_and_act(task, current_state)
                
                # 3. Execute action
                execution_result = await self.browser.execute_action(action_result.action)
                
                # 4. Reflect on the result
                reflection_result = await self._reflect_on_action(
                    task,
                    action_result.action,
                    ActionResult(
                        action=action_result.action,
                        success=execution_result.success,
                        result=execution_result.result
                    ),
                    current_state
                )
                
                # 5. Add to history
                self.history.add_step(action_result, ActionResult(
                    action=action_result.action,
                    success=execution_result.success,
                    result=execution_result.result
                ))
                
                # 6. Check if task is completed
                if action_result.action.action == "stop":
                    break
                
                # 7. If reflection indicates an issue, try to correct
                if not reflection_result.is_correct:
                    correction_result = await self._correct_action(
                        task,
                        action_result.action,
                        ActionResult(
                            action=action_result.action,
                            success=execution_result.success,
                            result=execution_result.result
                        ),
                        reflection_result.feedback
                    )
                    
                    if correction_result.success:
                        self.history.add_step(correction_result.action, correction_result)
            
            return AgentOutput(
                success=True,
                result="Task completed successfully",
                history=self.history
            )
            
        except Exception as e:
            return AgentOutput(
                success=False,
                result=f"Error: {str(e)}",
                history=self.history
            )
        finally:
            await self.browser.end_session()
    
    async def _reflect_on_action(
        self,
        task: str,
        action: ActionModel,
        execution_result: ActionResult,
        current_state: CurrentPageState
    ) -> 'ReflectionResult':
        """
        Reflect on whether the action was successful and appropriate
        """
        prompt = f"""
        Task: {task}
        Action taken: {action.action} with parameters {action.parameters}
        Execution result: {execution_result.result}
        Current page state: {current_state}
        
        Was this action appropriate for the task? Did it succeed? What should be done next?
        
        Return in JSON format:
        {{
            "is_correct": true/false,
            "feedback": "explanation of what happened and what should be done",
            "suggested_next_action": "what action to take next"
        }}
        """
        
        response = await self.llm_service.get_completion(
            prompt,
            response_format=ReflectionResult
        )
        
        return response
    
    async def _correct_action(
        self,
        task: str,
        failed_action: ActionModel,
        execution_result: ActionResult,
        feedback: str
    ) -> ActionResult:
        """
        Correct a failed action based on feedback
        """
        prompt = f"""
        Task: {task}
        Failed action: {failed_action.action} with parameters {failed_action.parameters}
        Execution result: {execution_result.result}
        Feedback: {feedback}
        
        Based on the feedback, what should be the correct action to take?
        
        Return in JSON format:
        {{
            "action": "...",
            "parameters": {{}}
        }}
        """
        
        response = await self.llm_service.get_completion(
            prompt,
            response_format=ActionModel
        )
        
        # Execute the correction
        correction_result = await self.browser.execute_action(response)
        return ActionResult(
            action=response,
            success=correction_result.success,
            result=correction_result.result
        )


class ReflectionResult(BaseModel):
    is_correct: bool
    feedback: str
    suggested_next_action: str