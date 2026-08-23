# 🚀 Deployment Guide

Complete guide for deploying Akitafolio to a production server.

> [!WARNING]
> The current `deploy.sh` is not approved for production: it archives `.env`,
> uses a predictable temporary path and installs a root service. Do not run it
> until Epic 5 in the [engineering roadmap](./ROADMAP.md) is complete.

## Current production migration

The accepted production topology is documented in
[ADR-0001](./adr/0001-separate-production-vps.md). Epic 0 moves the bot from the
shared VPS to the dedicated VPS `72.56.120.66` in Timeweb Cloud; its former Outline VPN must be
inventoried and removed only after explicit owner confirmation. The website and
its Docker runtime are out of scope.

### Migration invariants

- Verify the new VPS host-key fingerprint through the provider console before
  accepting it locally.
- Keep both the dedicated root SSH key and owner-approved root password login.
  Disable empty and keyboard-interactive passwords; require firewall controls,
  fail2ban, reduced authentication attempts and SSH log monitoring.
- Run the bot as a dedicated non-root `akitafolio` service account.
- Keep the systemd `EnvironmentFile` outside the code tree as `root:root` mode
  `0600`; keep application JSON data as `akitafolio` mode `0600`.
- Do not expose application ports and do not install the bot in the website's
  Docker/Compose environment.
- Do not copy the old `.env`. Create rotated production credentials only after
  sensitive URL logging is disabled.
- Transfer `saved_addresses.json` and `portfolio_history.json` directly over
  verified SSH while the old service is stopped; compare SHA-256 checksums.
- Never place `.env` or JSON data in Git, `/tmp`, or a deployment archive.
- Never run old and new Telegram polling processes at the same time.

### Cutover sequence

1. Harden SSH/firewall and create the service and operator accounts.
2. Install the reviewed application and pinned dependencies.
3. Configure systemd sandboxing and verify it with
   `systemd-analyze security tg-balance-bot.service`.
4. Stop the old service and calculate checksums without printing file contents.
5. Transfer and verify both JSON data files over SSH.
6. Add newly rotated secrets using a non-logging interactive mechanism.
7. Start one service instance and run the Epic 0 test checklist.
8. Keep the old installation stopped until the owner approves decommissioning.

The exact operational commands will be added after the target host baseline and
file layout have been verified. Do not copy commands from the legacy section
below to the new production VPS.

**Execution status (2026-08-23):** the dedicated service is enabled and active;
the legacy service is stopped and disabled. Epic 0 cutover is accepted; retain
the legacy application only for the separately approved rollback window. Do not
run the legacy commands below on either VPS.

## Legacy deployment reference

The remaining guide describes the old shared-host deployment and is retained
temporarily for rollback context. It is not the approved target configuration.

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
