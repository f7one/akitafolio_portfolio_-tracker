# 🚀 Akitafolio Deployment Guide - Server 194.87.83.103

## 📋 Prerequisites

Before deploying, ensure you have:

1. **SSH Access** to the server
   - IP: `194.87.83.103`
   - Username (usually `root` or your username)
   - Password or SSH key

2. **Bot Configuration**
   - `.env` file with your API keys
   - Bot tested locally

3. **Local Tools**
   - SSH client installed
   - Terminal access

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

**Note:** You'll be prompted for SSH password/key.

---

### Option 2: Manual Deployment (Step-by-Step)

#### Step 1: Connect to Server
```bash
ssh root@194.87.83.103
```

#### Step 2: Prepare Server
```bash
# Update system
apt-get update
apt-get upgrade -y

# Install Python and dependencies
apt-get install -y python3 python3-pip python3-venv git

# Create directory for bot
mkdir -p /opt/tg-balance-bot
cd /opt/tg-balance-bot
```

#### Step 3: Upload Bot Files

**From your local machine (new terminal):**
```bash
# Navigate to bot directory
cd "/Users/nikitazinevich/Desktop/Desktop/Crusor projects/tg-balance-bot"

# Create deployment package
tar -czf bot-deployment.tar.gz \
    bot.py \
    requirements.txt \
    .env \
    --exclude='__pycache__' \
    --exclude='*.pyc'

# Upload to server
scp bot-deployment.tar.gz root@194.87.83.103:/opt/tg-balance-bot/

# OR upload individual files
scp bot.py root@194.87.83.103:/opt/tg-balance-bot/
scp requirements.txt root@194.87.83.103:/opt/tg-balance-bot/
scp .env root@194.87.83.103:/opt/tg-balance-bot/
```

#### Step 4: Setup on Server

**Back in server SSH session:**
```bash
cd /opt/tg-balance-bot

# Extract if using tar
tar -xzf bot-deployment.tar.gz
rm bot-deployment.tar.gz

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Test Bot
```bash
# Test run
python bot.py
```

Press `Ctrl+C` to stop after confirming it works.

#### Step 6: Create Systemd Service

```bash
# Create service file
cat > /etc/systemd/system/tg-balance-bot.service << 'EOF'
[Unit]
Description=Telegram Crypto Balance Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tg-balance-bot
Environment="PATH=/opt/tg-balance-bot/venv/bin"
ExecStart=/opt/tg-balance-bot/venv/bin/python /opt/tg-balance-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### Step 7: Start Service

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

### Check Bot Status
```bash
ssh root@194.87.83.103 'systemctl status tg-balance-bot'
```

### View Live Logs
```bash
ssh root@194.87.83.103 'journalctl -u tg-balance-bot -f'
```

### View Last 100 Lines of Logs
```bash
ssh root@194.87.83.103 'journalctl -u tg-balance-bot -n 100'
```

### Restart Bot
```bash
ssh root@194.87.83.103 'systemctl restart tg-balance-bot'
```

### Stop Bot
```bash
ssh root@194.87.83.103 'systemctl stop tg-balance-bot'
```

### Start Bot
```bash
ssh root@194.87.83.103 'systemctl start tg-balance-bot'
```

---

## 🔄 Updating the Bot

### Method 1: Using Deployment Script
```bash
# From local machine
./deploy.sh
```

### Method 2: Manual Update
```bash
# Upload new bot.py
scp bot.py root@194.87.83.103:/opt/tg-balance-bot/

# Restart service
ssh root@194.87.83.103 'systemctl restart tg-balance-bot'
```

---

## 🔧 Troubleshooting

### Bot Not Starting

**Check logs:**
```bash
ssh root@194.87.83.103 'journalctl -u tg-balance-bot -n 50'
```

**Common issues:**
1. Missing `.env` file
2. Invalid API keys
3. Python dependencies not installed
4. Port already in use

### Check if Bot is Running
```bash
ssh root@194.87.83.103 'ps aux | grep bot.py'
```

### Check Python Environment
```bash
ssh root@194.87.83.103 'cd /opt/tg-balance-bot && source venv/bin/activate && python --version && pip list'
```

### Reinstall Dependencies
```bash
ssh root@194.87.83.103 << 'EOF'
cd /opt/tg-balance-bot
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
systemctl restart tg-balance-bot
EOF
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

### 2. Secure .env File
```bash
chmod 600 /opt/tg-balance-bot/.env
```

### 3. Setup Firewall
```bash
# Install UFW
apt-get install -y ufw

# Allow SSH
ufw allow ssh

# Enable firewall
ufw enable
```

---

## 📊 Server Requirements

**Minimum:**
- CPU: 1 core
- RAM: 512 MB
- Disk: 1 GB
- OS: Ubuntu 20.04+ / Debian 10+

**Recommended:**
- CPU: 2 cores
- RAM: 1 GB
- Disk: 5 GB
- OS: Ubuntu 22.04 LTS

---

## 🎯 Quick Deploy Commands

### Deploy Bot (All-in-One)
```bash
ssh root@194.87.83.103 << 'ENDSSH'
cd /opt/tg-balance-bot || mkdir -p /opt/tg-balance-bot
cd /opt/tg-balance-bot
# Upload files first, then run:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
systemctl restart tg-balance-bot
ENDSSH
```

---

## ✅ Post-Deployment Checklist

- [ ] Bot service is running (`systemctl status tg-balance-bot`)
- [ ] Logs show no errors (`journalctl -u tg-balance-bot -n 50`)
- [ ] Bot responds to `/start` in Telegram
- [ ] `/portfolio` command works
- [ ] `/eth` and `/btc` commands work
- [ ] Service starts on reboot (`systemctl is-enabled tg-balance-bot`)
- [ ] `.env` file is secure (`ls -la /opt/tg-balance-bot/.env`)

---

## 📝 Notes

- **Server IP:** 194.87.83.103
- **Bot Directory:** /opt/tg-balance-bot
- **Service Name:** tg-balance-bot
- **Log Location:** `journalctl -u tg-balance-bot`
- **Auto-restart:** Yes (on failure)
- **Start on boot:** Yes

---

## 🆘 Support Commands

### One-Line Status Check
```bash
ssh root@194.87.83.103 'systemctl status tg-balance-bot && journalctl -u tg-balance-bot -n 10'
```

### One-Line Restart
```bash
ssh root@194.87.83.103 'systemctl restart tg-balance-bot && sleep 2 && systemctl status tg-balance-bot'
```

### One-Line Full Log
```bash
ssh root@194.87.83.103 'journalctl -u tg-balance-bot --no-pager'
```

---

**Your bot will be running 24/7 on the server! 🚀**
