#!/bin/bash

# Gensyn Bot Webhook Setup Script
# Quick setup for webhook-based multi-VPS management

set -e

echo "🔧 Gensyn Bot Webhook Setup"
echo "=" * 50

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo $0"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "webhook_config.py" ]; then
    echo "❌ Please run this script from the gensyn-bot directory"
    echo "   cd /root/gensyn-bot && ./setup_webhook.sh"
    exit 1
fi

echo "📦 Installing/updating Python dependencies..."
# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "✅ Virtual environment found"
    source .venv/bin/activate
else
    echo "🔨 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Install/update requirements
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Make scripts executable
chmod +x webhook_config.py
chmod +x webhook_bot.py
chmod +x webhook_client.py
chmod +x webhook_server.py
chmod +x start_webhook_bot.py
chmod +x setup_webhook.sh

echo "✅ Scripts made executable"

# Run webhook configuration
echo ""
echo "🔗 Starting webhook configuration..."
echo "You'll be prompted for your n8n webhook URL and VPS details."
echo ""

python3 webhook_config.py

# Check if configuration was successful
if [ -f "webhook_config.json" ]; then
    echo ""
    echo "✅ Webhook configuration completed!"
    
    # Extract VPS info for display
    VPS_NAME=$(python3 -c "import json; print(json.load(open('webhook_config.json'))['vps_name'])" 2>/dev/null || echo "unknown")
    WEBHOOK_URL=$(python3 -c "import json; print(json.load(open('webhook_config.json'))['webhook_url'])" 2>/dev/null || echo "unknown")
    WEBHOOK_PORT=$(python3 -c "import json; print(json.load(open('webhook_config.json'))['webhook_port'])" 2>/dev/null || echo "8080")
    
    echo ""
    echo "📋 Configuration Summary:"
    echo "   VPS Name: $VPS_NAME"
    echo "   Webhook URL: $WEBHOOK_URL"
    echo "   Listening Port: $WEBHOOK_PORT"
    
    echo ""
    echo "🚀 Setup Complete! Next steps:"
    echo ""
    echo "1. Test the webhook bot:"
    echo "   python3 start_webhook_bot.py start"
    echo ""
    echo "2. Enable auto-start on boot:"
    echo "   python3 bot_manager.py"
    echo "   → Choose option 10 (Enable Bot on Boot)"
    echo "   → Choose option 2 (Webhook Bot Service)"
    echo ""
    echo "3. Check status anytime:"
    echo "   python3 start_webhook_bot.py status"
    echo ""
    echo "4. View logs:"
    echo "   tail -f webhook_bot.log"
    echo ""
    echo "📖 For detailed documentation, see README_WEBHOOK.md"
    
else
    echo "❌ Configuration failed. Please run manually:"
    echo "   python3 webhook_config.py"
    exit 1
fi

echo ""
echo "🎉 Webhook bot setup completed successfully!"

