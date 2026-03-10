#!/bin/bash
# EC2 Setup Script for Resume-Fit
# Run this on a fresh Ubuntu 24.04 EC2 instance

set -e

echo "=========================================="
echo "Resume-Fit EC2 Setup"
echo "=========================================="

# Update system
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
echo "🐍 Installing Python 3.11..."
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Node.js 20
echo "📗 Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Install LibreOffice for PDF conversion
echo "📄 Installing LibreOffice..."
sudo apt install libreoffice -y

# Install nginx
echo "🌐 Installing Nginx..."
sudo apt install nginx -y

# Create project directory
echo "📁 Creating project directory..."
sudo mkdir -p /opt/resume-fit
sudo chown $USER:$USER /opt/resume-fit
cd /opt/resume-fit

# Clone repository (or copy files)
echo "📥 Setting up project..."
# git clone https://github.com/Srikanthsanju/Resume-Fit.git .

# Backend setup
echo "🔧 Setting up backend..."
cd /opt/resume-fit/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
if [ ! -f .env ]; then
    echo "⚙️ Creating .env file..."
    cp .env.example .env
    echo "⚠️  Remember to edit .env with your API keys!"
fi

# Frontend setup
echo "🔧 Setting up frontend..."
cd /opt/resume-fit/frontend
npm install
npm run build

# Create systemd service for backend
echo "🔄 Creating backend service..."
sudo tee /etc/systemd/system/resume-fit-backend.service > /dev/null <<EOF
[Unit]
Description=Resume-Fit FastAPI Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=/opt/resume-fit/backend
Environment="PATH=/opt/resume-fit/backend/venv/bin"
ExecStart=/opt/resume-fit/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/resume-fit > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    # Frontend (React build)
    location / {
        root /opt/resume-fit/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
    }

    # File downloads
    location /files {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/resume-fit /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx

# Enable and start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable resume-fit-backend
sudo systemctl start resume-fit-backend

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/resume-fit/backend/.env with your API keys"
echo "2. Restart backend: sudo systemctl restart resume-fit-backend"
echo "3. Access the app at http://YOUR_PUBLIC_IP"
echo ""
echo "Useful commands:"
echo "  View backend logs: sudo journalctl -u resume-fit-backend -f"
echo "  Restart backend:   sudo systemctl restart resume-fit-backend"
echo "  Restart nginx:     sudo systemctl restart nginx"
