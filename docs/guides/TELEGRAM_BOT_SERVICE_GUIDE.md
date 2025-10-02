# Telegram Bot Service Management Guide

This guide explains how to manage the Radiator Telegram Bot as a systemd service.

## Overview

The Telegram bot is configured to run as a systemd user service, which means:
- It starts automatically when you log in
- It restarts automatically if it crashes
- It runs in the background
- It can be managed with standard systemd commands

## Service Management Commands

### Basic Service Control

```bash
# Check if the service is running
make telegram-service-status
# or
systemctl --user status radiator-telegram-bot.service

# Start the service
make telegram-service-start
# or
systemctl --user start radiator-telegram-bot.service

# Stop the service
make telegram-service-stop
# or
systemctl --user stop radiator-telegram-bot.service

# Restart the service
make telegram-service-restart
# or
systemctl --user restart radiator-telegram-bot.service
```

### Auto-Start Configuration

```bash
# Enable auto-start (service starts automatically on login)
systemctl --user enable radiator-telegram-bot.service

# Disable auto-start
systemctl --user disable radiator-telegram-bot.service

# Check if auto-start is enabled
systemctl --user is-enabled radiator-telegram-bot.service
```

### Logs and Monitoring

```bash
# View real-time logs
make telegram-service-logs
# or
journalctl --user -u radiator-telegram-bot.service -f

# View recent logs (last 50 lines)
journalctl --user -u radiator-telegram-bot.service -n 50

# View logs from today
journalctl --user -u radiator-telegram-bot.service --since today

# View logs with timestamps
journalctl --user -u radiator-telegram-bot.service -o short-iso
```

## Service Files

### Service Configuration
- **File**: `~/.config/systemd/user/radiator-telegram-bot.service`
- **Type**: User service (runs under your user account)
- **Auto-restart**: Enabled (restarts on failure)

### Startup Script
- **File**: `start-telegram-bot.sh`
- **Purpose**: Wrapper script that sets up the environment
- **Location**: Project root directory

## Troubleshooting

### Service Won't Start

1. **Check service status**:
   ```bash
   systemctl --user status radiator-telegram-bot.service
   ```

2. **Check logs for errors**:
   ```bash
   journalctl --user -u radiator-telegram-bot.service -n 20
   ```

3. **Test bot manually**:
   ```bash
   make telegram-test
   ```

4. **Check file permissions**:
   ```bash
   ls -la start-telegram-bot.sh
   chmod +x start-telegram-bot.sh
   ```

### Service Keeps Restarting

1. **Check for configuration errors**:
   ```bash
   journalctl --user -u radiator-telegram-bot.service --since "1 hour ago"
   ```

2. **Verify environment variables**:
   ```bash
   cat .env | grep TELEGRAM
   ```

3. **Test bot connection**:
   ```bash
   make telegram-test
   ```

### Service Not Auto-Starting

1. **Check if enabled**:
   ```bash
   systemctl --user is-enabled radiator-telegram-bot.service
   ```

2. **Enable the service**:
   ```bash
   systemctl --user enable radiator-telegram-bot.service
   ```

3. **Check user systemd session**:
   ```bash
   systemctl --user is-system-running
   ```

## Manual Bot Control

If you prefer to run the bot manually instead of as a service:

```bash
# Stop the service first
make telegram-service-stop

# Run bot manually
make telegram-bot

# Test bot connection
make telegram-test

# Reset bot state (re-send all files)
make telegram-reset
```

## Service Configuration Details

### Current Configuration

```ini
[Unit]
Description=Radiator Telegram Bot for Reports Monitoring
After=network.target
Wants=network.target

[Service]
Type=simple
WorkingDirectory=/home/vm/dev/radiator
ExecStart=/home/vm/dev/radiator/start-telegram-bot.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

### Key Settings

- **Restart=always**: Service restarts automatically on failure
- **RestartSec=10**: Wait 10 seconds before restarting
- **Type=simple**: Simple service type (not forking)
- **WorkingDirectory**: Sets the working directory for the service

## Monitoring and Maintenance

### Regular Checks

1. **Check service health**:
   ```bash
   make telegram-service-status
   ```

2. **Monitor logs for issues**:
   ```bash
   make telegram-service-logs
   ```

3. **Test bot functionality**:
   ```bash
   make telegram-test
   ```

### Performance Monitoring

```bash
# Check memory usage
systemctl --user show radiator-telegram-bot.service --property=MemoryCurrent

# Check CPU usage
systemctl --user show radiator-telegram-bot.service --property=CPUUsageNSec

# Check service uptime
systemctl --user show radiator-telegram-bot.service --property=ActiveEnterTimestamp
```

## Integration with Reports

The bot automatically monitors the `reports/` directory and sends new files to Telegram. When you generate reports:

1. **Status Change Reports**: `make generate-status-report`
2. **Time to Market Reports**: `make generate-time-to-market-report`
3. **Bot automatically detects and sends new files**

No manual intervention required - the bot handles everything automatically!

## Security Notes

- The service runs under your user account (not root)
- It has access only to the project directory
- No special privileges required
- Logs are stored in systemd journal (user-scoped)
