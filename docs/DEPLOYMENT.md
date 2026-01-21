# 🚀 Deployment Guide

Complete guide for deploying Akitafolio to a production server.

## 📋 Prerequisites

Before deploying, ensure you have:

1. **Server Access**
   - Linux server (Ubuntu 20.04+ recommended)
   - SSH access with root or sudo privileges
   - Minimum: 1 CPU, 512MB RAM, 1GB disk

2. **Configuration Files**
   - `.env` file with your API keys
   - Bot tested locally

3. **Required Software**
   - Python 3.8+
   - pip
   - virtualenv

---

## 🎯 Deployment Options

### Option 1: Automatic Deployment (Recommended)

Use the provided deployment script:

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Option 2: Manual Deployment

#### Step 1: Prepare Server

```bash
# Connect to server
ssh root@your-server-ip

# Update system
apt-get update && apt-get upgrade -y

# Install Python
apt-get install -y python3 python3-pip python3-venv git

# Create bot directory
mkdir -p /opt/tg-balance-bot
cd /opt/tg-balance-bot
```

#### Step 2: Upload Files

From your local machine:

```bash
# Upload bot files
scp -r akitafolio bot_refactored.py requirements.txt .env root@your-server-ip:/opt/tg-balance-bot/
```

#### Step 3: Setup Environment

```bash
# On server
cd /opt/tg-balance-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Test Bot

```bash
python bot_refactored.py
```

Press `Ctrl+C` after confirming it works.

#### Step 5: Create Systemd Service

```bash
cat > /etc/systemd/system/tg-balance-bot.service << 'EOF'
[Unit]
Description=Akitafolio - Multi-Chain Crypto Portfolio Tracker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tg-balance-bot
Environment="PATH=/opt/tg-balance-bot/venv/bin"
ExecStart=/opt/tg-balance-bot/venv/bin/python /opt/tg-balance-bot/bot_refactored.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### Step 6: Start Service

```bash
# Reload systemd
systemctl daemon-reload

# Enable service (start on boot)
systemctl enable tg-balance-bot

# Start service
systemctl start tg-balance-bot

# Check status
systemctl status tg-balance-bot
```

---

## 📊 Monitoring & Management

### Check Status
```bash
systemctl status tg-balance-bot
```

### View Logs
```bash
# Live logs
journalctl -u tg-balance-bot -f

# Last 100 lines
journalctl -u tg-balance-bot -n 100
```

### Restart Bot
```bash
systemctl restart tg-balance-bot
```

### Stop Bot
```bash
systemctl stop tg-balance-bot
```

---

## 🔄 Updating

### Method 1: Using Script
```bash
./deploy.sh
```

### Method 2: Manual Update
```bash
# Upload new files
scp -r akitafolio bot_refactored.py root@your-server-ip:/opt/tg-balance-bot/

# Restart service
ssh root@your-server-ip 'systemctl restart tg-balance-bot'
```

---

## 🔧 Troubleshooting

### Bot Not Starting

Check logs:
```bash
journalctl -u tg-balance-bot -n 50
```

Common issues:
1. Missing `.env` file
2. Invalid API keys
3. Python dependencies not installed
4. Missing akitafolio package

### Check Python Environment
```bash
cd /opt/tg-balance-bot
source venv/bin/activate
python --version
pip list
```

### Reinstall Dependencies
```bash
cd /opt/tg-balance-bot
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
systemctl restart tg-balance-bot
```

---

## 🔐 Security Best Practices

### 1. Use Non-Root User (Recommended)

```bash
# Create dedicated user
useradd -m -s /bin/bash botuser

# Move bot files
mv /opt/tg-balance-bot /home/botuser/
chown -R botuser:botuser /home/botuser/tg-balance-bot

# Update service file
sed -i 's/User=root/User=botuser/' /etc/systemd/system/tg-balance-bot.service
sed -i 's|/opt/tg-balance-bot|/home/botuser/tg-balance-bot|g' /etc/systemd/system/tg-balance-bot.service

# Reload and restart
systemctl daemon-reload
systemctl restart tg-balance-bot
```

### 2. Secure Environment File
```bash
chmod 600 /opt/tg-balance-bot/.env
```

### 3. Setup Firewall
```bash
apt-get install -y ufw
ufw allow ssh
ufw enable
```

---

## 📊 Server Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| CPU | 1 core | 2 cores |
| RAM | 512 MB | 1 GB |
| Disk | 1 GB | 5 GB |
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |

---

## ✅ Post-Deployment Checklist

- [ ] Bot service is running (`systemctl status tg-balance-bot`)
- [ ] Logs show no errors (`journalctl -u tg-balance-bot -n 50`)
- [ ] Bot responds to `/start` in Telegram
- [ ] `/portfolio` command works
- [ ] `/eth` and `/btc` commands work
- [ ] Service starts on reboot (`systemctl is-enabled tg-balance-bot`)
- [ ] `.env` file is secure (`ls -la .env`)

---

## 🆘 Quick Commands

### One-Line Status Check
```bash
ssh root@your-server-ip 'systemctl status tg-balance-bot && journalctl -u tg-balance-bot -n 10'
```

### One-Line Restart
```bash
ssh root@your-server-ip 'systemctl restart tg-balance-bot && sleep 2 && systemctl status tg-balance-bot'
```

### One-Line Full Log
```bash
ssh root@your-server-ip 'journalctl -u tg-balance-bot --no-pager | tail -100'
```

---

**Your bot will be running 24/7 on the server! 🚀**
