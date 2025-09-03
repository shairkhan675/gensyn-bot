import os
import time
import subprocess

BOT_CONFIG = "/root/bot_config.env"
WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"
BOT_PATH = "/root/gensyn-bot/bot.py"
VENV_PATH = "/root/gensyn-bot/.venv"
PYTHON_BIN = f"{VENV_PATH}/bin/python3"
REQUIREMENTS = "/root/gensyn-bot/requirements.txt"


def menu():
    while True:
        print("\n🛠️ Gensyn Bot Manager")
        print("=" * 50)
        print("📶 VPN & Network:")
        print("1. Paste WireGuard config")
        print("2. Check IP")
        print()
        print("🤖 Bot Configuration:")
        print("3. Setup Telegram Bot (Legacy)")
        print("4. Setup Webhook Bot (Recommended)")
        print("5. View Bot Configuration")
        print()
        print("🚀 Bot Control:")
        print("6. Start Legacy Bot")
        print("7. Start Webhook Bot")
        print("8. Stop All Bots")
        print("9. View Bot Status")
        print()
        print("⚙️ System:")
        print("10. Enable Bot on Boot")
        print("11. View Bot Logs")
        print("12. Rebuild Virtual Environment")
        print("13. Install requirements.txt")
        print()
        print("0. Exit")
        
        choice = input("\nSelect an option: ")

        if choice == "1":
            setup_vpn()
        elif choice == "2":
            check_ip()
        elif choice == "3":
            setup_telegram_bot()
        elif choice == "4":
            setup_webhook_bot()
        elif choice == "5":
            view_bot_config()
        elif choice == "6":
            start_legacy_bot()
        elif choice == "7":
            start_webhook_bot()
        elif choice == "8":
            stop_all_bots()
        elif choice == "9":
            view_bot_status()
        elif choice == "10":
            setup_systemd()
        elif choice == "11":
            view_logs()
        elif choice == "12":
            rebuild_venv()
        elif choice == "13":
            install_requirements()
        elif choice == "0":
            break
        else:
            print("❌ Invalid option.")


def setup_vpn():
    print("\n📋 Paste full WireGuard config. Type 'END' on a new line to finish:")
    config = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        config.append(line)

    os.makedirs("/etc/wireguard", exist_ok=True)
    with open(WG_CONFIG_PATH, "w") as f:
        f.write("\n".join(config))
    os.system("chmod 600 " + WG_CONFIG_PATH)
    print("✅ WireGuard config saved.")


def setup_telegram_bot():
    print("\n🤖 Legacy Telegram Bot Setup")
    print("⚠️  Note: This is the legacy polling-based bot. Consider using webhook bot instead.")
    token = input("Bot Token: ")
    user_id = input("Your Telegram User ID: ")

    with open(BOT_CONFIG, "w") as f:
        f.write(f"BOT_TOKEN={token}\n")
        f.write(f"USER_ID={user_id}\n")

    if not os.path.exists(BOT_PATH):
        os.system("cp ./default_bot.py /root/gensyn-bot/bot.py")
        os.system(f"chmod +x {BOT_PATH}")

    print("✅ Legacy bot config saved and default bot.py is ready.")

def setup_webhook_bot():
    print("\n🔗 Webhook Bot Setup")
    print("This will configure the bot to use webhooks instead of Telegram polling.")
    print("You'll need an n8n server to act as the central hub.")
    print()
    
    # Run webhook configuration
    os.system(f"{PYTHON_BIN} /root/gensyn-bot/webhook_config.py")

def view_bot_config():
    print("\n📋 Current Bot Configuration")
    print("=" * 40)
    
    # Check legacy config
    if os.path.exists(BOT_CONFIG):
        print("📱 Legacy Telegram Bot:")
        with open(BOT_CONFIG) as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    if "TOKEN" in key:
                        value = value[:10] + "..." if len(value) > 10 else value
                    print(f"   {key}: {value}")
    else:
        print("📱 Legacy Telegram Bot: Not configured")
    
    print()
    
    # Check webhook config
    webhook_config_path = "/root/gensyn-bot/webhook_config.json"
    if os.path.exists(webhook_config_path):
        print("🔗 Webhook Bot:")
        try:
            import json
            with open(webhook_config_path) as f:
                config = json.load(f)
            
            print(f"   VPS Name: {config.get('vps_name', 'Not set')}")
            print(f"   VPS ID: {config.get('vps_id', 'Not set')}")
            print(f"   Webhook URL: {config.get('webhook_url', 'Not set')}")
            print(f"   Webhook Port: {config.get('webhook_port', 'Not set')}")
            print(f"   Enabled: {config.get('enabled', False)}")
            token = config.get('auth_token', '')
            print(f"   Auth Token: {'Set' if token else 'Not set'}")
        except Exception as e:
            print(f"   Error reading config: {e}")
    else:
        print("🔗 Webhook Bot: Not configured")

def check_ip():
    print("\n🌐 Checking current IP address...")
    try:
        import requests
        ip = requests.get('https://api.ipify.org', timeout=10).text.strip()
        print(f"✅ Current Public IP: {ip}")
    except Exception as e:
        print(f"❌ Error checking IP: {str(e)}")


def start_legacy_bot():
    print("🚀 Starting legacy bot and reward.py in a screen session...")

    if not os.path.exists(f"{VENV_PATH}/bin/activate"):
        print("❌ Virtual environment not found. Please run option 12 to rebuild it.")
        return

    REWARD_PATH = "/root/gensyn-bot/reward.py"

    os.system("screen -S vpn_bot -X quit")
    os.system(
        f"screen -dmS vpn_bot bash -c 'source {VENV_PATH}/bin/activate && "
        f"python {BOT_PATH} & python {REWARD_PATH} && wait'"
    )
    print("✅ Legacy bot.py and reward.py started in screen session 'vpn_bot'")
    print("   Use: screen -r vpn_bot")

def start_webhook_bot():
    print("🔗 Starting webhook bot...")
    
    # Check if webhook is configured
    webhook_config_path = "/root/gensyn-bot/webhook_config.json"
    if not os.path.exists(webhook_config_path):
        print("❌ Webhook bot not configured. Please run option 4 first.")
        return
    
    # Stop any existing webhook bot
    os.system("pkill -f start_webhook_bot.py")
    os.system("pkill -f webhook_bot.py")
    
    # Start webhook bot
    os.system(f"{PYTHON_BIN} /root/gensyn-bot/start_webhook_bot.py start &")
    
    import time
    time.sleep(3)
    
    # Check if it started successfully
    if os.system("pgrep -f webhook_bot.py > /dev/null") == 0:
        print("✅ Webhook bot started successfully")
        print("   Use: python /root/gensyn-bot/start_webhook_bot.py status")
    else:
        print("❌ Failed to start webhook bot. Check logs.")

def stop_all_bots():
    print("🛑 Stopping all bots...")
    
    # Stop legacy bot
    legacy_stopped = False
    if os.system(f"pgrep -f '{BOT_PATH}' > /dev/null") == 0:
        os.system(f"pkill -f '{BOT_PATH}'")
        os.system("screen -S vpn_bot -X quit")
        legacy_stopped = True
    
    # Stop webhook bot
    webhook_stopped = False
    if os.system("pgrep -f webhook_bot.py > /dev/null") == 0:
        os.system("pkill -f start_webhook_bot.py")
        os.system("pkill -f webhook_bot.py")
        os.system("pkill -f webhook_reward.py")
        webhook_stopped = True
    
    if legacy_stopped or webhook_stopped:
        print("✅ Bots stopped.")
        if legacy_stopped:
            print("   Legacy bot stopped")
        if webhook_stopped:
            print("   Webhook bot stopped")
    else:
        print("ℹ️ No bots were running.")

def view_bot_status():
    print("\n📊 Bot Status")
    print("=" * 30)
    
    # Check legacy bot
    if os.system(f"pgrep -f '{BOT_PATH}' > /dev/null") == 0:
        print("📱 Legacy Bot: ✅ Running")
        os.system("pgrep -f bot.py")
    else:
        print("📱 Legacy Bot: ❌ Stopped")
    
    # Check webhook bot
    webhook_running = os.system("pgrep -f webhook_bot.py > /dev/null") == 0
    reward_running = os.system("pgrep -f webhook_reward.py > /dev/null") == 0
    
    if webhook_running or reward_running:
        print("🔗 Webhook Bot: ✅ Running")
        if webhook_running:
            print("   └─ Webhook server: ✅ Running")
        else:
            print("   └─ Webhook server: ❌ Stopped")
        
        if reward_running:
            print("   └─ Reward monitor: ✅ Running")
        else:
            print("   └─ Reward monitor: ❌ Stopped")
    else:
        print("🔗 Webhook Bot: ❌ Stopped")
    
    # Check if any screen sessions exist
    os.system("echo '\n📺 Screen Sessions:'")
    os.system("screen -ls 2>/dev/null | grep -E '(vpn_bot|gensyn)' || echo '   No relevant screen sessions'")

def view_logs():
    print("\n📋 Available Logs")
    print("1. Legacy bot errors")
    print("2. Webhook bot logs")
    print("3. Webhook client logs")
    print("4. Webhook server logs")
    print("5. Webhook reward logs")
    print("6. System journal (bot service)")
    print("7. Gensyn swarm logs")
    
    choice = input("\nSelect log to view: ")
    
    if choice == "1":
        os.system("tail -50 /root/bot_error.log")
    elif choice == "2":
        os.system("tail -50 /root/webhook_bot.log")
    elif choice == "3":
        os.system("tail -50 /root/webhook_client.log")
    elif choice == "4":
        os.system("tail -50 /root/webhook_server.log")
    elif choice == "5":
        os.system("tail -50 /root/webhook_reward.log")
    elif choice == "6":
        os.system("journalctl -u bot -f")
    elif choice == "7":
        os.system("tail -50 /root/rl-swarm/logs/swarm_launcher.log")
    else:
        print("❌ Invalid option.")


def setup_systemd():
    print("\n⚙️ Bot Service Setup")
    print("1. Legacy Bot Service")
    print("2. Webhook Bot Service (Recommended)")
    print("3. Disable Bot Service")
    
    choice = input("\nSelect option: ")
    
    if choice == "1":
        setup_legacy_systemd()
    elif choice == "2":
        setup_webhook_systemd()
    elif choice == "3":
        disable_systemd()
    else:
        print("❌ Invalid option.")

def setup_legacy_systemd():
    print("\n⚙️ Setting up legacy bot service...")

    service = f"""[Unit]
Description=Gensyn Legacy Telegram Bot
After=network.target

[Service]
Type=simple
ExecStart={PYTHON_BIN} {BOT_PATH}
EnvironmentFile={BOT_CONFIG}
Restart=always
User=root
WorkingDirectory=/root/gensyn-bot
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    with open("/etc/systemd/system/gensyn-legacy-bot.service", "w") as f:
        f.write(service)

    os.system("systemctl daemon-reload")
    os.system("systemctl enable gensyn-legacy-bot")
    os.system("systemctl start gensyn-legacy-bot")
    print("✅ Legacy bot service enabled and running via systemd.")

def setup_webhook_systemd():
    print("\n⚙️ Setting up webhook bot service...")
    
    # Check if webhook is configured
    webhook_config_path = "/root/gensyn-bot/webhook_config.json"
    if not os.path.exists(webhook_config_path):
        print("❌ Webhook bot not configured. Please run option 4 first.")
        return

    service = f"""[Unit]
Description=Gensyn Webhook Bot
After=network.target

[Service]
Type=simple
ExecStart={PYTHON_BIN} /root/gensyn-bot/start_webhook_bot.py start --daemon
Restart=always
RestartSec=10
User=root
WorkingDirectory=/root/gensyn-bot
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    with open("/etc/systemd/system/gensyn-webhook-bot.service", "w") as f:
        f.write(service)

    os.system("systemctl daemon-reload")
    os.system("systemctl enable gensyn-webhook-bot")
    os.system("systemctl start gensyn-webhook-bot")
    print("✅ Webhook bot service enabled and running via systemd.")
    print("   Use: systemctl status gensyn-webhook-bot")

def disable_systemd():
    print("\n🛑 Disabling bot services...")
    
    services = ["bot", "gensyn-legacy-bot", "gensyn-webhook-bot"]
    disabled_any = False
    
    for service in services:
        if os.path.exists(f"/etc/systemd/system/{service}.service"):
            os.system(f"systemctl stop {service}")
            os.system(f"systemctl disable {service}")
            print(f"   ✅ {service} service disabled")
            disabled_any = True
    
    if disabled_any:
        os.system("systemctl daemon-reload")
        print("✅ All bot services disabled.")
    else:
        print("ℹ️ No bot services found to disable.")


def rebuild_venv():
    print("♻️ Rebuilding virtual environment...")
    os.system(f"rm -rf {VENV_PATH}")
    os.system(f"python3 -m venv {VENV_PATH}")
    os.system(f"{PYTHON_BIN} -m pip install --upgrade pip")
    print("✅ Virtual environment rebuilt.")


def install_requirements():
    print("📦 Installing requirements.txt and Playwright dependencies...")
    if not os.path.exists(REQUIREMENTS):
        print("❌ requirements.txt not found.")
        return

    os.system(f"{PYTHON_BIN} -m pip install -r {REQUIREMENTS}")
    print("✅ Requirements and Playwright setup complete.")


if __name__ == "__main__":
    menu()

