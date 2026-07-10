# VPS 部署指南（与 legacy em-celery 一致）

- 运行用户：**Admin**
- 配置文件：**`~/.em_celery/config.ini`**
- 日志目录：**`~/.em_celery/logs`**
- 代码目录：**`/home/Admin/em-spapi-celery`**
- systemd：**catalog / offer 两个 worker，只消费、不发送**

## 目录布局

```
/home/Admin/em-spapi-celery/     # 应用代码 + .venv
/home/Admin/.em_celery/
  config.ini                    # SP-API、ES（broker 用 BROKER_URL 环境变量）
  logs/                         # CLI 文件日志（可选）
  data/                         # 运行时数据
/etc/conf.d/em_celery           # systemd EnvironmentFile（与 legacy 一致）
```

## 监听哪些 Redis 队列

**推荐：在 `/etc/conf.d/em_celery` 配置**（每次 worker 启动时读取）：

```ini
CELERY_CATALOG_QUEUES=SpapiCatalogItemsUpdate_US,SpapiCatalogItemsUpdate_UK
CELERY_CATALOG_CONCURRENCY=2

CELERY_OFFER_QUEUES=SpapiItemOffersUpdate_US,SpapiItemOffersUpdate_UK
CELERY_OFFER_CONCURRENCY=4
```

也支持 legacy 合并写法（会按队列名前缀自动拆分）：

```ini
CELERY_QUEUES=SpapiCatalogItemsUpdate_US,SpapiItemOffersUpdate_US,SpapiCatalogItemsUpdate_UK,SpapiItemOffersUpdate_UK
CELERY_CONCURRENCY=2
```

改完后重启对应 worker 即可。

```bash
sudo systemctl restart em-spapi-celery-catalog-worker em-spapi-celery-offer-worker
```

## 挂到旧队列

1. `BROKER_URL` 在 `/etc/conf.d/em_celery`（systemd EnvironmentFile）
2. 队列名写在 `/etc/conf.d/em_celery`（见上）

Sender 继续用旧机器上的 em-celery 工具发任务。

## 安装

代码用 **git** 管理在 `/home/Admin/em-spapi-celery`；`install.sh` 只装依赖和 systemd，**不再 rsync**。

```bash
# 需已存在 Admin 用户，且 Admin 已安装 uv
sudo -u Admin git clone <repo-url> /home/Admin/em-spapi-celery
sudo /home/Admin/em-spapi-celery/deploy/install.sh

sudo -u Admin nano /home/Admin/.em_celery/config.ini
sudo nano /etc/conf.d/em_celery
sudo systemctl enable --now em-spapi-celery-catalog-worker em-spapi-celery-offer-worker
```

## systemd 服务

| 单元 | 队列来源 |
|------|----------|
| `em-spapi-celery-catalog-worker` | `CELERY_CATALOG_QUEUES`（或拆分后的 `CELERY_QUEUES`） |
| `em-spapi-celery-offer-worker` | `CELERY_OFFER_QUEUES`（或拆分后的 `CELERY_QUEUES`） |

```bash
systemctl status em-spapi-celery-catalog-worker em-spapi-celery-offer-worker
journalctl -u em-spapi-celery-catalog-worker -f
journalctl -u em-spapi-celery-offer-worker -f
```

改 `config.ini` 后重启对应服务。

## 配置

**config.ini**：固定路径 `~/.em_celery/config.ini`（Admin 用户 home 下）

**EnvironmentFile**：`/etc/conf.d/em_celery`（`BROKER_URL`、队列、并发等）

## 升级

```bash
cd /home/Admin/em-spapi-celery
sudo -u Admin git pull
sudo -u Admin uv sync --no-dev
sudo systemctl restart em-spapi-celery-catalog-worker em-spapi-celery-offer-worker
```

## 安全提示

- 勿将 `config.ini` 提交 git
- 建议 `chmod 640 ~/.em_celery/config.ini`
