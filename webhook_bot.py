#!/usr/bin/env python3
"""
Webhook-based Gensyn Bot
Main bot that uses webhooks for communication instead of direct Telegram polling
"""

import os
import time
import threading
import subprocess
import logging
import requests
import shutil
import json
import re
import html
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import original bot functions and classes we'll reuse
import sys
sys.path.append('/root/gensyn-bot')

# Import our webhook classes
from webhook_config import WebhookConfig
from webhook_client import WebhookClient
from webhook_server import WebhookServer

# Import reusable functions from original bot
try:
    from bot import (
        get_cached_peer_info, parse_peer_info_from_swarm_log, write_cached_peer_info,
        backup_user_data, backup_user_data_sync, run_command, install_gensyn,
        setup_autostart, gensyn_soft_update, gensyn_hard_update, send_backup_files,
        check_gensyn_screen_running, start_gensyn_session, get_gensyn_log_status,
        check_gensyn_api, format_gensyn_status, start_vpn, stop_vpn,
        # Constants
        BOT_CONFIG, WG_CONFIG_PATH, SWARM_PEM_PATH, USER_DATA_PATH, USER_APIKEY_PATH,
        BACKUP_USERDATA_DIR, SYNC_BACKUP_DIR, GENSYN_LOG_PATH, WANDB_LOG_DIR,
        PEER_CACHE_FILE
    )
except ImportError as e:
    logging.error(f"Failed to import from original bot: {e}")
    # Define fallback constants
    BOT_CONFIG = "/root/bot_config.env"
    WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"
    SWARM_PEM_PATH = "/root/rl-swarm/swarm.pem"
    USER_DATA_PATH = "/root/rl-swarm/modal-login/temp-data/userData.json"
    USER_APIKEY_PATH = "/root/rl-swarm/modal-login/temp-data/userApiKey.json"
    BACKUP_USERDATA_DIR = "/root/gensyn-bot/backup-userdata"
    SYNC_BACKUP_DIR = "/root/gensyn-bot/sync-backup"
    GENSYN_LOG_PATH = "/root/rl-swarm/logs/swarm_launcher.log"
    WANDB_LOG_DIR = "/root/rl-swarm/logs/wandb"
    PEER_CACHE_FILE = "/root/gensyn-bot/peer_info.json"

class WebhookBot:
    def __init__(self):
        # Initialize configuration and clients
        self.config_manager = WebhookConfig()
        self.webhook_client = WebhookClient()
        self.webhook_server = WebhookServer()
        
        # Bot state
        self.monitoring_active = False
        self.reward_monitoring_active = False
        self.monitor_thread = None
        self.reward_monitor_thread = None
        
        # Setup logging
        logging.basicConfig(
            filename='/root/webhook_bot.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Register additional command handlers
        self._register_custom_handlers()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [BACKUP_USERDATA_DIR, SYNC_BACKUP_DIR]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _register_custom_handlers(self):
        """Register custom command handlers with the webhook server"""
        
        def gensyn_login(params: Dict[str, Any]) -> str:
            """Handle Gensyn login process"""
            email = params.get("email")
            otp = params.get("otp")
            
            if not email and not otp:
                return "Email and OTP required for login"
            
            try:
                # Clear any previous state
                for path in ["/root/email.txt", "/root/otp.txt"]:
                    if os.path.exists(path):
                        os.remove(path)
                
                # Write credentials to files for signup.py to read
                if email:
                    with open("/root/email.txt", "w") as f:
                        f.write(email)
                
                if otp:
                    with open("/root/otp.txt", "w") as f:
                        f.write(otp)
                
                # Run signup script
                venv_python = "/root/gensyn-bot/.venv/bin/python3"
                signup_script = "/root/gensyn-bot/signup.py"
                venv_site_packages = "/root/gensyn-bot/.venv/lib/python3.12/site-packages"
                
                process = subprocess.Popen(
                    [venv_python, signup_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env={**os.environ, "PYTHONPATH": venv_site_packages}
                )
                
                # Wait for completion with timeout
                try:
                    stdout, _ = process.communicate(timeout=300)  # 5 minute timeout
                    if process.returncode == 0:
                        return "Login process completed successfully"
                    else:
                        return f"Login failed: {stdout.decode()}"
                except subprocess.TimeoutExpired:
                    process.kill()
                    return "Login process timed out"
                    
            except Exception as e:
                return f"Login error: {str(e)}"
        
        def set_autostart(params: Dict[str, Any]) -> str:
            """Setup autostart service"""
            try:
                # Use the original setup_autostart function but capture output
                import io
                from contextlib import redirect_stdout, redirect_stderr
                
                f = io.StringIO()
                with redirect_stdout(f), redirect_stderr(f):
                    setup_autostart(None)  # Pass None instead of chat_id
                
                output = f.getvalue()
                if "error" in output.lower() or "failed" in output.lower():
                    return f"Autostart setup failed: {output}"
                else:
                    return "Autostart configured successfully"
            except Exception as e:
                return f"Error setting up autostart: {str(e)}"
        
        def install_gensyn_cmd(params: Dict[str, Any]) -> str:
            """Install Gensyn prerequisites"""
            try:
                # Run installation in a separate thread to avoid blocking
                def install_worker():
                    install_gensyn(None)  # Pass None instead of chat_id
                
                install_thread = threading.Thread(target=install_worker)
                install_thread.start()
                install_thread.join(timeout=1800)  # 30 minute timeout
                
                if install_thread.is_alive():
                    return "Installation is taking longer than expected but is still running"
                else:
                    return "Installation completed"
            except Exception as e:
                return f"Installation error: {str(e)}"
        
        def toggle_monitoring(params: Dict[str, Any]) -> str:
            """Toggle system monitoring"""
            action = params.get("action", "toggle")
            
            if action == "start" or (action == "toggle" and not self.monitoring_active):
                self.start_monitoring()
                return "System monitoring started"
            else:
                self.stop_monitoring()
                return "System monitoring stopped"
        
        def toggle_reward_monitoring(params: Dict[str, Any]) -> str:
            """Toggle reward monitoring"""
            action = params.get("action", "toggle")
            
            if action == "start" or (action == "toggle" and not self.reward_monitoring_active):
                self.start_reward_monitoring()
                return "Reward monitoring started"
            else:
                self.stop_reward_monitoring()
                return "Reward monitoring stopped"
        
        def get_backup_files(params: Dict[str, Any]) -> str:
            """Get backup files info"""
            try:
                files_info = []
                backup_files = [SWARM_PEM_PATH, USER_DATA_PATH, USER_APIKEY_PATH]
                
                for file_path in backup_files:
                    if os.path.exists(file_path):
                        stat = os.stat(file_path)
                        files_info.append({
                            "file": os.path.basename(file_path),
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    else:
                        files_info.append({
                            "file": os.path.basename(file_path),
                            "status": "not found"
                        })
                
                return json.dumps(files_info, indent=2)
            except Exception as e:
                return f"Error getting backup info: {str(e)}"
        
        def soft_update(params: Dict[str, Any]) -> str:
            """Perform soft update of Gensyn"""
            try:
                def update_worker():
                    gensyn_soft_update(None)  # Pass None instead of chat_id
                
                update_thread = threading.Thread(target=update_worker)
                update_thread.start()
                update_thread.join(timeout=600)  # 10 minute timeout
                
                if update_thread.is_alive():
                    return "Soft update is taking longer than expected but is still running"
                else:
                    return "Soft update completed"
            except Exception as e:
                return f"Soft update error: {str(e)}"
        
        def hard_update(params: Dict[str, Any]) -> str:
            """Perform hard update of Gensyn"""
            try:
                def update_worker():
                    gensyn_hard_update(None)  # Pass None instead of chat_id
                
                update_thread = threading.Thread(target=update_worker)
                update_thread.start()
                update_thread.join(timeout=600)  # 10 minute timeout
                
                if update_thread.is_alive():
                    return "Hard update is taking longer than expected but is still running"
                else:
                    return "Hard update completed"
            except Exception as e:
                return f"Hard update error: {str(e)}"
        
        # Register all custom handlers
        self.webhook_server.register_command_handler("gensyn_login", gensyn_login)
        self.webhook_server.register_command_handler("set_autostart", set_autostart)
        self.webhook_server.register_command_handler("install_gensyn", install_gensyn_cmd)
        self.webhook_server.register_command_handler("toggle_monitoring", toggle_monitoring)
        self.webhook_server.register_command_handler("toggle_reward_monitoring", toggle_reward_monitoring)
        self.webhook_server.register_command_handler("get_backup_files", get_backup_files)
        self.webhook_server.register_command_handler("soft_update", soft_update)
        self.webhook_server.register_command_handler("hard_update", hard_update)
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        # Start periodic sync backup
        def periodic_sync_backup():
            while True:
                try:
                    backup_user_data_sync()
                    time.sleep(60)
                except Exception as e:
                    self.logger.error(f"Periodic sync backup error: {str(e)}")
                    time.sleep(10)
        
        threading.Thread(target=periodic_sync_backup, daemon=True).start()
        
        # Start heartbeat sender
        def send_heartbeat():
            while True:
                try:
                    if self.webhook_client.is_enabled():
                        self.webhook_client.send_heartbeat()
                    time.sleep(300)  # Send heartbeat every 5 minutes
                except Exception as e:
                    self.logger.error(f"Heartbeat error: {str(e)}")
                    time.sleep(60)
        
        threading.Thread(target=send_heartbeat, daemon=True).start()
    
    def start_monitoring(self):
        """Start system monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        def monitor():
            previous_ip = ''
            previous_alive = None
            wandb_file_cache = set()
            wandb_folder_cache = set()
            last_stale_sent_ts = None
            previous_localhost_alive = None
            
            while self.monitoring_active:
                try:
                    # 1. API status monitoring
                    alive = check_gensyn_api()
                    
                    # 1a. Localhost:3000 status
                    try:
                        response = requests.get("http://localhost:3000", timeout=3)
                        localhost_alive = "Sign in to Gensyn" in response.text
                    except Exception:
                        localhost_alive = False
                    
                    if previous_localhost_alive is not None and localhost_alive != previous_localhost_alive:
                        status = 'Online' if localhost_alive else 'Offline'
                        self.webhook_client.send_notification(
                            "status_change",
                            f"localhost:3000 status changed: {status}",
                            "high"
                        )
                    previous_localhost_alive = localhost_alive
                    
                    # 2. IP change monitoring
                    try:
                        ip = requests.get('https://api.ipify.org', timeout=10).text.strip()
                    except:
                        ip = "Unknown"
                    
                    if ip and ip != previous_ip:
                        self.webhook_client.send_notification(
                            "ip_change",
                            f"IP changed: {ip}",
                            "normal"
                        )
                        previous_ip = ip
                    
                    if previous_alive is not None and alive != previous_alive:
                        status = 'Online' if alive else 'Offline'
                        self.webhook_client.send_notification(
                            "api_status_change",
                            f"API status changed: {status}",
                            "high"
                        )
                    previous_alive = alive
                    
                    # 3. Log freshness monitoring
                    log_data = get_gensyn_log_status()
                    if log_data and log_data.get("timestamp"):
                        latest_ts = log_data["timestamp"]
                        if (datetime.utcnow() - latest_ts > timedelta(minutes=240)):
                            if not last_stale_sent_ts or last_stale_sent_ts != latest_ts:
                                self.webhook_client.send_notification(
                                    "stale_logs",
                                    f"No new Gensyn log entry since {latest_ts.strftime('%Y-%m-%d %H:%M:%S')} UTC (>4h ago)!",
                                    "high"
                                )
                                last_stale_sent_ts = latest_ts
                        else:
                            last_stale_sent_ts = None
                    
                    # 4. WANDB monitoring
                    new_folders = []
                    new_files = []
                    if os.path.exists(WANDB_LOG_DIR):
                        for root, dirs, files in os.walk(WANDB_LOG_DIR):
                            for d in dirs:
                                folder_path = os.path.join(root, d)
                                if folder_path not in wandb_folder_cache:
                                    wandb_folder_cache.add(folder_path)
                                    new_folders.append(folder_path)
                            for name in files:
                                path = os.path.join(root, name)
                                if path not in wandb_file_cache:
                                    wandb_file_cache.add(path)
                                    new_files.append(path)
                        
                        if new_folders or new_files:
                            self.webhook_client.send_notification(
                                "wandb_detected",
                                f"WANDB activity detected: {len(new_folders)} new folders, {len(new_files)} new files",
                                "normal"
                            )
                    
                    time.sleep(60)
                    
                except Exception as e:
                    self.logger.error(f"Monitor error: {str(e)}")
                    time.sleep(10)
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
    
    def start_reward_monitoring(self):
        """Start reward monitoring"""
        if self.reward_monitoring_active:
            return
        
        self.reward_monitoring_active = True
        
        def reward_monitor():
            last_reward = None
            last_win = None
            peer_name = None
            peer_id = None
            
            while self.reward_monitoring_active:
                try:
                    # Discover peer info from cached JSON
                    try:
                        info = get_cached_peer_info()
                        if info:
                            peer_name = info.get("peer_name") or peer_name
                            peer_id = info.get("peer_id") or peer_id
                    except Exception:
                        pass
                    
                    # Resolve peer_id from name if not available
                    if not peer_id and peer_name:
                        try:
                            from urllib.parse import quote_plus
                            name_url = f"https://dashboard.gensyn.ai/api/v1/peer?name={quote_plus(peer_name)}"
                            r_name = requests.get(name_url, timeout=10)
                            if r_name.status_code == 200:
                                record = r_name.json()
                                raw_peer_id = record.get("peerId") or ""
                                peer_id = raw_peer_id.split("|")[-1] if "|" in raw_peer_id else raw_peer_id or None
                        except Exception:
                            pass
                    
                    # If still no peer_id, wait and retry
                    if not peer_id:
                        time.sleep(10)
                        continue
                    
                    # Fetch metrics by peer id
                    try:
                        from urllib.parse import quote_plus
                        id_url = f"https://dashboard.gensyn.ai/api/v1/peer?id={quote_plus(peer_id)}"
                        r = requests.get(id_url, timeout=10)
                        if r.status_code == 200:
                            data = r.json()
                            reward = data.get("reward", 0)
                            score = data.get("score", 0)
                            
                            # Check for increases
                            reward_diff = None
                            win_diff = None
                            if last_reward is not None and reward > last_reward:
                                reward_diff = reward - last_reward
                            if last_win is not None and score > last_win:
                                win_diff = score - last_win
                            
                            last_reward = reward
                            last_win = score
                            
                            # Send notifications for increases
                            notifications = []
                            if reward_diff:
                                notifications.append(f"🎁 reward {reward}+{reward_diff}")
                            if win_diff:
                                notifications.append(f"🏆 win {score}+{win_diff}")
                            
                            if notifications:
                                message = " ".join(notifications)
                                self.webhook_client.send_reward_update({
                                    "peer_name": peer_name,
                                    "peer_id": peer_id,
                                    "reward": reward,
                                    "reward_diff": reward_diff,
                                    "score": score,
                                    "win_diff": win_diff,
                                    "message": message
                                })
                    except Exception as e:
                        self.logger.error(f"Reward monitor fetch error: {str(e)}")
                    
                    time.sleep(600)  # 10 minutes
                    
                except Exception as e:
                    self.logger.error(f"Reward monitor error: {str(e)}")
                    time.sleep(30)
        
        self.reward_monitor_thread = threading.Thread(target=reward_monitor, daemon=True)
        self.reward_monitor_thread.start()
    
    def stop_reward_monitoring(self):
        """Stop reward monitoring"""
        self.reward_monitoring_active = False
    
    def run(self):
        """Run the webhook bot"""
        if not self.config_manager.is_configured():
            print("❌ Webhook not configured. Please run configuration first:")
            print("   python webhook_config.py")
            return
        
        print("🚀 Starting Gensyn Webhook Bot...")
        print(f"📍 VPS ID: {self.config_manager.get_vps_info()['vps_id']}")
        print(f"🌐 Webhook URL: {self.config_manager.config['webhook_url']}")
        print(f"🔌 Listening on port: {self.config_manager.config.get('webhook_port', 8080)}")
        
        # Start monitoring by default
        self.start_monitoring()
        self.start_reward_monitoring()
        
        # Send startup notification
        self.webhook_client.send_notification(
            "bot_startup",
            f"Gensyn Bot started on VPS {self.config_manager.get_vps_info()['vps_name']}",
            "normal"
        )
        
        # Run the webhook server (this blocks)
        self.webhook_server.run()

def main():
    """Main function"""
    try:
        bot = WebhookBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot failed to start: {str(e)}")
        logging.error(f"Bot startup error: {str(e)}")

if __name__ == "__main__":
    main()

