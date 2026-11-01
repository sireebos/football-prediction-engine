# 🚀 Universal Installation & Deployment Guide

> **SIPC Sports Intelligence & Bet9ja Zoom Virtual Football Engine**  
> Complete cross-platform installation instructions for **Linux**, **macOS**, and **Windows**.

---

## 📋 System Requirements Overview

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 20.04+ / macOS 12+ / Windows 10 (Build 19041+) | Ubuntu 22.04 LTS / macOS Sonoma / Windows 11 |
| **CPU** | 2 Cores | 4+ Cores (x86_64 or Apple Silicon ARM64) |
| **RAM** | 4 GB | 8 GB+ |
| **Disk Space** | 5 GB available | 15 GB SSD |
| **Network** | Broadband internet | Direct connection (no restrictive proxy) |

---

## 🎯 Choose Your Installation Method

1. [**Method 1: Docker (Recommended)**](#method-1-docker-full-stack-installation---all-operating-systems) — Deploys full Next.js UI, FastAPI, PostgreSQL, Redis, and Nginx with one command.
2. [**Method 2: Standalone CLI Tools**](#method-2-standalone-zoom-virtual-cli-tools) — Lightweight Python setup for running live terminal predictions and scrapers.
3. [**Method 3: Native Host Installation**](#method-3-native-host-installation-without-docker) — Full development setup running directly on your host machine.

---

## Method 1: Docker Full-Stack Installation - All Operating Systems

Docker provides an isolated, consistent runtime across Linux, macOS, and Windows.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DOCKER ARCHITECTURE                             │
│                                                                        │
│   Frontend (Next.js 14)      ────────▶  Port 3001                      │
│   Backend (FastAPI)          ────────▶  Port 8001 (Internal 8000)      │
│   Nginx Reverse Proxy        ────────▶  Port 80 / 8088                 │
│   PostgreSQL 16              ────────▶  Port 5433 (Internal 5432)      │
│   Redis 7                    ────────▶  Port 6380 (Internal 6379)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 🐧 A. Linux Installation (Ubuntu / Debian / Mint / Pop!_OS / Fedora / Arch)

#### 1. Install Docker & Docker Compose
```bash
# Ubuntu / Debian / Linux Mint:
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker engine and Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker to run without sudo
sudo usermod -aG docker $USER
newgrp docker
```

*For Fedora:*
```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

*For Arch Linux:*
```bash
sudo pacman -Syu docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

#### 2. Clone and Launch the Project
```bash
# Clone the repository
git clone https://github.com/your-org/DataCenter.git
cd DataCenter

# Copy environment template
cp .env.example .env

# Start all containers in the background
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

---

### 🍏 B. macOS Installation (Apple Silicon M1/M2/M3/M4 & Intel)

#### 1. Install Prerequisites
If you do not already have **Homebrew** installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Docker Desktop
```bash
# Install Docker Desktop via Homebrew Cask
brew install --cask docker

# Or download DMG directly:
# - Apple Silicon: https://desktop.docker.com/mac/main/arm64/Docker.dmg
# - Intel Macs:    https://desktop.docker.com/mac/main/amd64/Docker.dmg
```
- Open **Docker** from Applications (`/Applications/Docker.app`).
- Follow the prompt to enable Docker and grant privileged helper permissions.
- In Docker Settings > **General**, ensure **Use Virtualization framework** is enabled.

#### 3. Clone and Launch the Project
Open Terminal:
```bash
# Clone and enter project directory
git clone https://github.com/your-org/DataCenter.git
cd DataCenter

# Copy environment configuration
cp .env.example .env

# On Apple Silicon (ARM64), compose automatically handles multi-arch builds.
# If emulation is needed for specific x86 binary extensions:
export DOCKER_DEFAULT_PLATFORM=linux/amd64

# Start containers
docker compose up -d

# Check container health
docker compose ps
```

---

### 🪟 C. Windows Installation (Windows 10 / Windows 11)

#### 1. Install WSL2 (Windows Subsystem for Linux)
Open **PowerShell as Administrator**:
```powershell
# Install WSL2 with Ubuntu
wsl --install

# Restart your computer when prompted.
```

#### 2. Install Docker Desktop for Windows
1. Download **Docker Desktop for Windows**: [https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe)
2. Run the installer and ensure **Use WSL 2 instead of Hyper-V** is checked.
3. Open Docker Desktop > **Settings (Gear Icon)** > **Resources** > **WSL Integration**:
   - Check **Enable integration with my default WSL distro**.
   - Toggle on your installed distro (e.g. `Ubuntu`).
   - Click **Apply & restart**.

#### 3. Clone and Launch (Inside WSL2 or PowerShell)

*Option 1: Recommended — Inside WSL2 Terminal (Faster disk I/O):*
```bash
# Open WSL2
wsl

# Clone into your home directory (avoid /mnt/c for best performance)
cd ~
git clone https://github.com/your-org/DataCenter.git
cd DataCenter

cp .env.example .env
docker compose up -d
```

*Option 2: From Windows PowerShell:*
```powershell
# Set Git to preserve LF line endings
git config --global core.autocrlf false

# Clone repository
git clone https://github.com/your-org/DataCenter.git
cd DataCenter

Copy-Item .env.example .env
docker compose up -d
```

---

## Method 2: Standalone Zoom Virtual CLI Tools

If you only want to scrape Bet9ja Zoom, run Poisson predictions, and use the terminal viewers without Docker:

### 🐧 Linux & 🍏 macOS

```bash
# 1. Ensure Python 3.10+ is installed
python3 --version

# On Ubuntu/Debian if missing:
sudo apt-get install -y python3-venv python3-pip

# On macOS if missing:
brew install python@3.11

# 2. Clone or navigate to the tools folder
cd predition_zoom

# 3. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run Live Zoom Viewer across all 8 leagues:
python3 live_zoom.py

# 6. Predict upcoming fixture:
python3 zoom.py --predict "Z.Man City" "Z.Arsenal"

# 7. Scrape and update historical results across all leagues:
python3 zoom.py --all-leagues
```

### 🪟 Windows (PowerShell)

```powershell
# 1. Ensure Python 3.10+ is installed from python.org
# (Make sure to check "Add python.exe to PATH" during installation)
python --version

# 2. Open PowerShell and navigate to tools directory
cd predition_zoom

# 3. Enable script execution if restricted
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run tools
python live_zoom.py
python zoom.py --predict "Z.Man City" "Z.Arsenal"
python zoom.py --all-leagues
```

---

## Method 3: Native Host Installation (Without Docker)

For developers wishing to run the backend and frontend locally without containers.

### Prerequisites

| Tool | Version | Linux Command | macOS Command | Windows |
| :--- | :--- | :--- | :--- | :--- |
| **Node.js** | 18 LTS+ | `sudo apt install nodejs npm` | `brew install node@18` | [nodejs.org](https://nodejs.org) |
| **Python** | 3.11+ | `sudo apt install python3 python3-venv` | `brew install python@3.11` | [python.org](https://python.org) |
| **PostgreSQL**| 15 or 16 | `sudo apt install postgresql` | `brew install postgresql@16` | [postgresql.org](https://www.postgresql.org) |
| **Redis** | 7.x | `sudo apt install redis-server` | `brew install redis` | WSL2 or Memurai |

### 1. Database Setup
```bash
# Start PostgreSQL & Redis services:
# On Linux:
sudo systemctl start postgresql redis-server

# On macOS:
brew services start postgresql@16
brew services start redis

# Create database and user:
sudo -u postgres psql -c "CREATE DATABASE sipc;"
sudo -u postgres psql -c "CREATE USER sipc WITH PASSWORD 'sipc_secret_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sipc TO sipc;"
```

### 2. Backend Setup
```bash
cd backend

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend

# Install npm dependencies
npm install

# Start Next.js development server
npm run dev
```

---

## 🌐 Port Matrix & Access URLs

Once running, the application endpoints are available at:

| Service | Host Port | URL | Description |
| :--- | :---: | :--- | :--- |
| **Frontend Web UI** | `3001` | [http://localhost:3001](http://localhost:3001) | Main SIPC Sports Intelligence Dashboard |
| **Prediction vs Results** | `3001` | [http://localhost:3001](http://localhost:3001) | Backtest & Accuracy Comparison Matrix tab |
| **FastAPI Backend Docs** | `8001` | [http://localhost:8001/docs](http://localhost:8001/docs) | Interactive Swagger UI API documentation |
| **Zoom Live API** | `8001` | [http://localhost:8001/api/v1/autonomous/zoom-live](http://localhost:8001/api/v1/autonomous/zoom-live) | Real-time Zoom odds & results endpoint |
| **Zoom Performance API**| `8001` | [http://localhost:8001/api/v1/autonomous/zoom-performance](http://localhost:8001/api/v1/autonomous/zoom-performance) | Model accuracy, ROI, and match outcomes |
| **Nginx Gateway** | `8088` / `80` | [http://localhost:8088](http://localhost:8088) | Production Reverse Proxy |
| **PostgreSQL** | `5433` | `localhost:5433` | Database connection (`user: sipc`, `db: sipc`) |
| **Redis** | `6380` | `localhost:6380` | Cache & pub/sub broker |

---

## 🔍 Verification Commands

Test your deployment with these health check commands:

```bash
# 1. Test Backend Health & Version:
curl -s http://localhost:8001/health | jq .

# 2. Test Zoom Real-time Live Matches:
curl -s "http://localhost:8001/api/v1/autonomous/zoom-live?competition_id=1" | jq .total_upcoming_matches

# 3. Test Prediction vs Results Backtest Endpoint:
curl -s "http://localhost:8001/api/v1/autonomous/zoom-performance?limit=10" | jq .summary

# 4. Test Frontend Server:
curl -I http://localhost:3001/
```

Expected output for the health checks is HTTP `200 OK`.

---

## 🛠️ Troubleshooting & FAQs

### Q1: `bind: address already in use` error on ports 3001, 8001, or 5433
Another process is using one of the ports. Find and terminate it, or edit `docker-compose.yml`:
- **Linux / macOS:**
  ```bash
  sudo lsof -i :3001
  sudo lsof -i :8001
  # Kill process:
  sudo kill -9 <PID>
  ```
- **Windows:**
  ```powershell
  Get-Process -Id (Get-NetTCPConnection -LocalPort 3001).OwningProcess | Stop-Process -Force
  ```

### Q2: Docker permission denied on Linux (`connect: permission denied`)
Your user is not in the `docker` group:
```bash
sudo usermod -aG docker $USER
newgrp docker
# Or restart your user session:
su - $USER
```

### Q3: Bet9ja live data times out or returns 0 matches
Ensure your environment is not routing traffic through a dead local proxy:
- Verify `docker-compose.yml` does not contain invalid `HTTP_PROXY` variables.
- Direct outbound HTTPS connections to `zoomapi.bet9ja.com` and `web.bet9ja.com` must be allowed.
- Test connectivity from within the container:
  ```bash
  docker compose exec backend python3 -c "import urllib.request; print(urllib.request.urlopen('https://zoomapi.bet9ja.com').getcode())"
  ```

### Q4: Windows CRLF line ending errors in bash scripts
If you cloned the repo in Windows and run inside WSL2:
```bash
sudo apt-get install dos2unix
dos2unix scripts/*.sh
```

---

## 🔒 Production Security Best Practices

1. Change the default database password in `.env` (`POSTGRES_PASSWORD`).
2. Generate a secure `SECRET_KEY` for JWT tokens:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Set `DEBUG=False` in `.env` before public production deployment.
4. Bind Nginx ports directly to your domain or reverse proxy behind Cloudflare with SSL.
