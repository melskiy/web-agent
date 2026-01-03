import asyncio
from typing import Dict, Any
from dataclasses import dataclass

from browser_agent.agent import BrowserAgent, ReflectionAgent
from browser_agent.memory import AgentMemory
from browser_agent.security import SecurityManager, SecurityConfig
from browser_agent.llm_service import LLMService
from config import config


@dataclass
class FoodOrderConfig:
    """Configuration for food ordering agent"""
    delivery_service_url: str = "https://eda.yandex.ru"  # Example: Yandex.Eda
    user_credentials: Dict[str, str] = None
    preferred_restaurants: list = None
    favorite_items: list = None
    
    def __post_init__(self):
        if self.user_credentials is None:
            self.user_credentials = {}
        if self.preferred_restaurants is None:
            self.preferred_restaurants = []
        if self.favorite_items is None:
            self.favorite_items = ["BBQ-бургер", "картошка фри"]


class FoodOrderingAgent:
    """
    Specialized agent for food ordering tasks
    """
    
    def __init__(self, llm_service: LLMService, config: FoodOrderConfig = None):
        if config is None:
            config = FoodOrderConfig()
        self.config = config
        self.llm_service = llm_service
        self.memory = AgentMemory()
        self.security = SecurityManager(SecurityConfig())
        self.agent = ReflectionAgent(llm_service)  # Using reflection agent for better error handling
    
    async def order_food(self, food_items: list = None, restaurant_hint: str = "") -> Dict[str, Any]:
        """
        Main method to order food based on user request
        """
        if food_items is None:
            food_items = self.config.favorite_items
            
        print(f"🎯 Начинаю заказ еды: {', '.join(food_items)}")
        if restaurant_hint:
            print(f"📍 Ресторан: {restaurant_hint}")
        
        try:
            # Add task to memory
            await self.memory.save_task_result_to_long_term(
                task=f"Order {', '.join(food_items)}",
                result="Started food ordering process",
                success=True,
                importance=0.9
            )
            
            # Step 1: Navigate to delivery service
            print("🌐 Открываю сервис доставки еды...")
            result = await self._navigate_to_delivery_service()
            if not result["success"]:
                return result
            
            # Step 2: Find restaurant
            print("🔍 Ищу ресторан...")
            restaurant_result = await self._find_restaurant(food_items, restaurant_hint)
            if not restaurant_result["success"]:
                return restaurant_result
            
            restaurant_name = restaurant_result["restaurant_name"]
            print(f"🍽️  Найден ресторан: {restaurant_name}")
            
            # Step 3: Add items to cart
            print("🛒 Добавляю товары в корзину...")
            cart_result = await self._add_items_to_cart(food_items)
            if not cart_result["success"]:
                return cart_result
            
            # Step 4: Proceed to checkout
            print("💳 Перехожу к оформлению заказа...")
            checkout_result = await self._proceed_to_checkout()
            if not checkout_result["success"]:
                return checkout_result
            
            # Step 5: Complete order (stop before payment as per requirements)
            print("✅ Заказ оформлен (остановка перед оплатой)")
            return {
                "success": True,
                "result": f"Заказ {', '.join(food_items)} из {restaurant_name} готов к оплате",
                "order_summary": cart_result["items"]
            }
            
        except Exception as e:
            error_msg = f"Ошибка при заказе еды: {str(e)}"
            print(error_msg)
            
            await self.memory.save_task_result_to_long_term(
                task=f"Order {', '.join(food_items)}",
                result=error_msg,
                success=False,
                importance=0.9
            )
            
            return {
                "success": False,
                "result": error_msg
            }
    
    async def _navigate_to_delivery_service(self) -> Dict[str, Any]:
        """
        Navigate to the food delivery service
        """
        try:
            # In a real implementation, this would interact with the browser through browser-use
            # For demo purposes, we'll simulate the action
            print(f"  → Перехожу на {self.config.delivery_service_url}")
            
            # Simulate waiting for page load
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "result": f"Успешно перешел на {self.config.delivery_service_url}"
            }
        except Exception as e:
            return {
                "success": False,
                "result": f"Не удалось перейти на сервис доставки: {str(e)}"
            }
    
    async def _find_restaurant(self, food_items: list, restaurant_hint: str = "") -> Dict[str, Any]:
        """
        Find a restaurant that serves the requested food items
        """
        try:
            # Check memory for previously ordered restaurants
            if restaurant_hint:
                # If user specified a restaurant, try to find it
                print(f"  → Ищу ресторан по подсказке: {restaurant_hint}")
                # Simulate finding the restaurant
                await asyncio.sleep(1)
                return {
                    "success": True,
                    "restaurant_name": restaurant_hint,
                    "result": f"Найден ресторан: {restaurant_hint}"
                }
            else:
                # Look for restaurants that serve the requested items
                print(f"  → Ищу рестораны с {', '.join(food_items)}")
                
                # Check memory for previously ordered restaurants
                common_restaurants = await self.memory.get_common_tasks()
                for task in common_restaurants:
                    if "ресторан" in task.lower() or "заказ" in task.lower():
                        print(f" → Найден предыдущий ресторан из памяти")
                        # Simulate finding the restaurant
                        await asyncio.sleep(1)
                        return {
                            "success": True,
                            "restaurant_name": task.split()[-1] if task.split() else "Известный ресторан",
                            "result": f"Найден предыдущий ресторан из памяти"
                        }
                
                # If not found in memory, simulate search
                await asyncio.sleep(1)
                return {
                    "success": True,
                    "restaurant_name": "BBQ Palace",
                    "result": f"Найден подходящий ресторан по запросу {', '.join(food_items)}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "result": f"Не удалось найти ресторан: {str(e)}"
            }
    
    async def _add_items_to_cart(self, food_items: list) -> Dict[str, Any]:
        """
        Add requested food items to cart
        """
        try:
            print(f"  → Добавляю в корзину: {', '.join(food_items)}")
            
            # Simulate adding items to cart
            added_items = []
            for item in food_items:
                print(f"    - Добавляю {item}")
                await asyncio.sleep(0.5)  # Simulate time to add item
                added_items.append(item)
            
            return {
                "success": True,
                "result": f"Успешно добавлено в корзину: {', '.join(added_items)}",
                "items": added_items
            }
        except Exception as e:
            return {
                "success": False,
                "result": f"Не удалось добавить товары в корзину: {str(e)}"
            }
    
    async def _proceed_to_checkout(self) -> Dict[str, Any]:
        """
        Proceed to checkout page
        """
        try:
            print("  → Перехожу к оформлению заказа")
            
            # Simulate navigating to checkout
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "result": "Успешно перешел к оформлению заказа"
            }
        except Exception as e:
            return {
                "success": False,
                "result": f"Не удалось перейти к оформлению: {str(e)}"
            }


async def main():
    """
    Main function to demonstrate the food ordering agent
    """
    print("🤖 Запускаю демонстрацию агентской системы для заказа еды")
    print("="*60)
    
    # Initialize LLM service with configuration
    api_key = None
    if config.LLM_PROVIDER == "openai":
        api_key = config.OPENAI_API_KEY
    elif config.LLM_PROVIDER == "anthropic":
        api_key = config.ANTHROPIC_API_KEY
    elif config.LLM_PROVIDER == "gemini":
        api_key = config.GEMINI_API_KEY
    
    llm_service = LLMService(
        model=config.LLM_MODEL,
        api_key=api_key,
        provider=config.LLM_PROVIDER
    )
    
    # Configure the food ordering agent
    food_config = FoodOrderConfig(
        delivery_service_url=config.DEFAULT_DELIVERY_SERVICE_URL,
        favorite_items=["BBQ-бургер", "картошка фри"],
        preferred_restaurants=["BBQ Palace", "Мясная лавка"]
    )
    
    # Create the agent
    agent = FoodOrderingAgent(llm_service, food_config)
    
    # Example user request: "Закажи мне BBQ-бургер и картошку фри из того места, откуда я заказывал на прошлой неделе"
    print("📝 Пример запроса пользователя:")
    print('   "Закажи мне BBQ-бургер и картошку фри из того места, откуда я заказывал на прошлой неделе"')
    print()
    
    # Execute the task
    result = await agent.order_food(
        food_items=["BBQ-бургер", "картошка фри"],
        restaurant_hint="BBQ Palace" # Simulating knowledge of previous restaurant
    )
    
    print()
    print("="*60)
    print("📋 Результат выполнения задачи:")
    print(f"   Успех: {result['success']}")
    print(f"   Результат: {result['result']}")
    
    if result['success'] and 'order_summary' in result:
        print(f"   Заказ: {', '.join(result['order_summary'])}")


if __name__ == "__main__":
    asyncio.run(main())