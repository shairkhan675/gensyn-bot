#!/usr/bin/env python3
"""
Auto-Discovery Webhook Bot for Gensyn
Automatically registers and manages VPS with zero configuration
"""

import os
import sys
import json
import time
import threading
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add current directory to path
sys.path.append('/root/gensyn-bot')

from webhook_server import WebhookServer
from webhook_client import WebhookClient

class AutoDiscoveryBot:
    def __init__(self):
        self.config_file = "/root/gensyn-bot/auto_config.json"
        self.config = self.load_config()
        
        if not self.config:
            print("❌ No auto-configuration found. Please run auto_setup.py first.")
            sys.exit(1)
        
        # Initialize components
        self.webhook_client = AutoDiscoveryClient(self.config)
        self.webhook_server = AutoDiscoveryServer(self.config)
        
        # Bot state
        self.running = False
        self.registration_attempts = 0
        self.max_registration_attempts = 10
        
        # Setup logging
        logging.basicConfig(
            filename='/root/auto_webhook_bot.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        print(f"🤖 Auto-Discovery Bot initialized for VPS: {self.config['vps_name']}")
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load auto-configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load config: {str(e)}")
        return None
    
    def ensure_registration(self):
        """Continuously ensure VPS is registered with n8n"""
        while self.running:
            try:
                if self.config.get('registration_status') != 'approved':
                    if self.registration_attempts < self.max_registration_attempts:
                        success = self.attempt_registration()
                        if success:
                            self.config['registration_status'] = 'approved'
                            self.save_config()
                        else:
                            self.registration_attempts += 1
                            wait_time = min(300, 30 * (2 ** self.registration_attempts))  # Exponential backoff
                            self.logger.info(f"Registration failed, waiting {wait_time}s before retry {self.registration_attempts}/{self.max_registration_attempts}")
                            time.sleep(wait_time)
                    else:
                        self.logger.error("Max registration attempts reached, will retry in 1 hour")
                        time.sleep(3600)
                        self.registration_attempts = 0
                else:
                    # Send heartbeat every 5 minutes
                    self.send_heartbeat()
                    time.sleep(300)
                    
            except Exception as e:
                self.logger.error(f"Registration loop error: {str(e)}")
                time.sleep(60)
    
    def attempt_registration(self) -> bool:
        """Attempt to register with n8n server"""
        try:
            registration_data = {
                'message_type': 'vps_registration',
                'vps_id': self.config['vps_id'],
                'vps_name': self.config['vps_name'],
                'vps_uuid': self.config['vps_uuid'],
                'auth_token': self.config['auth_token'],
                'webhook_url': f"http://{self.get_public_ip()}:{self.config['webhook_port']}/webhook/command",
                'system_info': self.config['system_info'],
                'capabilities': self.get_current_capabilities(),
                'setup_time': self.config['setup_time'],
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'data': {
                    'registration_attempt': self.registration_attempts + 1,
                    'public_ip': self.get_public_ip(),
                    'local_time': datetime.now().isoformat(),
                    'uptime': self.get_uptime()
                }
            }
            
            response = requests.post(
                self.config['registration_endpoint'],
                json=registration_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'approved':
                    self.logger.info("VPS registration approved!")
                    return True
                else:
                    self.logger.info(f"Registration pending: {result.get('message', 'waiting for approval')}")
                    return False
            else:
                self.logger.warning(f"Registration failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Registration attempt failed: {str(e)}")
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to maintain registration"""
        try:
            heartbeat_data = {
                'message_type': 'heartbeat',
                'vps_id': self.config['vps_id'],
                'vps_name': self.config['vps_name'],
                'auth_token': self.config['auth_token'],
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'data': {
                    'uptime': self.get_uptime(),
                    'system_info': self.get_system_metrics(),
                    'status': 'online',
                    'capabilities': self.get_current_capabilities(),
                    'last_activity': datetime.utcnow().isoformat() + "Z"
                }
            }
            
            response = requests.post(
                self.config['status_endpoint'],
                json=heartbeat_data,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.debug("Heartbeat sent successfully")
            else:
                self.logger.warning(f"Heartbeat failed with status {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Heartbeat failed: {str(e)}")
    
    def get_public_ip(self) -> str:
        """Get current public IP"""
        try:
            response = requests.get('https://api.ipify.org', timeout=10)
            return response.text.strip()
        except:
            return self.config.get('last_known_ip', '127.0.0.1')
    
    def get_uptime(self) -> str:
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                hours = uptime_seconds / 3600
                return f"{hours:.1f}h"
        except:
            return "unknown"
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            import psutil
            return {
                'cpu_percent': round(psutil.cpu_percent(interval=1), 1),
                'memory_percent': round(psutil.virtual_memory().percent, 1),
                'disk_percent': round(psutil.disk_usage('/').percent, 1),
                'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_current_capabilities(self) -> Dict[str, Any]:
        """Get current VPS capabilities"""
        capabilities = {
            'gensyn': os.path.exists('/root/rl-swarm'),
            'vpn': os.path.exists('/etc/wireguard/wg0.conf'),
            'gensyn_running': self.check_gensyn_running(),
            'vpn_active': self.check_vpn_active(),
            'auto_discovery': True,
            'monitoring': True,
            'webhook_server': True,
            'commands': [
                'check_ip', 'vpn_on', 'vpn_off', 'gensyn_status', 
                'start_gensyn', 'kill_gensyn', 'get_logs',
                'soft_update', 'hard_update', 'get_backup_files',
                'system_status', 'restart_services'
            ]
        }
        
        return capabilities
    
    def check_gensyn_running(self) -> bool:
        """Check if Gensyn is currently running"""
        try:
            import subprocess
            result = subprocess.run("screen -ls", shell=True, capture_output=True, text=True)
            return "gensyn" in result.stdout
        except:
            return False
    
    def check_vpn_active(self) -> bool:
        """Check if VPN is currently active"""
        try:
            import subprocess
            result = subprocess.run("wg show", shell=True, capture_output=True, text=True)
            return result.returncode == 0 and "wg0" in result.stdout
        except:
            return False
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
    
    def setup_monitoring(self):
        """Set up system monitoring"""
        def monitor_loop():
            last_ip = None
            last_gensyn_status = None
            last_vpn_status = None
            
            while self.running:
                try:
                    # Check for IP changes
                    current_ip = self.get_public_ip()
                    if last_ip and current_ip != last_ip:
                        self.webhook_client.send_notification(
                            'ip_change',
                            f"IP changed from {last_ip} to {current_ip}",
                            'normal'
                        )
                    last_ip = current_ip
                    
                    # Check for Gensyn status changes
                    gensyn_running = self.check_gensyn_running()
                    if last_gensyn_status is not None and gensyn_running != last_gensyn_status:
                        status = "started" if gensyn_running else "stopped"
                        self.webhook_client.send_notification(
                            'gensyn_status_change',
                            f"Gensyn {status}",
                            'high'
                        )
                    last_gensyn_status = gensyn_running
                    
                    # Check for VPN status changes
                    vpn_active = self.check_vpn_active()
                    if last_vpn_status is not None and vpn_active != last_vpn_status:
                        status = "connected" if vpn_active else "disconnected"
                        self.webhook_client.send_notification(
                            'vpn_status_change',
                            f"VPN {status}",
                            'high'
                        )
                    last_vpn_status = vpn_active
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    self.logger.error(f"Monitoring error: {str(e)}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        self.logger.info("System monitoring started")
    
    def run(self):
        """Run the auto-discovery bot"""
        print(f"🚀 Starting Auto-Discovery Bot for {self.config['vps_name']}")
        print(f"📍 VPS ID: {self.config['vps_id']}")
        print(f"🌐 n8n Server: {self.config['n8n_server']}")
        print(f"🔌 Webhook Port: {self.config['webhook_port']}")
        
        self.running = True
        
        # Start webhook server in background
        server_thread = threading.Thread(
            target=lambda: self.webhook_server.run(port=self.config['webhook_port']),
            daemon=True
        )
        server_thread.start()
        
        # Start monitoring
        self.setup_monitoring()
        
        # Start registration loop
        registration_thread = threading.Thread(target=self.ensure_registration, daemon=True)
        registration_thread.start()
        
        print("✅ All systems started!")
        print("📊 Status:")
        print(f"   • Registration: {self.config.get('registration_status', 'unknown')}")
        print(f"   • Webhook Server: Running on port {self.config['webhook_port']}")
        print(f"   • Monitoring: Active")
        print(f"   • Auto-Discovery: Enabled")
        print("\n💡 This VPS will automatically appear in your Telegram bot!")
        print("🔍 Monitor logs: tail -f /root/auto_webhook_bot.log")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Auto-Discovery Bot...")
            self.running = False
            
            # Send offline notification
            try:
                offline_data = {
                    'message_type': 'vps_offline',
                    'vps_id': self.config['vps_id'],
                    'vps_name': self.config['vps_name'],
                    'auth_token': self.config['auth_token'],
                    'timestamp': datetime.utcnow().isoformat() + "Z",
                    'data': {'reason': 'manual_shutdown'}
                }
                
                requests.post(
                    self.config['status_endpoint'],
                    json=offline_data,
                    timeout=10
                )
            except:
                pass
            
            print("✅ Auto-Discovery Bot stopped")

class AutoDiscoveryClient(WebhookClient):
    """Enhanced webhook client with auto-discovery features"""
    
    def __init__(self, config: Dict[str, Any]):
        self.auto_config = config
        # Create a minimal webhook config for the parent class
        webhook_config = {
            'webhook_url': config['status_endpoint'],
            'vps_name': config['vps_name'],
            'vps_id': config['vps_id'],
            'auth_token': config['auth_token'],
            'enabled': True
        }
        
        # Save webhook config for compatibility
        with open('/root/gensyn-bot/webhook_config.json', 'w') as f:
            json.dump(webhook_config, f, indent=2)
        
        super().__init__()

class AutoDiscoveryServer(WebhookServer):
    """Enhanced webhook server with auto-discovery features"""
    
    def __init__(self, config: Dict[str, Any]):
        self.auto_config = config
        super().__init__()
        
        # Register auto-discovery specific commands
        self.register_auto_discovery_commands()
    
    def register_auto_discovery_commands(self):
        """Register additional commands for auto-discovery"""
        
        def system_status(params: Dict[str, Any]) -> str:
            """Get comprehensive system status"""
            try:
                import psutil
                
                status = {
                    'vps_name': self.auto_config['vps_name'],
                    'vps_id': self.auto_config['vps_id'],
                    'uptime': self.get_uptime(),
                    'system_metrics': {
                        'cpu_percent': psutil.cpu_percent(interval=1),
                        'memory_percent': psutil.virtual_memory().percent,
                        'disk_percent': psutil.disk_usage('/').percent,
                        'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
                    },
                    'services': {
                        'gensyn_running': self.check_gensyn_running(),
                        'vpn_active': self.check_vpn_active(),
                        'webhook_server': True
                    },
                    'network': {
                        'public_ip': self.get_public_ip(),
                        'vpn_ip': self.get_vpn_ip()
                    }
                }
                
                return json.dumps(status, indent=2)
                
            except Exception as e:
                return f"Error getting system status: {str(e)}"
        
        def restart_services(params: Dict[str, Any]) -> str:
            """Restart specified services"""
            service = params.get('service', 'all')
            
            try:
                if service == 'gensyn' or service == 'all':
                    # Restart Gensyn
                    os.system("screen -S gensyn -X quit")
                    time.sleep(2)
                    os.system("cd /root/rl-swarm && screen -dmS gensyn bash -c 'python3 -m venv .venv && source .venv/bin/activate && ./run_rl_swarm.sh'")
                
                if service == 'vpn' or service == 'all':
                    # Restart VPN
                    os.system("wg-quick down wg0")
                    time.sleep(1)
                    os.system("wg-quick up wg0")
                
                return f"Services restarted: {service}"
                
            except Exception as e:
                return f"Error restarting services: {str(e)}"
        
        # Register commands
        self.register_command_handler("system_status", system_status)
        self.register_command_handler("restart_services", restart_services)
    
    def get_uptime(self) -> str:
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                hours = uptime_seconds / 3600
                return f"{hours:.1f}h"
        except:
            return "unknown"
    
    def check_gensyn_running(self) -> bool:
        """Check if Gensyn is running"""
        try:
            import subprocess
            result = subprocess.run("screen -ls", shell=True, capture_output=True, text=True)
            return "gensyn" in result.stdout
        except:
            return False
    
    def check_vpn_active(self) -> bool:
        """Check if VPN is active"""
        try:
            import subprocess
            result = subprocess.run("wg show", shell=True, capture_output=True, text=True)
            return result.returncode == 0 and "wg0" in result.stdout
        except:
            return False
    
    def get_public_ip(self) -> str:
        """Get public IP"""
        try:
            import requests
            response = requests.get('https://api.ipify.org', timeout=5)
            return response.text.strip()
        except:
            return "unknown"
    
    def get_vpn_ip(self) -> str:
        """Get VPN IP if available"""
        try:
            import subprocess
            result = subprocess.run("ip addr show wg0", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'inet ' in line:
                        return line.split()[1].split('/')[0]
        except:
            pass
        return "no_vpn"

def main():
    """Main entry point"""
    if os.geteuid() != 0:
        print("❌ This script must be run as root")
        sys.exit(1)
    
    try:
        bot = AutoDiscoveryBot()
        bot.run()
    except Exception as e:
        print(f"❌ Bot failed to start: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
