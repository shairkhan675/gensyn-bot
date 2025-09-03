# n8n Setup Guide for Gensyn Bot Multi-VPS Management

This guide provides step-by-step instructions for setting up n8n as the central hub for managing multiple Gensyn Bot VPSs through a single Telegram interface.

## 🏗️ Architecture Overview

```
┌─────────────┐    webhook     ┌─────────────┐    Telegram     ┌─────────────┐
│    VPS 1    │ ─────────────> │     n8n     │ ──────────────> │  Telegram   │
│ webhook_bot │                │   Server    │                 │     Bot     │
│             │ <───────────── │             │ <────────────── │   (Single)  │
└─────────────┘    commands    └─────────────┘    user input   └─────────────┘
                                      │
┌─────────────┐    webhook            │
│    VPS 2    │ ─────────────────────>│
│ webhook_bot │                       │
│             │ <─────────────────────│
└─────────────┘    commands

┌─────────────┐
│    VPS N    │ ─────────────────────>│
│ webhook_bot │                       │
│             │ <─────────────────────│
└─────────────┘
```

## 📋 Prerequisites

### 1. n8n Installation
- **Self-hosted n8n**: Recommended for production
- **n8n Cloud**: Alternative for quick testing
- **Docker setup**: Most common deployment method

### 2. Telegram Bot Token
- Create a bot via [@BotFather](https://t.me/botfather)
- Get the bot token (format: `1234567890:ABCdefGHijKLmnoPQRStuVWXyz`)
- This will be your **single** bot for all VPSs

### 3. Domain/SSL
- Public domain pointing to your n8n instance
- SSL certificate (Let's Encrypt recommended)
- Example: `https://your-n8n-domain.com`

## 🔧 Step 1: Create Webhook Endpoints in n8n

### 1.1 VPS Status Receiver Webhook

This webhook receives status updates, notifications, and heartbeats from all VPSs.

#### Create the Webhook:
1. **Open n8n** → **New Workflow**
2. **Add Node** → **Trigger** → **Webhook**
3. **Configure Webhook Node**:
   - **Webhook URLs**: `Manual`
   - **HTTP Method**: `POST`
   - **Path**: `/webhook/gensyn/status`
   - **Authentication**: `None` (we handle auth in payload)
   - **Response**: `Respond to Webhook`

#### Webhook URL Format:
```
https://your-n8n-domain.com/webhook/gensyn/status
```

**Copy this URL** - you'll need it when configuring each VPS.

### 1.2 Command Sender (Optional)
For sending commands back to VPSs, we'll use HTTP Request nodes within workflows rather than separate webhooks.

## 🤖 Step 2: Configure Telegram Bot in n8n

### 2.1 Add Telegram Trigger
1. **Add Node** → **Trigger** → **Telegram Trigger**
2. **Configure**:
   - **Bot Token**: Your bot token from BotFather
   - **Additional Fields** → **Download Images**: `false`

### 2.2 Set Telegram Commands
In BotFather, set these commands for your bot:
```
start - 🚀 Start bot and show VPS list
vpses - 📋 Show available VPSs
help - ❓ Show help information
```

## 🔄 Step 3: Complete n8n Workflow Setup

### 3.1 Core Workflow Components

#### A. VPS State Management
```json
{
  "vps_list": [
    {
      "vps_id": "london-server",
      "vps_name": "London Server",
      "status": "online",
      "last_heartbeat": "2024-01-01T12:00:00Z",
      "webhook_url": "http://vps1-ip:8080/webhook/command",
      "auth_token": "vps1-auth-token"
    },
    {
      "vps_id": "ny-server", 
      "vps_name": "New York Server",
      "status": "online",
      "last_heartbeat": "2024-01-01T12:00:00Z",
      "webhook_url": "http://vps2-ip:8080/webhook/command",
      "auth_token": "vps2-auth-token"
    }
  ]
}
```

#### B. Message Flow
1. **Webhook receives VPS updates** → **Update VPS state** → **Notify if needed**
2. **Telegram user input** → **Show VPS selection** → **Route command** → **Send response**

## 📱 Step 4: Telegram Interface Design

### 4.1 Main Menu Structure
```
🤖 Gensyn Multi-VPS Manager

🖥️ Available VPSs:
├── 🟢 London Server (online)
├── 🟢 New York Server (online)  
└── 🔴 Tokyo Server (offline)

Select a VPS to manage:
[London] [New York] [Tokyo]
```

### 4.2 VPS-Specific Menu
```
🖥️ London Server Management

📊 Status: 🟢 Online (2m ago)
🌐 IP: 192.168.1.100
⚡ Gensyn: Running
🔒 VPN: Connected

Choose action:
[📊 Status] [▶️ Start] [⏹️ Stop]
[🌐 IP] [🔒 VPN On] [🔒 VPN Off]  
[📋 Logs] [🔄 Update] [⬅️ Back]
```

## 🛠️ Step 5: Webhook URL Configuration

### 5.1 URL Structure
For each VPS, you'll provide this webhook URL during setup:

```
https://your-n8n-domain.com/webhook/gensyn/status
```

### 5.2 VPS Configuration Example
When running `python webhook_config.py` on each VPS:

```bash
VPS Name (e.g., 'vps-1', 'london-server'): london-server
n8n Webhook URL: https://your-n8n-domain.com/webhook/gensyn/status
Webhook listening port (default: 8080): 8080
```

### 5.3 Authentication Tokens
Each VPS generates its own auth token. Store these in n8n for command routing:

```javascript
// In n8n, store VPS credentials
const vpsCredentials = {
  "london-server": {
    "webhook_url": "http://vps1-ip:8080/webhook/command",
    "auth_token": "abc123...generated-token"
  },
  "ny-server": {
    "webhook_url": "http://vps2-ip:8080/webhook/command", 
    "auth_token": "def456...generated-token"
  }
};
```

## 📡 Step 6: Webhook Payload Handling

### 6.1 Incoming Webhook Payloads
Your n8n webhook will receive these types of messages:

#### Status Update
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "message_type": "status_update",
  "vps_name": "london-server",
  "vps_id": "london-server", 
  "auth_token": "vps-auth-token",
  "data": {
    "gensyn_running": true,
    "vpn_status": "connected",
    "api_status": "running",
    "system": {
      "cpu_percent": 25.5,
      "memory_percent": 60.2,
      "disk_percent": 45.8
    }
  }
}
```

#### Notification
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "message_type": "notification",
  "vps_name": "london-server",
  "vps_id": "london-server",
  "auth_token": "vps-auth-token", 
  "data": {
    "notification_type": "ip_change",
    "message": "IP changed: 192.168.1.100",
    "priority": "normal"
  }
}
```

#### Heartbeat
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "message_type": "heartbeat",
  "vps_name": "london-server", 
  "vps_id": "london-server",
  "auth_token": "vps-auth-token",
  "data": {
    "uptime": "24.5h",
    "system_info": {
      "cpu_percent": 15.2,
      "memory_percent": 45.1,
      "disk_percent": 42.3
    }
  }
}
```

### 6.2 Processing Logic in n8n

#### Webhook Processing Node (Code)
```javascript
// Validate authentication
const expectedTokens = {
  "london-server": "token1",
  "ny-server": "token2"
  // Add all your VPS tokens here
};

const payload = $input.all()[0].json;
const vpsId = payload.vps_id;
const receivedToken = payload.auth_token;

if (!expectedTokens[vpsId] || expectedTokens[vpsId] !== receivedToken) {
  return [{ 
    json: { 
      error: "Invalid authentication",
      vps_id: vpsId,
      status: 401
    }
  }];
}

// Update VPS state based on message type
const messageType = payload.message_type;
const vpsData = payload.data;

switch(messageType) {
  case 'heartbeat':
    // Update last seen timestamp
    return [{
      json: {
        action: 'update_heartbeat',
        vps_id: vpsId,
        timestamp: payload.timestamp,
        system_info: vpsData.system_info
      }
    }];
    
  case 'notification':
    // Forward high priority notifications to Telegram
    if (vpsData.priority === 'high') {
      return [{
        json: {
          action: 'send_telegram_alert', 
          vps_name: payload.vps_name,
          message: vpsData.message,
          priority: vpsData.priority
        }
      }];
    }
    break;
    
  case 'status_update':
    // Update VPS status in state
    return [{
      json: {
        action: 'update_vps_status',
        vps_id: vpsId,
        status_data: vpsData
      }
    }];
    
  case 'reward_update':
    // Send reward notification to Telegram
    return [{
      json: {
        action: 'send_reward_notification',
        vps_name: payload.vps_name,
        message: vpsData.message,
        reward_data: vpsData
      }
    }];
}

return [{ json: { status: 'processed', message_type: messageType } }];
```

## 🎯 Step 7: Command Routing to VPS

### 7.1 Command Sending Logic
```javascript
// Send command to specific VPS
const vpsId = $json.selected_vps;
const command = $json.command;
const parameters = $json.parameters || {};

// Get VPS webhook URL and auth token
const vpsConfig = {
  "london-server": {
    "webhook_url": "http://vps1-ip:8080/webhook/command",
    "auth_token": "token1"
  },
  "ny-server": {
    "webhook_url": "http://vps2-ip:8080/webhook/command", 
    "auth_token": "token2"
  }
};

const config = vpsConfig[vpsId];
if (!config) {
  return [{ json: { error: `VPS ${vpsId} not found` } }];
}

// Prepare command payload
const commandPayload = {
  command: command,
  parameters: parameters,
  auth_token: config.auth_token,
  timestamp: new Date().toISOString(),
  request_id: `${vpsId}-${Date.now()}`
};

return [{
  json: commandPayload,
  headers: {
    'Content-Type': 'application/json'
  },
  url: config.webhook_url
}];
```

### 7.2 HTTP Request Node Configuration
- **Method**: `POST`
- **URL**: `{{ $json.url }}` (from previous node)
- **Headers**: `{{ $json.headers }}`
- **Body**: `{{ JSON.stringify($json) }}`
- **Timeout**: `30000` (30 seconds)

## 📊 Step 8: State Management

### 8.1 VPS State Storage
Use n8n's built-in data storage or connect to external database:

```javascript
// Store VPS state
const vpsState = await this.helpers.getWorkflowStaticData('global');

if (!vpsState.vpsList) {
  vpsState.vpsList = {};
}

const vpsId = $json.vps_id;
vpsState.vpsList[vpsId] = {
  name: $json.vps_name,
  status: 'online',
  last_heartbeat: new Date().toISOString(),
  last_status: $json.status_data,
  webhook_url: $json.webhook_url,
  // Don't store auth tokens in static data for security
};

return [{ json: { updated: vpsId, state: vpsState.vpsList[vpsId] } }];
```

### 8.2 VPS List Generation
```javascript
// Generate VPS list for Telegram menu
const vpsState = await this.helpers.getWorkflowStaticData('global');
const vpsList = vpsState.vpsList || {};

const buttons = [];
const vpsArray = Object.entries(vpsList).map(([id, data]) => {
  const status = data.status === 'online' ? '🟢' : '🔴';
  const lastSeen = new Date(data.last_heartbeat);
  const timeDiff = Math.floor((Date.now() - lastSeen.getTime()) / 1000 / 60);
  
  return {
    id: id,
    name: data.name,
    status: status,
    display: `${status} ${data.name} (${timeDiff}m ago)`,
    online: data.status === 'online' && timeDiff < 10
  };
});

// Create inline keyboard
const keyboard = vpsArray.map(vps => [{
  text: vps.display,
  callback_data: `select_vps_${vps.id}`
}]);

return [{
  json: {
    message: "🤖 *Gensyn Multi-VPS Manager*\n\nSelect a VPS to manage:",
    keyboard: keyboard,
    vps_list: vpsArray
  }
}];
```

## 🔒 Step 9: Security Configuration

### 9.1 Authentication Validation
```javascript
// Validate VPS authentication
const VALID_TOKENS = {
  // Store these securely - consider using n8n credentials
  "london-server": process.env.LONDON_SERVER_TOKEN,
  "ny-server": process.env.NY_SERVER_TOKEN
};

function validateAuth(vpsId, token) {
  return VALID_TOKENS[vpsId] === token;
}
```

### 9.2 Rate Limiting
```javascript
// Simple rate limiting per VPS
const rateLimits = await this.helpers.getWorkflowStaticData('global');
if (!rateLimits.requests) rateLimits.requests = {};

const vpsId = $json.vps_id;
const now = Date.now();
const windowMs = 60000; // 1 minute
const maxRequests = 60; // 60 requests per minute

if (!rateLimits.requests[vpsId]) {
  rateLimits.requests[vpsId] = [];
}

// Clean old requests
rateLimits.requests[vpsId] = rateLimits.requests[vpsId]
  .filter(time => now - time < windowMs);

if (rateLimits.requests[vpsId].length >= maxRequests) {
  return [{ json: { error: "Rate limit exceeded", status: 429 } }];
}

rateLimits.requests[vpsId].push(now);
return [{ json: { status: "ok" } }];
```

## 🚨 Step 10: Error Handling & Monitoring

### 10.1 VPS Offline Detection
```javascript
// Check for offline VPSs
const vpsState = await this.helpers.getWorkflowStaticData('global');
const vpsList = vpsState.vpsList || {};
const now = Date.now();
const offlineThreshold = 10 * 60 * 1000; // 10 minutes

const offlineVpses = Object.entries(vpsList)
  .filter(([id, data]) => {
    const lastSeen = new Date(data.last_heartbeat).getTime();
    return now - lastSeen > offlineThreshold;
  })
  .map(([id, data]) => ({
    id,
    name: data.name,
    last_seen: data.last_heartbeat
  }));

if (offlineVpses.length > 0) {
  return [{
    json: {
      action: 'send_offline_alert',
      offline_vpses: offlineVpses,
      message: `⚠️ VPSs offline: ${offlineVpses.map(v => v.name).join(', ')}`
    }
  }];
}

return [{ json: { status: 'all_online' } }];
```

### 10.2 Error Notification
```javascript
// Handle command execution errors
const response = $json;

if (!response.success) {
  const errorMessage = `❌ Command failed on ${response.vps_name}:\n\`${response.result}\``;
  
  return [{
    json: {
      action: 'send_error_notification',
      chat_id: $json.chat_id,
      message: errorMessage,
      parse_mode: 'Markdown'
    }
  }];
}

// Success response
const successMessage = `✅ Command executed on ${response.vps_name}:\n\`${response.result}\``;

return [{
  json: {
    action: 'send_success_notification', 
    chat_id: $json.chat_id,
    message: successMessage,
    parse_mode: 'Markdown'
  }
}];
```

## 📋 Step 11: Testing the Setup

### 11.1 Test Webhook Reception
1. **Configure one VPS** with your webhook URL
2. **Start the webhook bot** on that VPS
3. **Check n8n execution logs** for incoming heartbeats
4. **Verify VPS appears** in your Telegram bot

### 11.2 Test Command Routing
1. **Send a command** via Telegram (e.g., "Check IP")
2. **Verify command reaches VPS** (check VPS logs)
3. **Confirm response** appears in Telegram
4. **Test error handling** with invalid commands

### 11.3 Test Multiple VPS
1. **Configure second VPS** with same webhook URL but different name
2. **Verify both VPSs appear** in Telegram menu
3. **Test command routing** to specific VPS
4. **Confirm isolation** (commands only go to selected VPS)

## 🎛️ Step 12: Production Deployment

### 12.1 Environment Variables
Set these in your n8n environment:
```bash
# VPS Authentication Tokens
LONDON_SERVER_TOKEN=generated-token-1
NY_SERVER_TOKEN=generated-token-2

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token

# Admin Chat ID (for alerts)
ADMIN_CHAT_ID=your-telegram-user-id
```

### 12.2 Monitoring Setup
- **Enable n8n logs** for webhook nodes
- **Set up alerts** for VPS offline detection
- **Monitor webhook endpoint** health
- **Track command response times**

### 12.3 Backup Configuration
- **Export n8n workflows** regularly
- **Document VPS token mappings**
- **Backup webhook URLs** and configurations

## 🔧 Troubleshooting

### Common Issues

#### 1. Webhook Not Receiving Data
- **Check URL**: Verify webhook URL in VPS config
- **Check SSL**: Ensure HTTPS is working
- **Check firewall**: Verify n8n is accessible
- **Check logs**: Review n8n execution logs

#### 2. Authentication Failures
- **Verify tokens**: Check VPS auth tokens match n8n
- **Check encoding**: Ensure tokens are not modified
- **Review logs**: Check webhook server logs on VPS

#### 3. Commands Not Reaching VPS
- **Check VPS status**: Ensure VPS webhook server is running
- **Verify IP/port**: Confirm VPS webhook endpoint is accessible
- **Check authentication**: Verify auth tokens for outbound commands
- **Review timeouts**: Check command timeout settings

#### 4. Telegram Bot Not Responding
- **Check bot token**: Verify Telegram bot token in n8n
- **Check webhook**: Ensure Telegram webhook is set correctly
- **Review permissions**: Verify bot has necessary permissions
- **Check rate limits**: Ensure not hitting Telegram API limits

### Debug Commands
```bash
# Test VPS webhook endpoint
curl -X POST http://vps-ip:8080/webhook/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "check_ip",
    "auth_token": "your-vps-token",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }'

# Test n8n webhook endpoint  
curl -X POST https://your-n8n-domain.com/webhook/gensyn/status \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "heartbeat",
    "vps_id": "test-vps",
    "auth_token": "test-token",
    "data": {"uptime": "1h"}
  }'
```

---

## 📚 Additional Resources

- **n8n Documentation**: https://docs.n8n.io/
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Webhook Best Practices**: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
- **n8n Security Guide**: https://docs.n8n.io/hosting/security/

This completes the n8n setup guide. The next step is to create an importable workflow file that implements this architecture.

