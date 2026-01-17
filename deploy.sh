#!/bin/bash
# Deployment script for Telegram Crypto Bot
# Server: 194.87.83.103

set -e

echo "🚀 Deploying Telegram Crypto Bot..."

# Configuration
SERVER_IP="194.87.83.103"
SERVER_USER="root"  # Change if using different user
REMOTE_DIR="/opt/tg-balance-bot"
LOCAL_DIR="$(pwd)"

echo "📋 Deployment Configuration:"
echo "   Server: $SERVER_IP"
echo "   User: $SERVER_USER"
echo "   Remote Directory: $REMOTE_DIR"
echo ""

# Check if .env file exists locally
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with your configuration."
    exit 1
fi

echo "📦 Step 1: Creating deployment package..."
tar -czf bot-deployment.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='saved_addresses.json' \
    --exclude='portfolio_history.json' \
    --exclude='bot-deployment.tar.gz' \
    bot.py \
    requirements.txt \
    .env \
    *.md

echo "✅ Package created: bot-deployment.tar.gz"

echo ""
echo "📤 Step 2: Uploading to server..."
scp bot-deployment.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

echo ""
echo "🔧 Step 3: Installing on server..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    set -e
    
    echo "Creating directory..."
    mkdir -p /opt/tg-balance-bot
    cd /opt/tg-balance-bot
    
    echo "Extracting files..."
    tar -xzf /tmp/bot-deployment.tar.gz
    rm /tmp/bot-deployment.tar.gz
    
    echo "Installing system dependencies..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
    
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    echo "Installing Python packages..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "Creating systemd service..."
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

[Install]
WantedBy=multi-user.target
EOF
    
    echo "Enabling and starting service..."
    systemctl daemon-reload
    systemctl enable tg-balance-bot
    systemctl start tg-balance-bot
    
    echo "✅ Bot deployed and started!"
    echo ""
    echo "Service status:"
    systemctl status tg-balance-bot --no-pager
ENDSSH

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📋 Useful commands:"
echo "   Check status:  ssh $SERVER_USER@$SERVER_IP 'systemctl status tg-balance-bot'"
echo "   View logs:     ssh $SERVER_USER@$SERVER_IP 'journalctl -u tg-balance-bot -f'"
echo "   Restart bot:   ssh $SERVER_USER@$SERVER_IP 'systemctl restart tg-balance-bot'"
echo "   Stop bot:      ssh $SERVER_USER@$SERVER_IP 'systemctl stop tg-balance-bot'"
echo ""

# Cleanup
rm bot-deployment.tar.gz

echo "✅ Done!"
