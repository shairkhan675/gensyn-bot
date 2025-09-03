#!/usr/bin/env python3
"""
Webhook Client for Gensyn Bot
Handles sending status updates, notifications, and logs to the n8n server
"""

import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from webhook_config import WebhookConfig

class WebhookClient:
    def __init__(self, config_file: Optional[str] = None):
        self.config_manager = WebhookConfig()
        self.config = self.config_manager.get_config()
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Setup logging
        logging.basicConfig(
            filename='/root/webhook_client.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def is_enabled(self) -> bool:
        """Check if webhook client is enabled and configured"""
        return self.config_manager.is_configured()
    
    def _prepare_payload(self, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the webhook payload with VPS info and authentication"""
        vps_info = self.config_manager.get_vps_info()
        
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message_type": message_type,
            "vps_name": vps_info["vps_name"],
            "vps_id": vps_info["vps_id"],
            "auth_token": vps_info["auth_token"],
            "data": data
        }
        return payload
    
    def _send_webhook(self, payload: Dict[str, Any], retries: int = 3) -> bool:
        """Send webhook with retry logic"""
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            self.logger.error("Webhook URL not configured")
            return False
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"gensyn-bot-webhook/{self.config.get('vps_id', 'unknown')}"
        }
        
        for attempt in range(retries):
            try:
                response = self.session.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Webhook sent successfully: {payload['message_type']}")
                    return True
                else:
                    self.logger.warning(f"Webhook failed with status {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.logger.error(f"Webhook send error (attempt {attempt + 1}): {str(e)}")
                
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        self.logger.error(f"Failed to send webhook after {retries} attempts")
        return False
    
    def send_status_update(self, status_data: Dict[str, Any]) -> bool:
        """Send general status update"""
        if not self.is_enabled():
            return False
            
        payload = self._prepare_payload("status_update", status_data)
        return self._send_webhook(payload)
    
    def send_gensyn_status(self, gensyn_data: Dict[str, Any]) -> bool:
        """Send Gensyn-specific status"""
        if not self.is_enabled():
            return False
            
        payload = self._prepare_payload("gensyn_status", gensyn_data)
        return self._send_webhook(payload)
    
    def send_notification(self, notification_type: str, message: str, priority: str = "normal") -> bool:
        """Send notification message"""
        if not self.is_enabled():
            return False
            
        data = {
            "notification_type": notification_type,
            "message": message,
            "priority": priority
        }
        payload = self._prepare_payload("notification", data)
        return self._send_webhook(payload)
    
    def send_reward_update(self, reward_data: Dict[str, Any]) -> bool:
        """Send reward/win update"""
        if not self.is_enabled():
            return False
            
        payload = self._prepare_payload("reward_update", reward_data)
        return self._send_webhook(payload)
    
    def send_error_alert(self, error_type: str, error_message: str, context: Dict[str, Any] = None) -> bool:
        """Send error alert"""
        if not self.is_enabled():
            return False
            
        data = {
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        payload = self._prepare_payload("error_alert", data)
        return self._send_webhook(payload)
    
    def send_command_response(self, command: str, success: bool, result: str, execution_time: float = None) -> bool:
        """Send command execution response"""
        if not self.is_enabled():
            return False
            
        data = {
            "command": command,
            "success": success,
            "result": result,
            "execution_time": execution_time
        }
        payload = self._prepare_payload("command_response", data)
        return self._send_webhook(payload)
    
    def send_log_update(self, log_type: str, log_data: str, level: str = "info") -> bool:
        """Send log update"""
        if not self.is_enabled():
            return False
            
        data = {
            "log_type": log_type,
            "log_data": log_data,
            "level": level
        }
        payload = self._prepare_payload("log_update", data)
        return self._send_webhook(payload)
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to indicate VPS is alive"""
        if not self.is_enabled():
            return False
            
        data = {
            "uptime": self._get_uptime(),
            "system_info": self._get_system_info()
        }
        payload = self._prepare_payload("heartbeat", data)
        return self._send_webhook(payload)
    
    def _get_uptime(self) -> str:
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                uptime_hours = uptime_seconds / 3600
                return f"{uptime_hours:.1f}h"
        except:
            return "unknown"
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        except:
            return {}

# Example usage and testing
def test_webhook_client():
    """Test function for webhook client"""
    client = WebhookClient()
    
    if not client.is_enabled():
        print("❌ Webhook not configured. Run webhook_config.py first.")
        return
    
    print("🧪 Testing webhook client...")
    
    # Test heartbeat
    success = client.send_heartbeat()
    print(f"Heartbeat: {'✅' if success else '❌'}")
    
    # Test notification
    success = client.send_notification("test", "Webhook client test message")
    print(f"Notification: {'✅' if success else '❌'}")
    
    # Test status update
    status_data = {
        "api_status": "running",
        "vpn_status": "connected",
        "gensyn_running": True
    }
    success = client.send_status_update(status_data)
    print(f"Status Update: {'✅' if success else '❌'}")

if __name__ == "__main__":
    test_webhook_client()

