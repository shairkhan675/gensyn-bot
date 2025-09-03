# n8n Quick Start for Gensyn Bot Multi-VPS

This is a **quick start guide** for setting up n8n with the Gensyn Bot multi-VPS system. For detailed information, see the complete documentation files.

## 📁 Documentation Files

1. **`N8N_SETUP_GUIDE.md`** - Complete architecture and setup guide
2. **`gensyn-multi-vps-workflow.json`** - **IMPORTABLE WORKFLOW** 🔥
3. **`N8N_WORKFLOW_CONFIGURATION.md`** - Step-by-step configuration
4. **`N8N_QUICK_START.md`** - This quick start guide

## ⚡ 5-Minute Setup

### 1. Prerequisites
- ✅ n8n instance running (self-hosted or cloud)
- ✅ Domain with SSL pointing to n8n
- ✅ Telegram bot token from @BotFather

### 2. Import Workflow
1. **Download**: `gensyn-multi-vps-workflow.json`
2. **Import**: n8n → Import from file → Select JSON file
3. **Activate**: Toggle workflow to active

### 3. Set Environment Variables
```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
ADMIN_CHAT_ID=your-telegram-user-id-here
```

### 4. Get Webhook URL
- **Copy from workflow**: VPS Status Webhook node
- **Format**: `https://your-n8n-domain.com/webhook/gensyn/status`

### 5. Configure First VPS
```bash
cd /root/gensyn-bot
python webhook_config.py

# Enter:
# VPS Name: london-server
# Webhook URL: https://your-n8n-domain.com/webhook/gensyn/status
# Port: 8080
```

### 6. Add VPS to Workflow
Edit these workflow nodes with your VPS details:

#### "Process VPS Webhook" node:
```javascript
const expectedTokens = {
  "london-server": "your-vps-auth-token-here"
};
```

#### "Route Command to VPS" node:
```javascript
const vpsConfigs = {
  "london-server": {
    "webhook_url": "http://your-vps-ip:8080/webhook/command",
    "auth_token": "your-vps-auth-token-here"
  }
};
```

### 7. Start & Test
```bash
# On VPS
python start_webhook_bot.py start

# In Telegram
/start → Select VPS → Test commands
```

## 🔄 Add More VPSs

For each additional VPS:

1. **Configure VPS**: Same webhook URL, unique name
2. **Add to workflow**: Update both nodes with new VPS details
3. **Test**: Should appear in Telegram menu

## 📊 What You Get

### Single Telegram Interface
```
🤖 Gensyn Multi-VPS Manager

🖥️ Available VPSs:
├── 🟢 London Server (2m ago)
├── 🟢 New York Server (1m ago)  
└── 🔴 Tokyo Server (offline)

[Select VPS] → [Commands] → [Results]
```

### Per-VPS Management
```
🖥️ London Server Management

📊 Status: 🟢 Online (2m ago)
💻 CPU: 25% | RAM: 60% | Disk: 45%

[📊 Status] [🌐 IP] [▶️ Start] [⏹️ Stop]
[🔒 VPN On] [🔓 VPN Off] [📋 Logs]
```

### Automated Monitoring
- **Heartbeats**: Every 5 minutes from each VPS
- **Alerts**: High-priority notifications forwarded
- **Status Tracking**: Online/offline detection
- **System Metrics**: CPU, RAM, disk usage

## 🔧 Workflow Features

### Incoming Webhooks (VPS → n8n)
- ✅ Status updates
- ✅ Notifications & alerts  
- ✅ Reward notifications
- ✅ Error alerts
- ✅ Heartbeat monitoring
- ✅ Command responses

### Outgoing Commands (n8n → VPS)
- ✅ All original bot commands
- ✅ Gensyn management (start/stop/status)
- ✅ VPN control (on/off)
- ✅ System utilities (IP, logs, updates)
- ✅ Custom command routing

### Security
- ✅ Token-based authentication
- ✅ Per-VPS auth tokens
- ✅ Request validation
- ✅ Error handling

## 🚨 Troubleshooting

### VPS Not Showing?
1. **Check webhook URL** in VPS config
2. **Verify auth token** in workflow
3. **Confirm VPS bot running**
4. **Check n8n execution logs**

### Commands Not Working?
1. **Check VPS IP/port** in workflow
2. **Verify auth tokens** match
3. **Test VPS webhook endpoint**
4. **Check firewall settings**

### Test Commands
```bash
# Test VPS endpoint
curl -X POST http://vps-ip:8080/webhook/command \
  -H "Content-Type: application/json" \
  -d '{"command":"check_ip","auth_token":"your-token"}'

# Test n8n endpoint  
curl -X POST https://your-n8n.com/webhook/gensyn/status \
  -H "Content-Type: application/json" \
  -d '{"message_type":"heartbeat","vps_id":"test","auth_token":"test"}'
```

## 📚 Full Documentation

- **Complete Setup**: See `N8N_SETUP_GUIDE.md`
- **Detailed Config**: See `N8N_WORKFLOW_CONFIGURATION.md`
- **VPS Setup**: See `README_WEBHOOK.md`

## 🎯 Benefits Achieved

✅ **Unified Interface**: Single Telegram bot for all VPSs  
✅ **Scalable**: Add unlimited VPSs easily  
✅ **Real-time**: Instant status updates via webhooks  
✅ **Secure**: Token-based authentication  
✅ **Monitored**: Automatic health checking  
✅ **Future-ready**: Foundation for AI/automation  

**🎉 You now have enterprise-grade multi-VPS management through Telegram!**

