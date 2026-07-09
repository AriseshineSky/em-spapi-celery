em-spapi-celery
================

从 [em-celery](https://github.com/VG-IT/em-celery) 剥离的 SP-API Catalog / Offer Celery 项目，包含：

- Celery worker 与 task 定义（catalog、offer）
- 向 worker 发送 task 的 CLI 工具（文件 / ES 数据源）
- 同步拉取 offer 的脚本

目录结构与 em-celery 保持一致：

```
em-spapi-celery/
├── em_celery/          # Celery worker、task 包装层、task sender 工具
│   ├── tasks/
│   ├── tools/
│   └── utils/
├── em_tasks/           # 核心业务逻辑（SP-API 调用、解析、存储）
│   ├── tasks/
│   ├── spapi/
│   └── utils/
├── vendor/             # 私有 PyPI 包（本地 vendored）
│   ├── dropshipping/
│   └── cmutils/
```

## Installation

项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖，Python 版本见根目录 `.python-version`（当前 **3.12**）。

```bash
# 安装 uv 后，在项目根目录：
uv sync

# 仅安装运行时依赖（不含 dev）：
uv sync --no-dev
```

## Configuration

使用 INI 配置文件，固定路径：**`~/.em_celery/config.ini`**

VPS 生产部署见 [deploy/README.md](deploy/README.md)（Admin 用户 + systemd）。Broker 通过 **`BROKER_URL` 环境变量**（`/etc/conf.d/em_celery` 或 Sender CLI `-b`）配置。

主要配置段：

- `[spapi]` — Amazon SP-API **LWA OAuth** 凭证（`lwa_refresh_token`、`lwa_client_id`、`lwa_client_secret`；无需 AWS IAM 密钥，见 [SPAPI_CORE.md §2](docs/SPAPI_CORE.md#2-认证与客户端创建)）
- `[product_service]` — Catalog 产品 ES
- `[offer_service]` — Offer ES

Broker 仅通过 **`BROKER_URL` 环境变量** 或 Sender CLI **`-b`** 配置，不在 `config.ini` 中。

Usage
-----

启动 worker：

```bash
celery -A em_celery.worker worker -Q SpapiCatalogItemsUpdate_US,SpapiItemOffersUpdate_US
```

从 ASIN 文件发送 catalog task：

```bash
spapi_catalog_items_task_sender -b redis://localhost:6379/0 -m us asins.txt
```

从 ASIN 文件发送 offer task：

```bash
spapi_item_offers_task_sender -b redis://localhost:6379/0 -m us asins.txt
```

项目已有同步脚本，适合先确认凭证和 ES 写入是否正常（**不经过 Celery，不读 Redis 队列**）：

详见 [docs/SYNC_FETCH_OFFERS.md](docs/SYNC_FETCH_OFFERS.md)。

```bash
spapi_fetch_item_offers_sync -m us -a B0D1XD1ZV3
```

Documentation
-------------

- [技术文档（架构、流程图、CLI、配置）](docs/TECHNICAL.md)
- [程序入口指南](docs/ENTRY_POINTS.md)
- [SP-API 核心（请求与返回）](docs/SPAPI_CORE.md)
- [SP-API 限流与 Celery 多进程](docs/SPAPI_RATE_LIMITING.md)
- [Offer 端到端流程（入队 → 写 ES）](docs/OFFER_PIPELINE.md)
- [同步拉取 Offer（spapi_fetch_item_offers_sync）](docs/SYNC_FETCH_OFFERS.md)
- [Redis 优先级队列机制](docs/PRIORITY_QUEUE.md)
- [Ubuntu VPS 部署](deploy/README.md)
- [本地测试指南](local_dev/LOCAL_TESTING.md)
