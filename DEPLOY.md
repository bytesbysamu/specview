# Deploy

## VPS setup (one time)

```bash
# 1. Clone the repo
git clone <repo-url> /opt/specview
cd /opt/specview

# 2. Create the data directory and drop your projects in
mkdir -p /opt/specview/data/projects

# 3. Build and start
docker compose build
docker compose up -d
```

App runs on port 80.

## Update

```bash
cd /opt/specview
git pull
docker compose build
docker compose up -d
```

## Data directory

Projects live at `/opt/specview/data/projects/` on the VPS.
Each project is a folder containing markdown files.

For local dev, override the data dir:

```bash
SPECVIEW_DATA_DIR=/path/to/your/spec-doc-data docker compose up -d
```
