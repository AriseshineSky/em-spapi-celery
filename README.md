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

使用 INI 配置文件，默认路径与 legacy em-celery 相同：**`~/.em_celery/config.ini`**。

路径解析顺序：

1. `EM_CELERY_CONFIGURATION_PATH`
2. `MWS_COLLECTOR_CONFIGURATION_PATH`
3. `EM_SPAPI_CELERY_CONFIG`
4. `~/.em_celery/config.ini`

VPS 生产部署见 [deploy/README.md](deploy/README.md)（Admin 用户 + systemd）。Broker 可在 `config.ini [celery] broker_url` 或 `BROKER_URL` 环境变量中配置，Sender CLI 的 `-b` 可省略。

主要配置段：

- `[spapi]` — Amazon SP-API 凭证
- `[product_service]` — Catalog 产品 ES
- `[offer_service]` — Offer ES
- `[broker_url]` — Celery broker

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

同步拉取 offer（不经过 Celery）：

```bash
spapi_fetch_item_offers_sync -m us -a B000000001
```

Documentation
-------------

- [技术文档（架构、流程图、CLI、配置）](docs/TECHNICAL.md)
- [Ubuntu VPS 部署](deploy/README.md)
- [本地测试指南](local_dev/LOCAL_TESTING.md)
