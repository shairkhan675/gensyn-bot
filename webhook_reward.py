#!/usr/bin/env python3
"""
Webhook-based Reward Monitor for Gensyn Bot
Replaces direct Telegram messaging with webhook notifications
"""

import os
import time
import json
import html
import requests
import subprocess
from web3 import Web3
from datetime import datetime, date
from typing import Dict, Any, Optional, List

from webhook_client import WebhookClient

# Hardcoded settings (can be moved to config later)
PEER_NAMES = ["sly loud alpaca", "blue fast tiger"]  # Edit these if needed
DELAY_SECONDS = 1800  # 30 minutes
SCREEN_NAME = "gensyn"
NODE_NO = "1"

ALCHEMY_RPC = "https://gensyn-testnet.g.alchemy.com/v2/TD5tr7mo4VfXlSaolFlSr3tL70br2M9J"
CONTRACT_ADDRESS = "0x69C6e1D608ec64885E7b185d39b04B491a71768C"
ABI = [
    {
        "name": "getEoa",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "peerIds", "type": "string[]"}],
        "outputs": [{"name": "", "type": "address[]"}]
    }
]

EOA_CACHE_FILE = "/root/gensyn-bot/eoa_cache.json"

class WebhookRewardMonitor:
    def __init__(self):
        self.webhook_client = WebhookClient()
        self.w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS), 
            abi=ABI
        )
        
        # Setup logging
        import logging
        logging.basicConfig(
            filename='/root/webhook_reward.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def log_message(self, message: str):
        """Log message to file"""
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("/root/sent_messages_log.txt", "a") as f:
            f.write(f"{log_time} - Webhook Message Sent:\n{message}\n\n")
    
    def get_last_screen_logs(self, screen_name: str = "gensyn", lines: int = 10) -> str:
        """Get last screen logs"""
        try:
            log_path = f"/tmp/{screen_name}_log.txt"
            subprocess.run(f"screen -S {screen_name} -X hardcopy {log_path}", shell=True, check=True)
            with open(log_path, "rb") as f:
                content = f.read().decode("utf-8", errors="ignore")
            return "\n".join(content.strip().split("\n")[-lines:])
        except Exception as e:
            return f"Log fetch error: {str(e)}"
    
    def fetch_peer_data(self, peer_name: str) -> Optional[Dict[str, Any]]:
        """Fetch peer data from Gensyn API"""
        url_name = peer_name.replace(" ", "%20")
        url = f"https://dashboard-math.gensyn.ai/api/v1/peer?name={url_name}"
        try:
            response = requests.get(url, timeout=10)
            if response.ok:
                return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching peer data for {peer_name}: {str(e)}")
        return None
    
    def fetch_eoa_mapping(self, peer_ids: List[str]) -> Dict[str, str]:
        """Fetch EOA mapping from blockchain"""
        today = str(date.today())
        
        # Check cache first
        if os.path.exists(EOA_CACHE_FILE):
            try:
                with open(EOA_CACHE_FILE) as f:
                    data = json.load(f)
                    if data.get("date") == today:
                        return data.get("mapping", {})
            except Exception:
                pass
        
        # Fetch from blockchain
        try:
            addresses = self.contract.functions.getEoa(peer_ids).call()
            mapping = {pid: eoa for pid, eoa in zip(peer_ids, addresses)}
            
            # Cache the result
            with open(EOA_CACHE_FILE, "w") as f:
                json.dump({"date": today, "mapping": mapping}, f, indent=4)
            
            return mapping
        except Exception as e:
            self.logger.error(f"Error fetching EOA mapping: {str(e)}")
            return {pid: f"Error: {str(e)}" for pid in peer_ids}
    
    def format_peer_report(self, name: str, info: Dict[str, Any], eoa: str) -> Dict[str, Any]:
        """Format peer information for webhook"""
        peer_id = info["peerId"]
        explorer_link = f"https://gensyn-testnet.explorer.alchemy.com/address/{eoa}?tab=internal_txns"
        status = "Online" if info["online"] else "Offline"
        
        return {
            "node_number": NODE_NO,
            "peer_name": name,
            "peer_id": peer_id,
            "eoa_address": eoa,
            "total_reward": info['reward'],
            "total_wins": info['score'],
            "status": status,
            "online": info["online"],
            "explorer_link": explorer_link,
            "formatted_message": f"""
**Peer {NODE_NO}**
Name: `{name}`
Peer ID: `{peer_id}`
EOA: `{eoa}`
Total Reward: {info['reward']}
Total Wins: {info['score']}
Status: {status}
[View on Explorer]({explorer_link})
            """.strip()
        }
    
    def send_periodic_report(self):
        """Send periodic report via webhook"""
        try:
            peer_reports = []
            peer_infos = []
            peer_ids = []
            
            # Collect peer data
            for name in PEER_NAMES:
                data = self.fetch_peer_data(name.strip())
                if data:
                    peer_infos.append((name, data))
                    peer_ids.append(data["peerId"])
            
            if not peer_infos:
                self.webhook_client.send_error_alert(
                    "peer_data_fetch_failed",
                    "Failed to fetch data for any configured peers",
                    {"peer_names": PEER_NAMES}
                )
                return
            
            # Get EOA mappings
            eoa_map = self.fetch_eoa_mapping(peer_ids)
            
            # Format peer reports
            for name, info in peer_infos:
                peer_id = info["peerId"]
                eoa = eoa_map.get(peer_id, "N/A")
                report = self.format_peer_report(name, info, eoa)
                peer_reports.append(report)
            
            # Get screen logs
            logs = self.get_last_screen_logs(SCREEN_NAME)
            
            # Prepare webhook payload
            report_data = {
                "report_type": "periodic_status",
                "node_number": NODE_NO,
                "peer_reports": peer_reports,
                "screen_logs": logs,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # Send via webhook
            success = self.webhook_client.send_status_update(report_data)
            
            if success:
                self.logger.info(f"Periodic report sent successfully at {datetime.now()}")
                self.log_message(f"Periodic report sent: {len(peer_reports)} peers")
            else:
                self.logger.error("Failed to send periodic report via webhook")
            
        except Exception as e:
            error_msg = f"Error in periodic report: {str(e)}"
            self.logger.error(error_msg)
            self.webhook_client.send_error_alert(
                "periodic_report_error",
                error_msg,
                {"peer_names": PEER_NAMES}
            )
    
    def monitor_rewards(self):
        """Monitor for reward changes and send notifications"""
        last_rewards = {}
        last_scores = {}
        
        while True:
            try:
                # Collect current data
                for name in PEER_NAMES:
                    data = self.fetch_peer_data(name.strip())
                    if not data:
                        continue
                    
                    peer_id = data["peerId"]
                    current_reward = data.get("reward", 0)
                    current_score = data.get("score", 0)
                    
                    # Check for reward increase
                    if peer_id in last_rewards and current_reward > last_rewards[peer_id]:
                        reward_diff = current_reward - last_rewards[peer_id]
                        self.webhook_client.send_reward_update({
                            "peer_name": name,
                            "peer_id": peer_id,
                            "reward_increase": reward_diff,
                            "new_reward": current_reward,
                            "message": f"🎁 {name}: reward increased by {reward_diff} (now {current_reward})"
                        })
                    
                    # Check for score increase
                    if peer_id in last_scores and current_score > last_scores[peer_id]:
                        score_diff = current_score - last_scores[peer_id]
                        self.webhook_client.send_reward_update({
                            "peer_name": name,
                            "peer_id": peer_id,
                            "score_increase": score_diff,
                            "new_score": current_score,
                            "message": f"🏆 {name}: wins increased by {score_diff} (now {current_score})"
                        })
                    
                    # Update tracking
                    last_rewards[peer_id] = current_reward
                    last_scores[peer_id] = current_score
                
                time.sleep(600)  # Check every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Error in reward monitoring: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    def run(self):
        """Main run loop"""
        if not self.webhook_client.is_enabled():
            print("❌ Webhook not configured. Please run webhook_config.py first.")
            return
        
        print("🎯 Starting webhook-based reward monitor...")
        print(f"📊 Monitoring peers: {', '.join(PEER_NAMES)}")
        print(f"⏱️  Report interval: {DELAY_SECONDS/60:.1f} minutes")
        
        # Start reward monitoring in background
        import threading
        reward_thread = threading.Thread(target=self.monitor_rewards, daemon=True)
        reward_thread.start()
        
        # Send startup notification
        self.webhook_client.send_notification(
            "reward_monitor_startup",
            f"Reward monitor started for peers: {', '.join(PEER_NAMES)}",
            "normal"
        )
        
        # Main periodic reporting loop
        while True:
            try:
                self.send_periodic_report()
                time.sleep(DELAY_SECONDS)
            except KeyboardInterrupt:
                print("\n🛑 Reward monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Main loop error: {str(e)}")
                time.sleep(60)

def main():
    """Main function"""
    monitor = WebhookRewardMonitor()
    monitor.run()

if __name__ == "__main__":
    main()

