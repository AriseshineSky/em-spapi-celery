# mi01eu 部署手册

| 项 | 值 |
|----|-----|
| VPS | `34.57.231.45` |
| GCE 实例 | `mi01eu`（`us-central1-a`） |
| 运行用户 | `Admin` |
| 代码目录 | `/home/Admin/em-spapi-celery` |
| 业务配置 | `/home/Admin/.em_celery/config.ini` |
| Worker 环境变量 | `/etc/conf.d/em_celery` |

## 1. 首次部署（已完成）

```bash
# 从本机通过 gcloud 登录（实例默认用户 sky 有 sudo）
gcloud compute ssh mi01eu --zone=us-central1-a

# 在 VPS 上（root/sudo）
sudo apt-get update
sudo apt-get install -y git rsync curl python3 python3-venv

# 创建 Admin 用户（若不存在）
sudo useradd -m -s /bin/bash Admin

# 安装 uv（Admin 用户）
sudo -u Admin bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'

# 克隆代码
sudo -u Admin git clone https://github.com/AriseshineSky/em-spapi-celery.git /home/Admin/em-spapi-celery

# 安装依赖 + systemd 单元
sudo bash -lc 'cd /home/Admin/em-spapi-celery && ./deploy/install.sh /home/Admin/em-spapi-celery'
```

## 2. 填写配置骨架

### `/home/Admin/.em_celery/config.ini`

```ini
[spapi]
lwa_refresh_token = ...
lwa_client_id = ...
lwa_client_secret = ...

[product_service]
host = ES_HOST          # Elasticsearch 7.17.10
port = 9200

[offer_service]
host = ES_HOST          # Elasticsearch 7.17.10
port = 9200

[telegram]
api_token = ...
group_chat_id = ...
```

模板文件：`deploy/mi01eu/config.ini.skeleton`

```bash
sudo cp deploy/mi01eu/config.ini.skeleton /home/Admin/.em_celery/config.ini
sudo chown Admin:Admin /home/Admin/.em_celery/config.ini
sudo chmod 640 /home/Admin/.em_celery/config.ini
sudo nano /home/Admin/.em_celery/config.ini
```

### `/etc/conf.d/em_celery`

```ini
BROKER_URL=redis://LEGACY_REDIS_HOST:6379/0

CELERY_CATALOG_QUEUES=SpapiCatalogItemsUpdate_US,SpapiCatalogItemsUpdate_UK,SpapiCatalogItemsUpdate_BE,SpapiCatalogItemsUpdate_PL,SpapiCatalogItemsUpdate_ES
CELERY_CATALOG_CONCURRENCY=2

CELERY_OFFER_QUEUES=SpapiItemOffersUpdate_US,SpapiItemOffersUpdate_UK,SpapiItemOffersUpdate_BE,SpapiItemOffersUpdate_PL,SpapiItemOffersUpdate_ES
CELERY_OFFER_CONCURRENCY=4
```

模板文件：`deploy/mi01eu/em_celery.conf.skeleton`

```bash
sudo cp deploy/mi01eu/em_celery.conf.skeleton /etc/conf.d/em_celery
sudo chmod 644 /etc/conf.d/em_celery
sudo nano /etc/conf.d/em_celery
```

## 3. 启动 worker

配置填好后：

```bash
sudo systemctl enable em-spapi-celery-catalog-worker em-spapi-celery-offer-worker
sudo systemctl start em-spapi-celery-catalog-worker em-spapi-celery-offer-worker
```

## 4. 验证

```bash
# 服务状态
systemctl status em-spapi-celery-catalog-worker em-spapi-celery-offer-worker

# 日志
journalctl -u em-spapi-celery-catalog-worker -f
journalctl -u em-spapi-celery-offer-worker -f

# 已注册 task
sudo -u Admin bash -lc 'cd /home/Admin/em-spapi-celery && .venv/bin/celery -A em_celery.worker inspect registered'

# 当前监听的队列（启动日志）
journalctl -u em-spapi-celery-catalog-worker -b | tail -20
```

## 5. 升级

```bash
sudo -u Admin bash -lc 'cd /home/Admin/em-spapi-celery && git pull && export PATH=$HOME/.local/bin:$PATH && uv sync --no-dev'
sudo systemctl restart em-spapi-celery-catalog-worker em-spapi-celery-offer-worker
```

## 6. SSH 访问 Admin

```bash
# 推荐：gcloud（当前 sky 用户有 sudo）
gcloud compute ssh mi01eu --zone=us-central1-a

# 直接 SSH Admin（需本机公钥已加入 /home/Admin/.ssh/authorized_keys）
ssh Admin@34.57.231.45
```

## 注意事项

- **不要**在配置完成前启动 worker（SP-API 凭证为 CHANGEME 会失败）
- Redis broker 必须与 legacy sender 相同，才能消费旧队列
- Sender 仍在旧机器运行；本 VPS **只消费**
