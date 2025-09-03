# Gensyn Bot - Webhook Architecture

This document describes the new webhook-based architecture for multi-VPS management via a single Telegram bot using n8n as a central hub.

## 🏗️ Architecture Overview

### Previous Architecture (Legacy)
- Each VPS runs its own bot instance with Telegram polling
- Requires separate bot tokens per VPS
- Direct Telegram API communication
- Poor scalability for multiple VPSs

### New Architecture (Webhook-based)
- Each VPS sends status updates to n8n via HTTP webhooks
- Single Telegram bot (managed by n8n) for all VPS interactions
- n8n acts as central router and state manager
- Scalable to unlimited VPSs

```
┌─────────────┐    webhook     ┌─────────────┐    Telegram     ┌─────────────┐
│    VPS 1    │ ─────────────> │     n8n     │ ──────────────> │  Telegram   │
│             │                │   Server    │                 │     Bot     │
│ webhook_bot │ <───────────── │             │ <────────────── │             │
└─────────────┘    commands    └─────────────┘    user input   └─────────────┘
                                      │
┌─────────────┐    webhook            │
│    VPS 2    │ ─────────────────────>│
│             │                       │
│ webhook_bot │ <─────────────────────│
└─────────────┘    commands
```

## 📁 File Structure

```
gensyn-bot/
├── webhook_config.py          # Interactive webhook configuration
├── webhook_client.py          # Sends updates to n8n
├── webhook_server.py          # Receives commands from n8n
├── webhook_bot.py             # Main webhook bot integrating all components
├── webhook_reward.py          # Webhook-based reward monitoring
├── start_webhook_bot.py       # Startup script with process management
├── bot_manager.py             # Updated management interface
├── bot.py                     # Legacy bot (preserved for backwards compatibility)
├── reward.py                  # Legacy reward monitor
├── signup.py                  # Gensyn login automation
└── requirements.txt           # Updated dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Update Python packages
pip install -r requirements.txt

# Or use the bot manager
python bot_manager.py
# Choose option 13: Install requirements.txt
```

### 2. Configure Webhook Bot
```bash
# Interactive configuration
python webhook_config.py

# Or use the bot manager
python bot_manager.py
# Choose option 4: Setup Webhook Bot
```

You'll be prompted for:
- **VPS Name**: Friendly name (e.g., "london-server", "vps-1")
- **VPS ID**: Auto-generated from name (used for routing)
- **Webhook URL**: Your n8n webhook endpoint
- **Listening Port**: Port for incoming commands (default: 8080)
- **Auth Token**: Auto-generated security token

### 3. Start the Bot
```bash
# Using the startup script
python start_webhook_bot.py start

# Or use the bot manager
python bot_manager.py
# Choose option 7: Start Webhook Bot
```

### 4. Enable Auto-Start (Optional)
```bash
python bot_manager.py
# Choose option 10: Enable Bot on Boot
# Choose option 2: Webhook Bot Service
```

## 🔧 Configuration

### Webhook Configuration File
Located at `/root/gensyn-bot/webhook_config.json`:

```json
{
  "webhook_url": "https://your-n8n.domain.com/webhook/gensyn",
  "vps_name": "london-server",
  "vps_id": "london-server",
  "auth_token": "your-secure-token",
  "webhook_port": 8080,
  "enabled": true
}
```

### Configuration Commands
```bash
# View current configuration
python webhook_config.py --status

# Reconfigure
python webhook_config.py

# View via bot manager
python bot_manager.py
# Choose option 5: View Bot Configuration
```

## 📡 Webhook Communication Protocol

### Outbound Messages (VPS → n8n)

All messages include:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "message_type": "status_update|notification|reward_update|error_alert|command_response|log_update|heartbeat",
  "vps_name": "london-server",
  "vps_id": "london-server",
  "auth_token": "your-secure-token",
  "data": { /* message-specific data */ }
}
```

#### Message Types

1. **status_update**: General VPS status
2. **notification**: Alert notifications
3. **reward_update**: Gensyn reward/win changes
4. **error_alert**: Error notifications
5. **command_response**: Response to executed commands
6. **log_update**: Log entries
7. **heartbeat**: Keep-alive (every 5 minutes)

### Inbound Commands (n8n → VPS)

Commands sent to `http://vps-ip:port/webhook/command`:

```json
{
  "command": "check_ip|vpn_on|vpn_off|gensyn_status|start_gensyn|kill_gensyn|get_logs",
  "parameters": {
    "param1": "value1"
  },
  "auth_token": "your-secure-token",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "optional-unique-id"
}
```

#### Available Commands

| Command | Description | Parameters |
|---------|-------------|------------|
| `check_ip` | Get current public IP | None |
| `vpn_on` | Enable VPN | None |
| `vpn_off` | Disable VPN | None |
| `gensyn_status` | Get Gensyn status | None |
| `start_gensyn` | Start Gensyn node | `use_sync_backup`, `fresh_start` |
| `kill_gensyn` | Stop Gensyn node | None |
| `get_logs` | Get log files | `log_type`, `lines` |
| `gensyn_login` | Perform Gensyn login | `email`, `otp` |
| `set_autostart` | Setup autostart | None |
| `install_gensyn` | Install Gensyn | None |
| `soft_update` | Soft update Gensyn | None |
| `hard_update` | Hard update Gensyn | None |

### Health Check Endpoint

GET `http://vps-ip:port/health` returns:
```json
{
  "status": "healthy",
  "vps_id": "london-server",
  "vps_name": "london-server",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

## 🔒 Security

### Authentication
- All webhook communications use a secure token
- Tokens are automatically generated during setup
- Failed authentication attempts are logged

### Network Security
- Webhook server binds to `0.0.0.0` by default
- Consider using firewall rules to restrict access
- Use HTTPS for n8n webhook URLs when possible

### Token Management
```bash
# View current token
python webhook_config.py --status

# Regenerate token (reconfigure)
python webhook_config.py
```

## 📊 Monitoring & Logging

### Log Files
- `/root/webhook_bot.log` - Main bot operations
- `/root/webhook_client.log` - Outbound webhook calls
- `/root/webhook_server.log` - Inbound command processing
- `/root/webhook_reward.log` - Reward monitoring

### View Logs
```bash
# Use bot manager
python bot_manager.py
# Choose option 11: View Bot Logs

# Or directly
tail -f /root/webhook_bot.log
```

### Process Monitoring
```bash
# Check status
python start_webhook_bot.py status

# Via bot manager
python bot_manager.py
# Choose option 9: View Bot Status
```

## 🔄 Process Management

### Manual Control
```bash
# Start all components
python start_webhook_bot.py start

# Start without reward monitor
python start_webhook_bot.py start --no-reward-monitor

# Stop all
python start_webhook_bot.py stop

# Restart
python start_webhook_bot.py restart

# Check status
python start_webhook_bot.py status
```

### Systemd Service
```bash
# Setup service
python bot_manager.py
# Choose option 10, then option 2

# Control via systemd
systemctl status gensyn-webhook-bot
systemctl restart gensyn-webhook-bot
systemctl stop gensyn-webhook-bot
```

## 🐛 Troubleshooting

### Common Issues

1. **Webhook not configured**
   ```bash
   python webhook_config.py
   ```

2. **Port already in use**
   ```bash
   # Find process using port
   lsof -i :8080
   # Change port in configuration
   python webhook_config.py
   ```

3. **n8n not receiving webhooks**
   - Check webhook URL is correct
   - Verify authentication token
   - Check network connectivity
   - Review webhook_client.log

4. **Commands not executing**
   - Check webhook_server.log
   - Verify authentication
   - Ensure proper JSON format

### Debug Mode
```bash
# Start with verbose logging
python webhook_bot.py  # Direct execution shows more output
```

### Test Webhook Client
```bash
python webhook_client.py  # Runs test functions
```

## 🔄 Migration from Legacy Bot

### Backwards Compatibility
- Legacy bot (`bot.py`) remains functional
- Both bots can coexist during transition
- Gradual migration supported

### Migration Steps
1. Configure webhook bot: `python webhook_config.py`
2. Test webhook bot: `python start_webhook_bot.py start`
3. Verify functionality
4. Stop legacy bot: `python bot_manager.py` → option 8
5. Enable webhook bot autostart

### Rollback
```bash
# Stop webhook bot
python start_webhook_bot.py stop

# Start legacy bot
python bot_manager.py
# Choose option 6: Start Legacy Bot
```

## 🌐 n8n Integration

### Required n8n Workflows

1. **Webhook Receiver**: Receives status updates from VPSs
2. **Telegram Interface**: Single bot for all user interactions
3. **Command Router**: Routes commands to appropriate VPS
4. **State Manager**: Tracks VPS status and availability

### Example n8n Webhook Node Configuration
- **HTTP Method**: POST
- **Path**: `/webhook/gensyn`
- **Authentication**: None (handled in payload)
- **Response Mode**: Return Response

### VPS Selection Flow
1. User opens Telegram bot
2. Bot shows inline keyboard with available VPSs
3. User selects VPS
4. Bot shows VPS-specific commands
5. User selects command
6. n8n routes command to selected VPS
7. VPS executes and responds
8. n8n forwards response to user

## 📚 API Reference

### WebhookClient Methods
```python
client = WebhookClient()

# Send status update
client.send_status_update({
    "gensyn_running": True,
    "vpn_status": "connected"
})

# Send notification
client.send_notification("error", "VPN disconnected", "high")

# Send reward update
client.send_reward_update({
    "peer_name": "test peer",
    "reward_increase": 100
})
```

### WebhookServer Custom Handlers
```python
server = WebhookServer()

def custom_command(params):
    # Your custom logic here
    return "Command executed successfully"

server.register_command_handler("custom_cmd", custom_command)
```

## 🚀 Future Extensibility

The webhook architecture enables:

1. **AI/LLM Integration**: Easy to add intelligent automation
2. **Multi-Cloud Support**: Manage VPSs across different providers
3. **Advanced Monitoring**: Custom metrics and alerting
4. **Batch Operations**: Execute commands across multiple VPSs
5. **Web Dashboard**: Browser-based management interface

## 📝 License & Support

This is an enhanced version of the original gensyn-bot with webhook capabilities for multi-VPS management. All existing functionality is preserved while adding powerful new features for scalability and centralized management.

For issues or questions, please check the log files and troubleshooting section above.

