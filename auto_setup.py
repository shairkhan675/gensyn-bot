#!/usr/bin/env python3
"""
Automated Setup for Gensyn Bot - Zero Configuration Required
This script automatically configures everything for non-technical users
"""

import os
import sys
import json
import time
import requests
import secrets
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

class AutoSetup:
    def __init__(self):
        self.config = {}
        self.setup_dir = "/root/gensyn-bot"
        self.config_file = f"{self.setup_dir}/auto_config.json"
        
    def print_banner(self):
        print("""
╔══════════════════════════════════════════════════════════════╗
║                 🤖 GENSYN BOT AUTO SETUP                     ║
║              Zero Configuration Required!                    ║
╚══════════════════════════════════════════════════════════════╝

🎯 This will automatically:
   ✓ Configure your VPS for webhook communication
   ✓ Register with the central n8n server
   ✓ Enable auto-discovery for seamless management
   ✓ Set up monitoring and alerts

📋 You only need to provide:
   • n8n Server URL (where your central hub is)
   • VPS Name (friendly name for this server)

🚀 Everything else is handled automatically!
""")

    def get_user_input(self) -> bool:
        """Get minimal input from user"""
        print("📝 Quick Setup (2 questions only):")
        print("-" * 50)
        
        # Get n8n server URL
        while True:
            n8n_url = input("🌐 Enter your n8n server URL (e.g., https://n8n.yourdomain.com): ").strip()
            if self.validate_n8n_url(n8n_url):
                self.config['n8n_server'] = n8n_url.rstrip('/')
                break
            print("❌ Invalid URL. Please enter a valid https:// URL")
        
        # Get VPS name
        while True:
            vps_name = input("🏷️  Enter a name for this VPS (e.g., 'London Server', 'VPS-1'): ").strip()
            if len(vps_name) >= 2:
                self.config['vps_name'] = vps_name
                self.config['vps_id'] = vps_name.lower().replace(' ', '-').replace('_', '-')
                break
            print("❌ Please enter a name with at least 2 characters")
        
        return True
    
    def validate_n8n_url(self, url: str) -> bool:
        """Validate n8n server URL"""
        if not url.startswith(('http://', 'https://')):
            return False
        
        try:
            # Test if n8n server is reachable
            response = requests.get(f"{url}/healthz", timeout=10)
            return True
        except:
            # If /healthz fails, try base URL
            try:
                response = requests.get(url, timeout=10)
                return response.status_code < 500
            except:
                return False
    
    def auto_configure(self) -> bool:
        """Automatically configure everything"""
        print("\n🔧 Auto-configuring system...")
        
        # Generate unique identifiers
        self.config['vps_uuid'] = secrets.token_hex(16)
        self.config['auth_token'] = secrets.token_urlsafe(32)
        self.config['setup_time'] = datetime.utcnow().isoformat() + "Z"
        
        # Auto-detect system info
        self.config['system_info'] = self.get_system_info()
        
        # Set webhook endpoints
        self.config['registration_endpoint'] = f"{self.config['n8n_server']}/webhook/gensyn/register"
        self.config['status_endpoint'] = f"{self.config['n8n_server']}/webhook/gensyn/status"
        
        # Auto-select available port
        self.config['webhook_port'] = self.find_available_port()
        
        print(f"✓ Generated unique VPS ID: {self.config['vps_id']}")
        print(f"✓ Generated secure auth token: {self.config['auth_token'][:10]}...")
        print(f"✓ Selected port: {self.config['webhook_port']}")
        print(f"✓ Detected system: {self.config['system_info']['os']} with {self.config['system_info']['cpu_cores']} CPU cores")
        
        return True
    
    def get_system_info(self) -> Dict[str, Any]:
        """Auto-detect system information"""
        import platform
        import psutil
        
        try:
            return {
                'os': platform.system(),
                'os_version': platform.release(),
                'architecture': platform.machine(),
                'cpu_cores': psutil.cpu_count(),
                'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 1),
                'hostname': platform.node(),
                'python_version': platform.python_version()
            }
        except Exception as e:
            return {
                'os': 'Unknown',
                'error': str(e)
            }
    
    def find_available_port(self, start_port: int = 8080) -> int:
        """Find an available port automatically"""
        import socket
        
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        
        return 8080  # Fallback
    
    def register_with_n8n(self) -> bool:
        """Automatically register this VPS with n8n server"""
        print("\n📡 Registering with central server...")
        
        registration_data = {
            'vps_id': self.config['vps_id'],
            'vps_name': self.config['vps_name'],
            'vps_uuid': self.config['vps_uuid'],
            'auth_token': self.config['auth_token'],
            'webhook_url': f"http://{self.get_public_ip()}:{self.config['webhook_port']}/webhook/command",
            'system_info': self.config['system_info'],
            'setup_time': self.config['setup_time'],
            'capabilities': self.get_capabilities(),
            'status': 'registering'
        }
        
        try:
            response = requests.post(
                self.config['registration_endpoint'],
                json=registration_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.config['registration_status'] = 'approved'
                self.config['n8n_admin_chat_id'] = result.get('admin_chat_id')
                print("✅ Successfully registered with central server!")
                print(f"✓ Admin will be notified of new VPS: {self.config['vps_name']}")
                return True
            else:
                print(f"⚠️  Registration pending approval (status: {response.status_code})")
                self.config['registration_status'] = 'pending'
                return True
                
        except Exception as e:
            print(f"❌ Registration failed: {str(e)}")
            print("🔄 VPS will continue trying to register automatically...")
            self.config['registration_status'] = 'failed'
            return False
    
    def get_public_ip(self) -> str:
        """Get public IP address"""
        try:
            response = requests.get('https://api.ipify.org', timeout=10)
            return response.text.strip()
        except:
            return '127.0.0.1'  # Fallback
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Auto-detect what this VPS can do"""
        capabilities = {
            'gensyn': os.path.exists('/root/rl-swarm'),
            'vpn': os.path.exists('/etc/wireguard/wg0.conf'),
            'docker': self.command_exists('docker'),
            'screen': self.command_exists('screen'),
            'auto_discovery': True,
            'monitoring': True,
            'commands': [
                'check_ip', 'vpn_on', 'vpn_off', 'gensyn_status', 
                'start_gensyn', 'kill_gensyn', 'get_logs',
                'soft_update', 'hard_update', 'get_backup_files'
            ]
        }
        
        return capabilities
    
    def command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except:
            return False
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            # Also save in webhook config format for compatibility
            webhook_config = {
                'webhook_url': self.config['status_endpoint'],
                'vps_name': self.config['vps_name'],
                'vps_id': self.config['vps_id'],
                'auth_token': self.config['auth_token'],
                'webhook_port': self.config['webhook_port'],
                'enabled': True,
                'auto_configured': True,
                'n8n_server': self.config['n8n_server']
            }
            
            with open('/root/gensyn-bot/webhook_config.json', 'w') as f:
                json.dump(webhook_config, f, indent=2)
                
            print(f"✓ Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save configuration: {str(e)}")
            return False
    
    def setup_auto_start(self) -> bool:
        """Set up automatic startup"""
        print("\n⚙️ Setting up automatic startup...")
        
        try:
            # Create systemd service
            service_content = f"""[Unit]
Description=Gensyn Auto-Discovery Bot
After=network.target
StartLimitInterval=0

[Service]
Type=simple
Restart=always
RestartSec=10
User=root
WorkingDirectory=/root/gensyn-bot
ExecStart=/root/gensyn-bot/.venv/bin/python3 /root/gensyn-bot/auto_webhook_bot.py
Environment=PYTHONPATH=/root/gensyn-bot

[Install]
WantedBy=multi-user.target
"""
            
            with open('/etc/systemd/system/gensyn-auto-bot.service', 'w') as f:
                f.write(service_content)
            
            # Enable and start service
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', 'gensyn-auto-bot'], check=True)
            
            print("✓ Auto-start service created and enabled")
            return True
            
        except Exception as e:
            print(f"⚠️  Auto-start setup failed: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test connection to n8n server"""
        print("\n🧪 Testing connection...")
        
        try:
            test_data = {
                'message_type': 'test_connection',
                'vps_id': self.config['vps_id'],
                'vps_name': self.config['vps_name'],
                'auth_token': self.config['auth_token'],
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'data': {'test': True}
            }
            
            response = requests.post(
                self.config['status_endpoint'],
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Connection test successful!")
                return True
            else:
                print(f"⚠️  Connection test returned status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            return False
    
    def run(self) -> bool:
        """Run the complete auto-setup process"""
        try:
            self.print_banner()
            
            if not self.get_user_input():
                return False
            
            if not self.auto_configure():
                return False
            
            if not self.save_config():
                return False
            
            # Try to register (don't fail if this doesn't work)
            self.register_with_n8n()
            
            if not self.setup_auto_start():
                print("⚠️  Manual start will be required")
            
            self.test_connection()
            
            print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🎉 SETUP COMPLETE!                        ║
╚══════════════════════════════════════════════════════════════╝

✅ Your VPS is now configured for auto-discovery!

📊 Configuration Summary:
   • VPS Name: {self.config['vps_name']}
   • VPS ID: {self.config['vps_id']}
   • Webhook Port: {self.config['webhook_port']}
   • n8n Server: {self.config['n8n_server']}
   • Status: {self.config.get('registration_status', 'configured')}

🚀 Starting the bot now...
   • Auto-discovery enabled
   • Will appear automatically in your Telegram bot
   • No further configuration needed!

🔧 Manual Controls:
   • Start: systemctl start gensyn-auto-bot
   • Stop: systemctl stop gensyn-auto-bot  
   • Status: systemctl status gensyn-auto-bot
   • Logs: journalctl -u gensyn-auto-bot -f

💡 The VPS will automatically:
   ✓ Register with your central server
   ✓ Send status updates and heartbeats
   ✓ Respond to commands from Telegram
   ✓ Monitor system health
   ✓ Handle Gensyn operations

🎯 Ready! Check your Telegram bot - this VPS should appear shortly!
""")
            
            # Auto-start the bot
            try:
                subprocess.run(['systemctl', 'start', 'gensyn-auto-bot'], check=True)
                print("✅ Bot started successfully!")
                print("🔍 Use 'journalctl -u gensyn-auto-bot -f' to view logs")
            except Exception as e:
                print(f"⚠️  Auto-start failed, starting manually...")
                # Fallback to manual start
                subprocess.Popen([
                    '/root/gensyn-bot/.venv/bin/python3', 
                    '/root/gensyn-bot/auto_webhook_bot.py'
                ], cwd='/root/gensyn-bot')
                print("✅ Bot started in background!")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n🛑 Setup cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Setup failed: {str(e)}")
            return False

def main():
    """Main entry point"""
    if os.geteuid() != 0:
        print("❌ This script must be run as root: sudo python3 auto_setup.py")
        sys.exit(1)
    
    if not os.path.exists('/root/gensyn-bot'):
        print("❌ Please run this from the gensyn-bot directory")
        sys.exit(1)
    
    setup = AutoSetup()
    success = setup.run()
    
    if success:
        print("\n🎉 All done! Your VPS is now part of the multi-VPS network!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
