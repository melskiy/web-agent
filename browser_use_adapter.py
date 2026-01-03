"""
Adapter for browser-use library integration
This module provides the interface between our agent system and the browser-use library
"""
from typing import Dict, Any, Optional
import asyncio
from dataclasses import dataclass

try:
    from browser_use.browser.service import BrowserService
    from browser_use.browser.views import CurrentPageState
    from browser_use.agent.views import ActionModel, ActionResult
    from browser_use.llm.service import LLMService as BrowserUseLLMService
    from browser_use.memory.views import Memory
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    print("⚠️  browser-use library not found. Install it using: pip install browser-use")


@dataclass
class BrowserActionResult:
    """Result of a browser action"""
    success: bool
    result: str
    page_state: Optional[CurrentPageState] = None


class BrowserUseAdapter:
    """
    Adapter class to integrate browser-use library with our agent system
    """
    
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        if not BROWSER_USE_AVAILABLE:
            raise ImportError(
                "browser-use library is required but not installed. "
                "Install it using: pip install browser-use"
            )
        
        self.browser_service = BrowserService(
            headless=headless,
            slow_mo=slow_mo
        )
        self.session_active = False
    
    async def start_session(self):
        """Start a new browser session"""
        await self.browser_service.create_session()
        self.session_active = True
        print("🌐 Браузерная сессия запущена")
    
    async def end_session(self):
        """End the current browser session"""
        if self.session_active:
            await self.browser_service.close_session()
            self.session_active = False
            print("🔒 Браузерная сессия завершена")
    
    async def get_current_page_state(self) -> CurrentPageState:
        """Get the current state of the page"""
        if not self.session_active:
            raise RuntimeError("Browser session not active. Call start_session() first.")
        
        return await self.browser_service.get_current_page_state()
    
    async def execute_action(self, action: ActionModel) -> BrowserActionResult:
        """Execute a browser action"""
        if not self.session_active:
            raise RuntimeError("Browser session not active. Call start_session() first.")
        
        try:
            if action.action == "click":
                element_id = action.parameters.get("element_id")
                if element_id:
                    await self.browser_service.click_element(element_id)
                    return BrowserActionResult(
                        success=True,
                        result=f"Clicked element {element_id}",
                        page_state=await self.get_current_page_state()
                    )
                else:
                    return BrowserActionResult(
                        success=False,
                        result="Missing element_id parameter for click action"
                    )
            
            elif action.action == "type":
                element_id = action.parameters.get("element_id")
                text = action.parameters.get("text")
                if element_id and text:
                    await self.browser_service.type_text(element_id, text)
                    return BrowserActionResult(
                        success=True,
                        result=f"Typed '{text}' into element {element_id}",
                        page_state=await self.get_current_page_state()
                    )
                else:
                    return BrowserActionResult(
                        success=False,
                        result="Missing element_id or text parameter for type action"
                    )
            
            elif action.action == "scroll":
                direction = action.parameters.get("direction", "down")
                await self.browser_service.scroll_page(direction)
                return BrowserActionResult(
                    success=True,
                    result=f"Scrolled {direction}",
                    page_state=await self.get_current_page_state()
                )
            
            elif action.action == "goto":
                url = action.parameters.get("url")
                if url:
                    await self.browser_service.go_to_url(url)
                    return BrowserActionResult(
                        success=True,
                        result=f"Navigated to {url}",
                        page_state=await self.get_current_page_state()
                    )
                else:
                    return BrowserActionResult(
                        success=False,
                        result="Missing url parameter for goto action"
                    )
            
            elif action.action == "wait":
                seconds = action.parameters.get("seconds", 1)
                await asyncio.sleep(seconds)
                return BrowserActionResult(
                    success=True,
                    result=f"Waited for {seconds} seconds",
                    page_state=await self.get_current_page_state()
                )
            
            elif action.action == "stop":
                return BrowserActionResult(
                    success=True,
                    result="Stop action received",
                    page_state=await self.get_current_page_state()
                )
            
            else:
                return BrowserActionResult(
                    success=False,
                    result=f"Unknown action: {action.action}"
                )
        
        except Exception as e:
            return BrowserActionResult(
                success=False,
                result=f"Error executing action {action.action}: {str(e)}"
            )
    
    async def take_screenshot(self, path: str = None) -> str:
        """Take a screenshot of the current page"""
        if not self.session_active:
            raise RuntimeError("Browser session not active. Call start_session() first.")
        
        return await self.browser_service.take_screenshot(path)
    
    async def get_page_content(self) -> str:
        """Get the text content of the current page"""
        if not self.session_active:
            raise RuntimeError("Browser session not active. Call start_session() first.")
        
        page_state = await self.get_current_page_state()
        return page_state.content


# Example usage of the adapter
async def example_usage():
    """
    Example of how to use the BrowserUseAdapter with our agent system
    """
    print("🧪 Тестирую интеграцию с browser-use...")
    
    # Create adapter
    adapter = BrowserUseAdapter(headless=True)
    
    try:
        # Start session
        await adapter.start_session()
        
        # Go to a test page
        action = ActionModel(
            action="goto",
            parameters={"url": "https://httpbin.org/forms/post"}
        )
        result = await adapter.execute_action(action)
        print(f"Navigation result: {result.result}")
        
        # Get page state
        page_state = await adapter.get_current_page_state()
        print(f"Current page: {page_state.title}")
        
        # Take screenshot
        screenshot_path = await adapter.take_screenshot("test_screenshot.png")
        print(f"Screenshot saved to: {screenshot_path}")
        
    except Exception as e:
        print(f"Error in example: {e}")
    finally:
        # End session
        await adapter.end_session()


if __name__ == "__main__":
    if BROWSER_USE_AVAILABLE:
        asyncio.run(example_usage())
    else:
        print("browser-use library is not available. Please install it to run this example.")