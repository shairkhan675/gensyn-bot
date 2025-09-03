# n8n Workflow Configuration Guide

This guide explains how to configure the imported n8n workflow for Gensyn Bot multi-VPS management.

## 📦 Import the Workflow

### Step 1: Import Workflow File
1. **Open your n8n instance**
2. **Click "Import from file"** or **Workflows → Import**
3. **Select** `gensyn-multi-vps-workflow.json`
4. **Click "Import"**

The workflow will be imported with all nodes connected, but you'll need to configure several components.

## 🔧 Required Configuration

### Step 2: Set Environment Variables

Before configuring the workflow, set these environment variables in your n8n deployment:

#### For Docker/Docker Compose:
```bash
# .env file or docker-compose.yml
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
ADMIN_CHAT_ID=your-telegram-user-id-here
```

#### For Self-hosted n8n:
```bash
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token-here"
export ADMIN_CHAT_ID="your-telegram-user-id-here"
```

#### For n8n Cloud:
1. **Go to Settings** → **Environment Variables**
2. **Add**:
   - `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
   - `ADMIN_CHAT_ID`: Your Telegram user ID (get from @userinfobot)

### Step 3: Configure VPS Authentication Tokens

You need to add the authentication tokens from each VPS to the workflow.

#### 3.1 Get Tokens from Each VPS
On each VPS, after running `python webhook_config.py`, get the auth token:

```bash
# On VPS
python webhook_config.py --status
# Or check the config file
cat /root/gensyn-bot/webhook_config.json | grep auth_token
```

#### 3.2 Add Tokens to Workflow
1. **Open the imported workflow**
2. **Find the "Process VPS Webhook" node** (code node)
3. **Edit the `expectedTokens` object**:

```javascript
// Replace this section in the "Process VPS Webhook" node:
const expectedTokens = {
  // Add your VPS tokens here - get them from each VPS webhook_config.json
  // Format: "vps-id": "auth-token"
  "london-server": "your-london-server-token-here",
  "ny-server": "your-ny-server-token-here",
  "tokyo-server": "your-tokyo-server-token-here"
  // Add more VPSs as needed
};
```

### Step 4: Configure VPS Command Routing

#### 4.1 Add VPS Webhook URLs
1. **Find the "Route Command to VPS" node** (code node)
2. **Edit the `vpsConfigs` object**:

```javascript
// Replace this section in the "Route Command to VPS" node:
const vpsConfigs = {
  // Format: "vps-id": { "webhook_url": "http://vps-ip:port/webhook/command", "auth_token": "token" }
  "london-server": {
    "webhook_url": "http://192.168.1.100:8080/webhook/command",
    "auth_token": "your-london-server-token-here"
  },
  "ny-server": {
    "webhook_url": "http://45.67.89.123:8080/webhook/command", 
    "auth_token": "your-ny-server-token-here"
  },
  "tokyo-server": {
    "webhook_url": "http://98.76.54.321:8080/webhook/command",
    "auth_token": "your-tokyo-server-token-here"
  }
  // Add more VPSs as needed
};
```

#### 4.2 How to Get VPS IPs and Ports
On each VPS:
```bash
# Get current IP
curl -s https://api.ipify.org

# Check webhook port (default is 8080)
python webhook_config.py --status
```

## 🌐 Configure Webhook URL

### Step 5: Get Your n8n Webhook URL

1. **Go to the imported workflow**
2. **Click on the "VPS Status Webhook" trigger node**
3. **Copy the webhook URL** (it will look like):
   ```
   https://your-n8n-domain.com/webhook/gensyn/status
   ```

### Step 6: Configure Each VPS

Run this on **each VPS** you want to manage:

```bash
cd /root/gensyn-bot

# Configure webhook (if not done already)
python webhook_config.py

# When prompted, enter:
# - VPS Name: london-server (or unique name for each VPS)
# - Webhook URL: https://your-n8n-domain.com/webhook/gensyn/status
# - Port: 8080 (or your preferred port)
```

## 🧪 Testing the Setup

### Step 7: Test Webhook Reception

1. **Start one VPS webhook bot**:
   ```bash
   python start_webhook_bot.py start
   ```

2. **Check n8n execution logs**:
   - Go to **Executions** in n8n
   - You should see executions from the webhook trigger
   - Look for heartbeat messages every 5 minutes

3. **Check VPS appears in Telegram**:
   - Open your Telegram bot
   - Send `/start`
   - You should see the VPS listed

### Step 8: Test Command Execution

1. **In Telegram bot**, send `/start`
2. **Select your VPS** from the list
3. **Click "Check IP"** or another simple command
4. **Verify response** appears in Telegram
5. **Check VPS logs** to confirm command was received:
   ```bash
   tail -f /root/webhook_server.log
   ```

## 🔧 Advanced Configuration

### Custom Commands

To add custom commands, modify the "Route Command to VPS" node:

```javascript
// In the parameters section, add custom logic:
if (command === 'custom_command') {
  parameters = { 
    custom_param: 'value',
    another_param: 123 
  };
}
```

Then implement the command handler on each VPS in `webhook_server.py`.

### Custom Notifications

To modify notification behavior, edit the "Should Send Alert?" node conditions:

```javascript
// Add custom alert conditions
if (input.notification_type === 'custom_alert') {
  result.send_alert = true;
}
```

### VPS Grouping

To group VPSs by region or type, modify the "Generate VPS Menu" node:

```javascript
// Group VPSs by region
const regions = {};
vpsList.forEach(vps => {
  const region = vps.id.split('-')[0]; // e.g., 'london-server' -> 'london'
  if (!regions[region]) regions[region] = [];
  regions[region].push(vps);
});

// Create region-based keyboard
const keyboard = Object.entries(regions).map(([region, vpses]) => 
  vpses.map(vps => ({
    text: vps.display,
    callback_data: `select_vps_${vps.id}`
  }))
);
```

## 🔐 Security Best Practices

### 1. Secure Token Storage

Instead of hardcoding tokens in workflow nodes, use n8n credentials:

1. **Go to Settings** → **Credentials**
2. **Create new credential** → **Generic**
3. **Add your VPS tokens**
4. **Reference in workflow**:
   ```javascript
   const credentials = await this.getCredentials('your-credential-name');
   const token = credentials.vps_token;
   ```

### 2. IP Whitelisting

Configure your VPS firewalls to only allow n8n webhook requests:

```bash
# On each VPS, allow only your n8n server IP
ufw allow from YOUR_N8N_SERVER_IP to any port 8080
```

### 3. HTTPS Enforcement

Ensure all webhook communications use HTTPS:
- Use SSL certificates for your n8n instance
- Consider using Cloudflare or similar for additional protection

## 📊 Monitoring Setup

### Workflow Monitoring

1. **Enable workflow error notifications**:
   - Go to **Workflow Settings**
   - Enable **Error Workflow**
   - Set up error handling

2. **Monitor execution times**:
   - Check **Executions** regularly
   - Look for slow or failed executions
   - Set up alerts for failures

### VPS Health Monitoring

The workflow automatically monitors VPS health through heartbeats:

- **Online threshold**: VPS is considered online if heartbeat received within 10 minutes
- **Offline alerts**: Automatic alerts when VPS goes offline
- **System metrics**: CPU, RAM, and disk usage tracked

## 🔄 Scaling to More VPSs

### Adding New VPSs

1. **Configure new VPS**:
   ```bash
   python webhook_config.py
   # Use same webhook URL, unique VPS name
   ```

2. **Update n8n workflow**:
   - Add token to "Process VPS Webhook" node
   - Add config to "Route Command to VPS" node

3. **Test new VPS**:
   - Start webhook bot on new VPS
   - Verify it appears in Telegram menu

### Bulk Management

For managing many VPSs, consider:

1. **Environment-based configuration**: Store VPS configs in environment variables
2. **External database**: Store VPS details in database instead of workflow static data
3. **API-based management**: Create API endpoints for adding/removing VPSs

## 🐛 Troubleshooting

### Common Issues

#### 1. VPS Not Appearing in Menu
- **Check webhook URL** in VPS config
- **Verify auth token** in n8n workflow
- **Check n8n execution logs** for webhook errors
- **Confirm VPS webhook bot is running**

#### 2. Commands Not Working
- **Verify VPS IP and port** in workflow config
- **Check VPS firewall** settings
- **Confirm auth tokens** match
- **Review command timeout** settings

#### 3. Authentication Errors
- **Double-check tokens** in both VPS and n8n
- **Ensure tokens weren't truncated** during copy/paste
- **Verify token format** (no extra spaces/characters)

#### 4. Telegram Bot Not Responding
- **Check bot token** in environment variables
- **Verify bot permissions** with @BotFather
- **Check chat ID** for admin notifications
- **Review Telegram API limits**

### Debug Commands

```bash
# Test VPS webhook endpoint
curl -X POST http://vps-ip:8080/webhook/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "check_ip",
    "auth_token": "your-token",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }'

# Test n8n webhook endpoint
curl -X POST https://your-n8n-domain.com/webhook/gensyn/status \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "heartbeat",
    "vps_id": "test-vps",
    "vps_name": "Test VPS",
    "auth_token": "test-token",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "data": {"uptime": "1h"}
  }'
```

---

## 🎉 Final Steps

Once everything is configured:

1. ✅ **All VPSs configured** with webhook URL
2. ✅ **All tokens added** to n8n workflow  
3. ✅ **Environment variables set** in n8n
4. ✅ **Workflow activated** in n8n
5. ✅ **Telegram bot tested** with multiple VPSs
6. ✅ **Commands working** on all VPSs
7. ✅ **Monitoring setup** and alerts configured

You now have a fully functional multi-VPS management system through a single Telegram bot! 🚀

## 📞 Need Help?

- **Check execution logs** in n8n for detailed error information
- **Review VPS logs**: `/root/webhook_bot.log`, `/root/webhook_server.log`
- **Test individual components** using the debug commands above
- **Verify network connectivity** between n8n and VPSs

