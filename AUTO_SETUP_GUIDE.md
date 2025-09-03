# 🤖 Automated Gensyn Bot Setup Guide

**Zero Configuration Required!** This guide shows you how to set up an automated, self-discovering multi-VPS management system that requires **minimal technical knowledge**.

## 🎯 What This Does

- **Auto-Discovery**: VPSs automatically register themselves with your n8n server
- **Zero Config**: No manual token management or IP address configuration
- **Plug & Play**: Just run one command on each VPS and they appear in Telegram
- **Admin Approval**: Optional approval system for new VPSs
- **Real-time Monitoring**: Automatic status updates and health monitoring

## 📋 Quick Overview

```
1. Setup n8n server (one time)
2. Run auto_setup.py on each VPS (2 questions only)
3. VPSs auto-register and appear in Telegram
4. Manage unlimited VPSs from single bot
```

## 🏗️ Architecture

```
VPS 1 ──┐                    ┌─ Single Telegram Bot
VPS 2 ──┼──► n8n Server ──────┤
VPS 3 ──┘     (Auto Hub)      └─ Admin Notifications
   ↑                               ↑
Auto-registers              Approve/Reject VPSs
```

## 🚀 Part 1: n8n Server Setup (One Time)

### Step 1: Import Auto-Discovery Workflow

1. **Download**: `gensyn-auto-discovery-workflow.json`
2. **Import to n8n**: Workflows → Import from file
3. **Activate workflow**

### Step 2: Set Environment Variables

Set these in your n8n deployment:

```bash
# Required
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
ADMIN_CHAT_ID=your-telegram-user-id

# Optional
AUTO_APPROVE_VPS=true  # Auto-approve new VPSs (false = manual approval)
```

### Step 3: Get Webhook URLs

After importing, copy these URLs from the workflow:

- **Registration URL**: `https://your-n8n.com/webhook/gensyn/register` 
- **Status URL**: `https://your-n8n.com/webhook/gensyn/status`

**That's it for n8n setup!** 🎉

## 🖥️ Part 2: VPS Setup (Per VPS)

### Method 1: One-Line Install (Recommended)

```bash
# Download and run auto-setup
curl -sSL https://raw.githubusercontent.com/shairkhan2/gensyn-bot/main/auto_install.sh | bash
```

### Method 2: Manual Setup

```bash
# 1. Clone/download gensyn-bot
cd /root
git clone https://github.com/shairkhan2/gensyn-bot.git

# 2. Run auto-setup
cd gensyn-bot
python3 auto_setup.py
```

### Setup Questions (Only 2!)

```
🌐 Enter your n8n server URL: https://your-n8n.com
🏷️ Enter a name for this VPS: London Server
```

**That's it!** Everything else is automatic:
- ✅ Generates unique VPS ID and auth tokens
- ✅ Auto-detects system capabilities 
- ✅ Configures webhook endpoints
- ✅ Registers with n8n server
- ✅ Starts monitoring services
- ✅ Sets up auto-start on boot

## 📱 Part 3: Using the System

### Telegram Interface

1. **Open your Telegram bot**
2. **Send `/start`**
3. **See all VPSs automatically!**

```
🤖 Gensyn Auto-Discovery Manager

📊 Status: 3/3 VPSs online

🖥️ Select a VPS to manage:
[🟢 London Server (2m ago)]
[🟢 New York VPS (1m ago)]
[🟢 Tokyo Server (3m ago)]

[🔄 Refresh] [⚙️ Admin Panel]
```

### VPS Management

Select any VPS to get:

```
🖥️ London Server Management

📊 Status: 🟢 Online (2m ago)
💻 CPU: 25% | RAM: 60% | Disk: 45%
🎯 Gensyn: ✅ | VPN: ✅ | Auto-Discovery: ✅

🎛️ Choose an action:
[📊 Status] [🌐 IP] [📈 Gensyn Status]
[▶️ Start] [⏹️ Stop] [🔄 Restart]
[🔒 VPN On] [🔓 VPN Off] [📋 Logs]
```

### Admin Features

Admins get additional options:
- **Approve/reject new VPSs**
- **View all VPS statuses**
- **Receive registration notifications**
- **Manage VPS permissions**

## 🔒 Security & Approval

### Auto-Approval Mode
```bash
# In n8n environment
AUTO_APPROVE_VPS=true   # VPSs auto-approved
```

### Manual Approval Mode  
```bash
# In n8n environment
AUTO_APPROVE_VPS=false  # Admin approval required
```

When a new VPS registers, admin receives:

```
🤖 New VPS Registration

VPS Details:
• Name: Tokyo Server
• ID: tokyo-server
• IP: 198.51.100.1
• System: Linux x86_64
• CPU Cores: 4
• Memory: 8GB

Capabilities:
• Gensyn: ✅
• VPN: ✅
• Auto-Discovery: ✅

Status: ⏳ Pending Approval

[✅ Approve] [❌ Reject]
```

## 🔧 Advanced Configuration

### Custom VPS Capabilities

The system auto-detects what each VPS can do:

```python
# Automatically detected
capabilities = {
    'gensyn': os.path.exists('/root/rl-swarm'),      # Gensyn installed?
    'vpn': os.path.exists('/etc/wireguard/wg0.conf'), # VPN configured?
    'docker': command_exists('docker'),               # Docker available?
    'monitoring': True,                               # Always enabled
    'auto_discovery': True                            # Always enabled
}
```

### Environment Variables

VPS setup supports these environment variables:

```bash
# Pre-configure setup (skip questions)
export N8N_SERVER_URL="https://your-n8n.com"
export VPS_NAME="Auto Server"
export AUTO_APPROVE="true"

# Then run setup
python3 auto_setup.py
```

### Custom Commands

Add custom commands by modifying the auto-discovery bot:

```python
# In auto_webhook_bot.py
def custom_command(params):
    # Your custom logic
    return "Custom command executed"

# Register it
server.register_command_handler("custom_cmd", custom_command)
```

## 📊 Monitoring & Maintenance

### System Status

Each VPS automatically reports:
- **Heartbeat every 5 minutes**
- **System metrics** (CPU, RAM, disk)
- **Service status** (Gensyn, VPN)
- **IP address changes**
- **Error conditions**

### Log Files

```bash
# Auto-discovery bot logs
tail -f /root/auto_webhook_bot.log

# System service logs  
journalctl -u gensyn-auto-bot -f

# Setup logs
tail -f /root/gensyn-bot/setup.log
```

### Health Checks

The system includes built-in health monitoring:
- **VPS offline detection** (no heartbeat > 10 minutes)
- **Service failure alerts**
- **System resource warnings**
- **Network connectivity issues**

## 🐛 Troubleshooting

### VPS Not Appearing in Telegram

1. **Check registration status**:
   ```bash
   python3 auto_setup.py --status
   ```

2. **Check logs**:
   ```bash
   tail -f /root/auto_webhook_bot.log
   ```

3. **Test connection**:
   ```bash
   curl -X POST https://your-n8n.com/webhook/gensyn/status \
     -H "Content-Type: application/json" \
     -d '{"message_type":"test","vps_id":"test","auth_token":"test"}'
   ```

### Registration Failed

1. **Check n8n URL**:
   ```bash
   curl https://your-n8n.com/healthz
   ```

2. **Verify firewall**:
   ```bash
   # Allow outbound HTTPS
   ufw allow out 443
   ```

3. **Re-run setup**:
   ```bash
   python3 auto_setup.py
   ```

### Commands Not Working

1. **Check VPS status in n8n logs**
2. **Verify auth token matches**
3. **Test webhook endpoint**:
   ```bash
   curl -X POST http://localhost:8080/webhook/command \
     -H "Content-Type: application/json" \
     -d '{"command":"check_ip","auth_token":"your-token"}'
   ```

## 🔄 Scaling to Many VPSs

### Bulk Deployment

For deploying to many VPSs:

1. **Create deployment script**:
   ```bash
   #!/bin/bash
   export N8N_SERVER_URL="https://your-n8n.com"
   export VPS_NAME="Server-$(hostname)"
   curl -sSL https://raw.githubusercontent.com/your-repo/auto_install.sh | bash
   ```

2. **Use configuration management**:
   - Ansible
   - Terraform
   - Custom deployment tools

### Performance Considerations

- **n8n server**: Can handle 100+ VPSs easily
- **Heartbeat frequency**: 5 minutes (adjustable)
- **Webhook timeouts**: 30 seconds (adjustable)
- **Database storage**: Uses n8n workflow static data

## 🚀 Benefits Achieved

✅ **Zero Configuration**: No manual token/IP management  
✅ **Auto-Discovery**: VPSs register themselves automatically  
✅ **Non-Technical Friendly**: Just 2 questions during setup  
✅ **Scalable**: Add unlimited VPSs with same simple process  
✅ **Secure**: Auto-generated unique tokens per VPS  
✅ **Monitored**: Real-time health and status tracking  
✅ **Admin Controlled**: Approve/reject new VPSs  
✅ **Future-Ready**: Foundation for AI automation  

## 🎯 Summary

This automated system transforms VPS management from a complex technical task into a simple, user-friendly process:

1. **One-time n8n setup** (import workflow, set environment variables)
2. **Simple VPS setup** (2 questions, everything else automatic)
3. **Instant management** (VPSs appear automatically in Telegram)

**Perfect for non-technical users** who want enterprise-grade multi-VPS management without the complexity! 🎉
