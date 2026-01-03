import asyncio
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field
import getpass


class SecurityConfig(BaseModel):
    """Configuration for security features"""
    enable_hitl: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    sensitive_actions: list = Field(default_factory=list)  # Actions that require confirmation
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.sensitive_actions:
            self.sensitive_actions = [
                "payment", "purchase", "checkout", "login",
                "delete", "remove", "cancel", "2fa", "captcha"
            ]


class HumanInTheLoop:
    """Handles human intervention in automated processes"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.pending_confirmation = {}
    
    async def request_confirmation(
        self,
        action: str,
        details: Dict[str, Any],
        timeout: int | None = None
    ) -> bool:
        """
        Request human confirmation for sensitive actions
        """
        if timeout is None:
            timeout = self.config.timeout_seconds
            
        print(f"\n⚠️  SECURITY ALERT: Action requires confirmation")
        print(f"Action: {action}")
        print(f"Details: {details}")
        
        try:
            # Use asyncio.wait_for to implement timeout
            confirmation = await asyncio.wait_for(
                self._get_user_input_async(f"Allow this action? (y/n): "),
                timeout=timeout
            )
            return confirmation.lower() in ['y', 'yes', 'true', '1']
        except asyncio.TimeoutError:
            print(f"\n⏰ Timeout: No response within {timeout} seconds")
            return False
    
    async def _get_user_input_async(self, prompt: str) -> str:
        """Get user input asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)
    
    async def handle_2fa_request(self) -> str | None:
        """
        Handle 2FA code input from user
        """
        print("\n🔒 Two-factor authentication required")
        try:
            code = await asyncio.wait_for(
                self._get_user_input_async("Enter 2FA code: "),
                timeout=self.config.timeout_seconds
            )
            return code.strip()
        except asyncio.TimeoutError:
            print(f"\n⏰ Timeout: 2FA code not provided within {self.config.timeout_seconds} seconds")
            return None
    
    async def handle_captcha_request(self, captcha_info: Dict[str, Any]) -> str | None:
        """
        Handle CAPTCHA solving request
        """
        print(f"\n🔒 CAPTCHA challenge detected")
        print(f"CAPTCHA type: {captcha_info.get('type', 'unknown')}")
        
        if captcha_info.get('image_url'):
            print(f"CAPTCHA image: {captcha_info['image_url']}")
        
        try:
            solution = await asyncio.wait_for(
                self._get_user_input_async("Enter CAPTCHA solution: "),
                timeout=self.config.timeout_seconds
            )
            return solution.strip()
        except asyncio.TimeoutError:
            print(f"\n⏰ Timeout: CAPTCHA not solved within {self.config.timeout_seconds} seconds")
            return None
    
    async def handle_sensitive_action(
        self,
        action: str,
        details: Dict[str, Any]
    ) -> bool:
        """
        Handle any sensitive action that requires human approval
        """
        if not self.config.enable_hitl:
            return True  # Skip confirmation if HITL is disabled
            
        # Check if action is sensitive
        is_sensitive = any(sensitive in action.lower() for sensitive in self.config.sensitive_actions)
        
        if is_sensitive:
            return await self.request_confirmation(action, details)
        
        return True


class CredentialManager:
    """Secure credential management"""
    
    def __init__(self):
        self._credentials = {}
        self._encrypted_storage = True
    
    def store_credential(self, service: str, username: str, password: str):
        """
        Store credentials securely
        In a real implementation, this would encrypt the credentials
        """
        # For now, just store in memory
        # In production, use proper encryption and secure storage
        self._credentials[service] = {
            'username': username,
            'password': self._encrypt_password(password)  # Simplified
        }
    
    def get_credential(self, service: str) -> Dict[str, str] | None:
        """
        Retrieve credentials for a service
        """
        if service in self._credentials:
            cred = self._credentials[service]
            return {
                'username': cred['username'],
                'password': self._decrypt_password(cred['password'])
            }
        return None
    
    def _encrypt_password(self, password: str) -> str:
        """
        Encrypt password (simplified for example)
        In production, use proper encryption like AES
        """
        # This is a placeholder - use proper encryption in production
        return f"encrypted_{password}"  # Don't do this in production!
    
    def _decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt password (simplified for example)
        In production, use proper decryption
        """
        # This is a placeholder - use proper decryption in production
        return encrypted_password.replace("encrypted_", "")  # Don't do this in production!


class SecurityManager:
    """Main security manager combining all security features"""
    
    def __init__(self, config: SecurityConfig | None = None):
        if config is None:
            config = SecurityConfig()
        self.config = config
        self.hitl = HumanInTheLoop(config)
        self.credential_manager = CredentialManager()
        self.action_history = []
    
    async def check_action_allowed(
        self,
        action: str,
        details: Dict[str, Any] | None = None
    ) -> bool:
        """
        Check if an action is allowed based on security policies
        """
        if details is None:
            details = {}
        
        # Add action to history
        self.action_history.append({
            'action': action,
            'details': details,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        # Handle sensitive actions
        return await self.hitl.handle_sensitive_action(action, details)
    
    async def handle_authentication_challenge(
        self,
        challenge_type: str,
        challenge_details: Dict[str, Any] | None = None
    ) -> str | None:
        """
        Handle various authentication challenges
        """
        if challenge_type.lower() == '2fa':
            return await self.hitl.handle_2fa_request()
        elif challenge_type.lower() == 'captcha':
            return await self.hitl.handle_captcha_request(challenge_details or {})
        else:
            print(f"Unknown challenge type: {challenge_type}")
            return None
    
    def store_credentials(self, service: str, username: str, password: str):
        """
        Store credentials securely
        """
        self.credential_manager.store_credential(service, username, password)
    
    def get_credentials(self, service: str) -> Dict[str, str] | None:
        """
        Retrieve credentials for a service
        """
        return self.credential_manager.get_credential(service)
    
    async def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """
        Log security-related events
        """
        print(f"🔒 Security Event: {event_type}")
        print(f"Details: {details}")
        
        # In production, log to secure logging system
        # This is where you'd integrate with your logging infrastructure


# Example usage:
async def example_usage():
    # Create security manager
    security = SecurityManager()
    
    # Test sensitive action handling
    action_allowed = await security.check_action_allowed(
        "purchase",
        {"item": "laptop", "amount": 1000}
    )
    print(f"Action allowed: {action_allowed}")
    
    # Test credential management
    security.store_credentials("example.com", "user123", "password123")
    creds = security.get_credentials("example.com")
    print(f"Retrieved credentials: {creds}")


if __name__ == "__main__":
    asyncio.run(example_usage())