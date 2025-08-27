#!/bin/bash

# Radiator API Deployment Script for Ubuntu
# Run this script as root or with sudo

set -e

# Configuration
APP_NAME="radiator-api"
APP_USER="radiator"
APP_GROUP="radiator"
APP_DIR="/opt/radiator-api"
SERVICE_FILE="radiator-api.service"

echo "🚀 Starting Radiator API deployment..."

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo "🔧 Installing required packages..."
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
apt-get install -y postgresql postgresql-contrib postgresql-client
apt-get install -y nginx curl git

# Create application user
echo "👤 Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --create-home --shell /bin/bash "$APP_USER"
    usermod -aG sudo "$APP_USER"
fi

# Create application directory
echo "📁 Creating application directory..."
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_GROUP" "$APP_DIR"

# Clone or update repository
if [ -d "$APP_DIR/.git" ]; then
    echo "🔄 Updating existing repository..."
    cd "$APP_DIR"
    sudo -u "$APP_USER" git pull origin main
else
    echo "📥 Cloning repository..."
    cd /tmp
    git clone https://github.com/yourusername/radiator-api.git
    cp -r radiator-api/* "$APP_DIR/"
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
fi

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3.11 -m venv .venv
sudo -u "$APP_USER" .venv/bin/pip install --upgrade pip

# Install dependencies
echo "📚 Installing Python dependencies..."
sudo -u "$APP_USER" .venv/bin/pip install -e .

# Create necessary directories
echo "📂 Creating necessary directories..."
sudo -u "$APP_USER" mkdir -p "$APP_DIR/logs" "$APP_DIR/uploads"

# Setup environment file
echo "⚙️ Setting up environment configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/env.example" "$APP_DIR/.env"
    chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
    echo "⚠️  Please edit $APP_DIR/.env with your configuration"
fi

# Setup PostgreSQL
echo "🐘 Setting up PostgreSQL..."
sudo -u postgres createuser --createdb --createrole --superuser "$APP_USER" || true
sudo -u postgres createdb -O "$APP_USER" radiator_db || true

# Setup systemd service
echo "🔧 Setting up systemd service..."
cp "$APP_DIR/deploy/$SERVICE_FILE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_FILE"

# Setup Nginx
echo "🌐 Setting up Nginx..."
cat > /etc/nginx/sites-available/radiator-api << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/radiator-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# Start the service
echo "🚀 Starting Radiator API service..."
systemctl start "$SERVICE_FILE"
systemctl status "$SERVICE_FILE"

echo "✅ Deployment completed successfully!"
echo "📋 Next steps:"
echo "   1. Edit $APP_DIR/.env with your configuration"
echo "   2. Run: sudo -u $APP_USER $APP_DIR/.venv/bin/alembic upgrade head"
echo "   3. Check service status: systemctl status $SERVICE_FILE"
echo "   4. Check logs: journalctl -u $SERVICE_FILE -f"
echo "   5. Access your API at: http://your-server-ip"
