Deployment Guide
Prerequisites

GitHub account with repos
AWS account for EC2
Render account
Google Gemini API key
Pinecone API key

Part 1: Heavy Backend (AWS EC2)
Step 1: Launch EC2 Instance

Go to AWS Console → EC2 → Launch Instances
Configuration:

AMI: Ubuntu 22.04 LTS
Instance Type: m7i-flex.large (minimum recommended)
Storage: 20GB EBS
Security Group: Allow ports 22 (SSH), 8000 (API)

Create/Use Key Pair:

Download .pem file
Store safely

Step 2: Connect via SSH
bashchmod 400 your-key.pem
ssh -i your-key.pem ubuntu@your-ec2-public-ip
Step 3: Run Bootstrap Script
bash# Clone or upload your repo
git clone https://github.com/yourusername/prepsphere-rag.git
cd prepsphere-rag

# Run bootstrap (installs everything + starts service)

sudo bash heavy_backend/bootstrap.sh
What bootstrap does:

Updates system packages
Installs Python 3.11
Creates virtual environment
Installs dependencies
Creates .env file
Sets up systemd service
Starts the service

Step 4: Configure Environment
bashsudo nano /opt/heavy_backend/.env
Add:
GEMINI_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
INDEX_NAME=your_index_name
FORWARDER_TOKEN=your_secret_token
MODEL_CACHE_DIR=/opt/models
PORT=8000
LOG_LEVEL=info
Step 5: Verify Service
bashsudo systemctl status myrag.service
Should show: active (running)
Step 6: Test Locally on EC2
bashcurl -X POST http://localhost:8000/chat \
 -H "Authorization: Bearer your_secret_token" \
 -H "Content-Type: application/json" \
 -d '{"question": "test question"}'
Step 7: Get Public IP
bashcurl http://169.254.169.254/latest/meta-data/public-ipv4
This is your Heavy Backend URL for Thin Forwarder.

Part 2: Thin Forwarder (Render)
Step 1: Update Repository
Create/update in your thin_forwarder/ folder:
main.py - Update with correct EC2 URL:
pythonHEAVY_BACKEND_URL = "http://your-ec2-public-ip:8000"
requirements.txt:
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
requests==2.31.0
.env.example:
HEAVY_BACKEND_URL=http://your-ec2-ip:8000
FORWARDER_TOKEN=your_secret_token
Step 2: Push to GitHub
bashgit add .
git commit -m "Update thin forwarder for deployment"
git push origin main
Step 3: Connect to Render

Go to https://dashboard.render.com
Click New + → Web Service
Connect GitHub repository
Select prepsphere-rag repo

Step 4: Configure Web Service
SettingValueNameprepsphere-thin-forwarderEnvironmentPython 3RegionChoose closest to youBranchmainBuild Commandpip install -r thin_forwarder/requirements.txtStart Commanduvicorn thin_forwarder.main:app --host 0.0.0.0
Step 5: Add Environment Variables
Click Advanced → Add Environment Variable:

HEAVY_BACKEND_URL = http://your-ec2-public-ip:8000
FORWARDER_TOKEN = (same as EC2 .env)

Step 6: Deploy
Click Create Web Service
Wait 2-3 minutes. You'll get a URL like:
https://prepsphere-thin-forwarder.onrender.com
Step 7: Test Render Deployment
bashcurl -X POST "https://prepsphere-thin-forwarder.onrender.com/chat" \
 -H "Authorization: Bearer your_secret_token" \
 -H "Content-Type: application/json" \
 -d '{"question": "test question"}'

Part 3: Data Pipeline
Upload Extracted Texts to EC2
bash# From local machine
scp -i your-key.pem -r data/extracted_texts/\* \
 ubuntu@your-ec2-ip:/opt/heavy_backend/texts/
Index Texts in Pinecone
Run on EC2:
bashssh -i your-key.pem ubuntu@your-ec2-ip
cd /opt/heavy_backend

# Run indexing script (create if not exists)

python index_documents.py

Maintenance
Update Heavy Backend
bashssh -i your-key.pem ubuntu@your-ec2-ip
cd /opt/heavy_backend
git pull origin main
pip install -r requirements.txt
sudo systemctl restart myrag.service
Update Thin Forwarder
Just push to GitHub. Render auto-deploys.
Monitor Services
EC2:
bashsudo systemctl logs -f myrag.service
Render:
View logs in dashboard

Troubleshooting
Heavy Backend Won't Start
bashsudo systemctl status myrag.service
sudo journalctl -u myrag.service -n 50
Thin Forwarder Can't Reach EC2

Check EC2 security group allows port 8000
Verify HEAVY_BACKEND_URL is correct
Test from EC2: curl http://localhost:8000/

Pinecone Connection Issues

Verify API key is correct
Check index name matches
Ensure environment has internet access
