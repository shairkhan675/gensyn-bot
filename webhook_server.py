#!/usr/bin/env python3
"""
Webhook Server for Gensyn Bot
Handles incoming command requests from the n8n server
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

from webhook_config import WebhookConfig

class CommandRequest(BaseModel):
    """Pydantic model for incoming command requests"""
    command: str
    parameters: Optional[Dict[str, Any]] = {}
    auth_token: str
    timestamp: Optional[str] = None
    request_id: Optional[str] = None

class CommandResponse(BaseModel):
    """Pydantic model for command responses"""
    success: bool
    result: str
    execution_time: float
    timestamp: str
    vps_id: str
    request_id: Optional[str] = None

class WebhookServer:
    def __init__(self):
        self.config_manager = WebhookConfig()
        self.config = self.config_manager.get_config()
        self.app = FastAPI(title="Gensyn Bot Webhook Server")
        self.command_handlers: Dict[str, Callable] = {}
        
        # Setup logging
        logging.basicConfig(
            filename='/root/webhook_server.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup routes
        self._setup_routes()
        
        # Default command handlers
        self._register_default_handlers()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/webhook/command")
        async def receive_command(request: CommandRequest, background_tasks: BackgroundTasks):
            """Main endpoint for receiving commands"""
            return await self._handle_command_request(request, background_tasks)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            vps_info = self.config_manager.get_vps_info()
            return {
                "status": "healthy",
                "vps_id": vps_info["vps_id"],
                "vps_name": vps_info["vps_name"],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0"
            }
        
        @self.app.get("/status")
        async def get_status():
            """Get current VPS status"""
            if not self._authenticate_request(None):  # Quick status doesn't need auth
                return await self._get_basic_status()
            return await self._get_detailed_status()
    
    def _authenticate_request(self, auth_token: Optional[str]) -> bool:
        """Authenticate incoming request"""
        if not auth_token:
            return False
        
        expected_token = self.config.get("auth_token")
        if not expected_token:
            self.logger.error("No auth token configured")
            return False
        
        return auth_token == expected_token
    
    async def _handle_command_request(self, request: CommandRequest, background_tasks: BackgroundTasks) -> JSONResponse:
        """Handle incoming command request"""
        start_time = time.time()
        vps_info = self.config_manager.get_vps_info()
        
        # Authenticate request
        if not self._authenticate_request(request.auth_token):
            self.logger.warning(f"Unauthorized command request: {request.command}")
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Check if command handler exists
        if request.command not in self.command_handlers:
            self.logger.error(f"Unknown command: {request.command}")
            raise HTTPException(status_code=400, detail=f"Unknown command: {request.command}")
        
        # Log the request
        self.logger.info(f"Executing command: {request.command} with params: {request.parameters}")
        
        try:
            # Execute command
            handler = self.command_handlers[request.command]
            result = await self._execute_command_async(handler, request.parameters)
            
            execution_time = time.time() - start_time
            
            response = CommandResponse(
                success=True,
                result=result,
                execution_time=execution_time,
                timestamp=datetime.utcnow().isoformat() + "Z",
                vps_id=vps_info["vps_id"],
                request_id=request.request_id
            )
            
            self.logger.info(f"Command {request.command} executed successfully in {execution_time:.2f}s")
            return JSONResponse(content=response.dict())
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Command failed: {str(e)}"
            
            response = CommandResponse(
                success=False,
                result=error_msg,
                execution_time=execution_time,
                timestamp=datetime.utcnow().isoformat() + "Z",
                vps_id=vps_info["vps_id"],
                request_id=request.request_id
            )
            
            self.logger.error(f"Command {request.command} failed: {str(e)}")
            return JSONResponse(content=response.dict(), status_code=500)
    
    async def _execute_command_async(self, handler: Callable, parameters: Dict[str, Any]) -> str:
        """Execute command handler asynchronously"""
        loop = asyncio.get_event_loop()
        
        if asyncio.iscoroutinefunction(handler):
            return await handler(parameters)
        else:
            return await loop.run_in_executor(None, handler, parameters)
    
    def register_command_handler(self, command: str, handler: Callable):
        """Register a command handler"""
        self.command_handlers[command] = handler
        self.logger.info(f"Registered command handler: {command}")
    
    def _register_default_handlers(self):
        """Register default command handlers"""
        
        def check_ip(params: Dict[str, Any]) -> str:
            """Check current public IP"""
            import requests
            try:
                ip = requests.get('https://api.ipify.org', timeout=10).text.strip()
                return f"Current Public IP: {ip}"
            except Exception as e:
                return f"Error checking IP: {str(e)}"
        
        def vpn_on(params: Dict[str, Any]) -> str:
            """Turn VPN on"""
            import subprocess
            try:
                subprocess.run(['wg-quick', 'up', 'wg0'], check=True)
                return "VPN enabled successfully"
            except subprocess.CalledProcessError as e:
                if "already exists" in str(e):
                    return "VPN already enabled"
                raise Exception(f"VPN failed to start: {str(e)}")
        
        def vpn_off(params: Dict[str, Any]) -> str:
            """Turn VPN off"""
            import subprocess
            try:
                subprocess.run(['wg-quick', 'down', 'wg0'], check=True)
                return "VPN disabled successfully"
            except subprocess.CalledProcessError as e:
                if "is not a WireGuard interface" in str(e):
                    return "VPN already disabled"
                raise Exception(f"VPN failed to stop: {str(e)}")
        
        def gensyn_status(params: Dict[str, Any]) -> str:
            """Get Gensyn status"""
            # Import the status function from the original bot
            try:
                import sys
                sys.path.append('/root/gensyn-bot')
                from bot import format_gensyn_status
                return format_gensyn_status()
            except Exception as e:
                return f"Error getting Gensyn status: {str(e)}"
        
        def start_gensyn(params: Dict[str, Any]) -> str:
            """Start Gensyn"""
            try:
                import sys
                sys.path.append('/root/gensyn-bot')
                from bot import start_gensyn_session, check_gensyn_screen_running
                
                if check_gensyn_screen_running():
                    return "Gensyn already running"
                
                use_sync_backup = params.get("use_sync_backup", True)
                fresh_start = params.get("fresh_start", False)
                
                # This would need to be adapted to not use chat_id
                # For now, we'll use a simple version
                import subprocess
                import os
                
                if fresh_start:
                    cmd = "cd /root/rl-swarm && screen -dmS gensyn bash -c 'python3 -m venv .venv && source .venv/bin/activate && ./run_rl_swarm.sh'"
                    subprocess.run(cmd, shell=True, check=True)
                    return "Fresh Gensyn node started"
                else:
                    if not os.path.exists("/root/rl-swarm/swarm.pem"):
                        return "swarm.pem not found. Use fresh_start=true or upload swarm.pem first"
                    
                    cmd = "cd /root/rl-swarm && screen -dmS gensyn bash -c 'python3 -m venv .venv && source .venv/bin/activate && ./run_rl_swarm.sh'"
                    subprocess.run(cmd, shell=True, check=True)
                    return "Gensyn started successfully"
                    
            except Exception as e:
                return f"Error starting Gensyn: {str(e)}"
        
        def kill_gensyn(params: Dict[str, Any]) -> str:
            """Kill Gensyn"""
            try:
                import subprocess
                subprocess.run("screen -S gensyn -X quit", shell=True, check=True)
                return "Gensyn screen killed successfully"
            except subprocess.CalledProcessError as e:
                return f"Failed to kill Gensyn screen: {str(e)}"
        
        def get_logs(params: Dict[str, Any]) -> str:
            """Get system logs"""
            log_type = params.get("log_type", "gensyn")
            lines = params.get("lines", 50)
            
            try:
                if log_type == "gensyn":
                    log_path = "/root/rl-swarm/logs/swarm_launcher.log"
                elif log_type == "bot":
                    log_path = "/root/bot_error.log"
                elif log_type == "webhook":
                    log_path = "/root/webhook_server.log"
                else:
                    return f"Unknown log type: {log_type}"
                
                if not os.path.exists(log_path):
                    return f"Log file not found: {log_path}"
                
                import subprocess
                result = subprocess.run(f"tail -{lines} {log_path}", shell=True, capture_output=True, text=True)
                return result.stdout
                
            except Exception as e:
                return f"Error reading logs: {str(e)}"
        
        # Register all handlers
        self.register_command_handler("check_ip", check_ip)
        self.register_command_handler("vpn_on", vpn_on)
        self.register_command_handler("vpn_off", vpn_off)
        self.register_command_handler("gensyn_status", gensyn_status)
        self.register_command_handler("start_gensyn", start_gensyn)
        self.register_command_handler("kill_gensyn", kill_gensyn)
        self.register_command_handler("get_logs", get_logs)
    
    async def _get_basic_status(self) -> Dict[str, Any]:
        """Get basic VPS status without authentication"""
        vps_info = self.config_manager.get_vps_info()
        return {
            "vps_id": vps_info["vps_id"],
            "vps_name": vps_info["vps_name"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "online"
        }
    
    async def _get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed VPS status"""
        try:
            import psutil
            import subprocess
            
            # Check Gensyn status
            gensyn_running = False
            try:
                result = subprocess.run("screen -ls", shell=True, capture_output=True, text=True)
                gensyn_running = "gensyn" in result.stdout
            except:
                pass
            
            # Check VPN status
            vpn_status = "unknown"
            try:
                result = subprocess.run("wg show", shell=True, capture_output=True, text=True)
                vpn_status = "connected" if result.returncode == 0 and "wg0" in result.stdout else "disconnected"
            except:
                pass
            
            # Check API status
            api_status = "unknown"
            try:
                import requests
                response = requests.get("http://localhost:3000", timeout=3)
                api_status = "running" if "Sign in to Gensyn" in response.text else "stopped"
            except:
                api_status = "stopped"
            
            vps_info = self.config_manager.get_vps_info()
            
            return {
                "vps_id": vps_info["vps_id"],
                "vps_name": vps_info["vps_name"],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "online",
                "gensyn_running": gensyn_running,
                "vpn_status": vpn_status,
                "api_status": api_status,
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent
                }
            }
        except Exception as e:
            return {"error": f"Failed to get detailed status: {str(e)}"}
    
    def run(self, host: str = "0.0.0.0", port: Optional[int] = None):
        """Run the webhook server"""
        if not self.config_manager.is_configured():
            self.logger.error("Webhook not configured. Run webhook_config.py first.")
            return
        
        server_port = port or self.config.get("webhook_port", 8080)
        self.logger.info(f"Starting webhook server on {host}:{server_port}")
        
        try:
            uvicorn.run(self.app, host=host, port=server_port, log_level="info")
        except Exception as e:
            self.logger.error(f"Failed to start webhook server: {str(e)}")

# Main function for running the server
def main():
    server = WebhookServer()
    server.run()

if __name__ == "__main__":
    main()

