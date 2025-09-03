#!/usr/bin/env python3
"""
Startup Script for Gensyn Webhook Bot
Handles both webhook server and monitoring processes
"""

import os
import sys
import time
import signal
import subprocess
import threading
import argparse
from typing import List, Optional

# Add current directory to path
sys.path.append('/root/gensyn-bot')

from webhook_config import WebhookConfig

class WebhookBotManager:
    def __init__(self):
        self.config_manager = WebhookConfig()
        self.processes: List[subprocess.Popen] = []
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.stop_all()
        sys.exit(0)
    
    def check_configuration(self) -> bool:
        """Check if webhook is properly configured"""
        if not self.config_manager.is_configured():
            print("❌ Webhook not configured!")
            print("   Please run: python webhook_config.py")
            return False
        
        config = self.config_manager.get_config()
        print("✅ Webhook configuration found:")
        print(f"   VPS Name: {config.get('vps_name')}")
        print(f"   VPS ID: {config.get('vps_id')}")
        print(f"   Webhook URL: {config.get('webhook_url')}")
        print(f"   Listening Port: {config.get('webhook_port', 8080)}")
        return True
    
    def check_dependencies(self) -> bool:
        """Check if all dependencies are available"""
        print("🔍 Checking dependencies...")
        
        # Check Python modules
        required_modules = [
            'fastapi', 'uvicorn', 'requests', 'psutil', 'web3'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            print(f"❌ Missing Python modules: {', '.join(missing_modules)}")
            print("   Please run: pip install -r requirements.txt")
            return False
        
        # Check if virtual environment exists
        venv_path = "/root/gensyn-bot/.venv"
        if not os.path.exists(f"{venv_path}/bin/python3"):
            print("⚠️  Virtual environment not found at /root/gensyn-bot/.venv")
            print("   The bot will use system Python")
        else:
            print("✅ Virtual environment found")
        
        print("✅ All dependencies available")
        return True
    
    def start_webhook_server(self) -> subprocess.Popen:
        """Start the webhook server process"""
        print("🚀 Starting webhook server...")
        
        # Try to use virtual environment first, fall back to system Python
        python_path = "/root/gensyn-bot/.venv/bin/python3"
        if not os.path.exists(python_path):
            python_path = "python3"
        
        cmd = [python_path, "/root/gensyn-bot/webhook_bot.py"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env={**os.environ, "PYTHONPATH": "/root/gensyn-bot"}
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            if process.poll() is None:
                print("✅ Webhook server started successfully")
                return process
            else:
                stdout, _ = process.communicate()
                print(f"❌ Webhook server failed to start: {stdout}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting webhook server: {str(e)}")
            return None
    
    def start_reward_monitor(self) -> Optional[subprocess.Popen]:
        """Start the reward monitoring process"""
        print("📊 Starting reward monitor...")
        
        # Try to use virtual environment first, fall back to system Python
        python_path = "/root/gensyn-bot/.venv/bin/python3"
        if not os.path.exists(python_path):
            python_path = "python3"
        
        cmd = [python_path, "/root/gensyn-bot/webhook_reward.py"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env={**os.environ, "PYTHONPATH": "/root/gensyn-bot"}
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            if process.poll() is None:
                print("✅ Reward monitor started successfully")
                return process
            else:
                stdout, _ = process.communicate()
                print(f"❌ Reward monitor failed to start: {stdout}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting reward monitor: {str(e)}")
            return None
    
    def monitor_processes(self):
        """Monitor running processes and restart if needed"""
        while self.running:
            try:
                # Check each process
                for i, process in enumerate(self.processes[:]):  # Copy list to avoid modification during iteration
                    if process and process.poll() is not None:
                        print(f"⚠️  Process {i} died, restarting...")
                        
                        # Remove dead process
                        self.processes.remove(process)
                        
                        # Restart based on process type (simple heuristic)
                        if "webhook_bot.py" in ' '.join(process.args):
                            new_process = self.start_webhook_server()
                        elif "webhook_reward.py" in ' '.join(process.args):
                            new_process = self.start_reward_monitor()
                        else:
                            continue
                        
                        if new_process:
                            self.processes.append(new_process)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"❌ Error in process monitor: {str(e)}")
                time.sleep(60)
    
    def start_all(self, enable_reward_monitor: bool = True):
        """Start all components"""
        if not self.check_configuration():
            return False
        
        if not self.check_dependencies():
            return False
        
        print("\n🚀 Starting Gensyn Webhook Bot...")
        
        # Start webhook server
        webhook_process = self.start_webhook_server()
        if not webhook_process:
            print("❌ Failed to start webhook server")
            return False
        
        self.processes.append(webhook_process)
        
        # Start reward monitor if enabled
        if enable_reward_monitor:
            reward_process = self.start_reward_monitor()
            if reward_process:
                self.processes.append(reward_process)
            else:
                print("⚠️  Reward monitor failed to start, continuing without it")
        
        # Start process monitor
        self.running = True
        monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        monitor_thread.start()
        
        print("\n✅ All components started successfully!")
        print("📋 Running processes:")
        for i, process in enumerate(self.processes):
            if process and process.poll() is None:
                print(f"   {i+1}. PID {process.pid}: {' '.join(process.args)}")
        
        print("\n📊 Bot Status:")
        print(f"   VPS: {self.config_manager.get_vps_info()['vps_name']}")
        print(f"   Webhook URL: {self.config_manager.config['webhook_url']}")
        print(f"   Listening Port: {self.config_manager.config.get('webhook_port', 8080)}")
        print("\n💡 Press Ctrl+C to stop all processes")
        
        return True
    
    def stop_all(self):
        """Stop all running processes"""
        print("🛑 Stopping all processes...")
        self.running = False
        
        for i, process in enumerate(self.processes):
            if process and process.poll() is None:
                print(f"   Stopping process {i+1} (PID {process.pid})...")
                try:
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                        print(f"   ✅ Process {i+1} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"   🔨 Force killing process {i+1}...")
                        process.kill()
                        process.wait()
                        print(f"   ✅ Process {i+1} force killed")
                        
                except Exception as e:
                    print(f"   ❌ Error stopping process {i+1}: {str(e)}")
        
        self.processes.clear()
        print("✅ All processes stopped")
    
    def status(self):
        """Show status of all components"""
        print("📊 Gensyn Webhook Bot Status")
        print("=" * 40)
        
        if not self.config_manager.is_configured():
            print("❌ Not configured")
            return
        
        config = self.config_manager.get_config()
        vps_info = self.config_manager.get_vps_info()
        
        print(f"VPS Name: {vps_info['vps_name']}")
        print(f"VPS ID: {vps_info['vps_id']}")
        print(f"Webhook URL: {config['webhook_url']}")
        print(f"Listening Port: {config.get('webhook_port', 8080)}")
        
        print(f"\nRunning Processes: {len(self.processes)}")
        for i, process in enumerate(self.processes):
            if process:
                status = "Running" if process.poll() is None else "Stopped"
                print(f"  {i+1}. PID {process.pid}: {status}")
        
        # Check if ports are listening
        try:
            import socket
            port = config.get('webhook_port', 8080)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"✅ Webhook server responding on port {port}")
            else:
                print(f"❌ Webhook server not responding on port {port}")
        except Exception:
            print("❓ Unable to check webhook server status")
    
    def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        try:
            while self.running and any(p.poll() is None for p in self.processes):
                time.sleep(1)
        except KeyboardInterrupt:
            pass

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description="Gensyn Webhook Bot Manager")
    parser.add_argument("command", nargs="?", choices=["start", "stop", "status", "restart"], 
                       default="start", help="Command to execute")
    parser.add_argument("--no-reward-monitor", action="store_true", 
                       help="Don't start the reward monitor")
    parser.add_argument("--daemon", action="store_true",
                       help="Run in daemon mode (requires systemd or similar)")
    
    args = parser.parse_args()
    
    manager = WebhookBotManager()
    
    if args.command == "start":
        if manager.start_all(enable_reward_monitor=not args.no_reward_monitor):
            if not args.daemon:
                manager.wait_for_shutdown()
        
    elif args.command == "stop":
        manager.stop_all()
        
    elif args.command == "status":
        manager.status()
        
    elif args.command == "restart":
        manager.stop_all()
        time.sleep(2)
        if manager.start_all(enable_reward_monitor=not args.no_reward_monitor):
            if not args.daemon:
                manager.wait_for_shutdown()

if __name__ == "__main__":
    main()

