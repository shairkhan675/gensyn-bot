#!/usr/bin/env python3
"""
Webhook Configuration System for Gensyn Bot
Handles interactive setup for webhook URL, VPS name, and authentication token
"""

import os
import json
import secrets
from typing import Dict, Optional

# Configuration file paths
WEBHOOK_CONFIG_FILE = "/root/gensyn-bot/webhook_config.json"
BOT_CONFIG_FILE = "/root/bot_config.env"

class WebhookConfig:
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load existing webhook configuration or return defaults"""
        if os.path.exists(WEBHOOK_CONFIG_FILE):
            try:
                with open(WEBHOOK_CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "webhook_url": "",
            "vps_name": "",
            "vps_id": "",
            "auth_token": "",
            "webhook_port": 8080,
            "enabled": False
        }
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(WEBHOOK_CONFIG_FILE), exist_ok=True)
            with open(WEBHOOK_CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def generate_auth_token(self) -> str:
        """Generate a secure authentication token"""
        return secrets.token_urlsafe(32)
    
    def interactive_setup(self):
        """Interactive setup wizard for webhook configuration"""
        print("\n🔧 Gensyn Bot Webhook Configuration")
        print("=" * 50)
        
        # Check if already configured
        if self.config.get("enabled"):
            print(f"Current configuration:")
            print(f"  VPS Name: {self.config.get('vps_name', 'Not set')}")
            print(f"  VPS ID: {self.config.get('vps_id', 'Not set')}")
            print(f"  Webhook URL: {self.config.get('webhook_url', 'Not set')}")
            print(f"  Webhook Port: {self.config.get('webhook_port', 8080)}")
            print(f"  Auth Token: {'Set' if self.config.get('auth_token') else 'Not set'}")
            
            choice = input("\nReconfigure? (y/N): ").strip().lower()
            if choice != 'y':
                return True
        
        print("\n📋 Please provide the following information:")
        
        # Get VPS name/identifier
        while True:
            vps_name = input("VPS Name (e.g., 'vps-1', 'london-server'): ").strip()
            if vps_name and len(vps_name) >= 2:
                self.config["vps_name"] = vps_name
                # Auto-generate VPS ID from name (can be customized)
                self.config["vps_id"] = vps_name.lower().replace(" ", "-")
                break
            print("❌ Please enter a valid VPS name (at least 2 characters)")
        
        # Get webhook URL
        while True:
            webhook_url = input("n8n Webhook URL (e.g., 'https://your-n8n.domain.com/webhook/gensyn'): ").strip()
            if webhook_url.startswith(('http://', 'https://')) and len(webhook_url) > 10:
                self.config["webhook_url"] = webhook_url.rstrip('/')
                break
            print("❌ Please enter a valid webhook URL starting with http:// or https://")
        
        # Get webhook port for incoming commands
        port_input = input(f"Webhook listening port (default: {self.config.get('webhook_port', 8080)}): ").strip()
        if port_input.isdigit():
            port = int(port_input)
            if 1024 <= port <= 65535:
                self.config["webhook_port"] = port
            else:
                print("❌ Port must be between 1024-65535, using default")
        
        # Generate or reuse auth token
        if not self.config.get("auth_token"):
            self.config["auth_token"] = self.generate_auth_token()
            print(f"\n🔐 Generated authentication token: {self.config['auth_token']}")
            print("💡 Save this token - you'll need it in your n8n configuration!")
        else:
            print(f"\n🔐 Using existing authentication token: {self.config['auth_token']}")
        
        # Enable webhook mode
        self.config["enabled"] = True
        
        # Save configuration
        if self.save_config():
            print("\n✅ Webhook configuration saved successfully!")
            print(f"📍 VPS ID: {self.config['vps_id']}")
            print(f"🌐 Webhook URL: {self.config['webhook_url']}")
            print(f"🔌 Listening Port: {self.config['webhook_port']}")
            print("\n📋 Next steps:")
            print("1. Configure your n8n server with the webhook URL and auth token")
            print("2. Start the bot with: python webhook_bot.py")
            return True
        else:
            print("❌ Failed to save configuration")
            return False
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.config.copy()
    
    def is_configured(self) -> bool:
        """Check if webhook is properly configured"""
        required_fields = ["webhook_url", "vps_name", "vps_id", "auth_token"]
        return (
            self.config.get("enabled", False) and
            all(self.config.get(field) for field in required_fields)
        )
    
    def get_vps_info(self) -> Dict:
        """Get VPS identification info"""
        return {
            "vps_name": self.config.get("vps_name", ""),
            "vps_id": self.config.get("vps_id", ""),
            "auth_token": self.config.get("auth_token", "")
        }

def main():
    """Main function for standalone configuration"""
    config = WebhookConfig()
    
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--status":
        # Show current status
        if config.is_configured():
            print("✅ Webhook is configured and enabled")
            info = config.get_vps_info()
            print(f"   VPS Name: {info['vps_name']}")
            print(f"   VPS ID: {info['vps_id']}")
            print(f"   Webhook URL: {config.config['webhook_url']}")
        else:
            print("❌ Webhook is not configured")
            print("   Run without arguments to configure")
    else:
        # Interactive setup
        config.interactive_setup()

if __name__ == "__main__":
    main()

