# 本地测试 Celery Task 分发工具

本文说明如何在本地验证 **task sender（分发端）** 和 **worker（消费端）**，不修改项目现有代码。

## 架构速览

```
ASIN 文件 / ES
      │
      ▼
Task Sender CLI          Redis Broker              Celery Worker
(spapi_*_task_sender) ──► (队列) ──────────────────► (spapi_update_*)
      │                         SpapiCatalogItemsUpdate_US
      │                         SpapiItemOffersUpdate_US
      └── 发送前会查 ES 过滤 TTL（-f 可跳过）
```

Sender 通过 `task.apply_async(..., queue=..., connection=...)` 把消息写入 broker；Worker 从同名队列消费并调用 SP-API。

---

## 测试分层

| 层级 | 目标 | 需要 Redis | 需要 ES | 需要 SP-API |
|------|------|:----------:|:-------:|:-----------:|
| L1 分发冒烟 | 消息能进队列 | ✓ | ✗ | ✗ |
| L2 Sender CLI | 官方 sender 工具行为 | ✓ | ✓ | ✗ |
| L3 Worker 消费 | Worker 能取到 task | ✓ | ✓* | ✓ |
| L4 同步脚本 | 绕过 Celery 直接调 SP-API | ✗ | ✓ | ✓ |

\* Worker 启动时会 `ensure_indice`；执行 task 时需要 SP-API 和 ES。

**建议顺序**：L1 → L2 → L3，逐层加依赖。

---

## 0. 准备环境

```bash
cd /home/sky/src/em-spapi-celery

# 安装依赖（uv，见根目录 pyproject.toml）
uv sync

# 启动本地 Redis（可选：连同 ES 7.17.10 一起起）
docker compose -f local_dev/docker-compose.yml up -d
```

Broker 地址统一用：

```bash
export BROKER_URL=redis://127.0.0.1:6379/0
```

---

## L1：只测「分发到队列」（最快）

不跑官方 sender（sender 初始化时会连 ES），用辅助脚本直接 `apply_async`：

```bash
export BROKER_URL=redis://127.0.0.1:6379/0

# 发 1 条 catalog task + 1 条 offer task
python local_dev/smoke_test_dispatch.py

# 查看队列里是否有消息
python local_dev/inspect_queue.py --broker "$BROKER_URL" --marketplace us
```

预期：

- `smoke_test_dispatch.py` 打印 `OK: dispatched ...`
- `inspect_queue.py` 显示 `SpapiCatalogItemsUpdate_US`、`SpapiItemOffersUpdate_US` 长度 ≥ 1

此层 **不需要** `~/.em_celery/config.ini`，也 **不会** 调用 Amazon API。

清空测试队列：

```bash
python local_dev/inspect_queue.py --broker "$BROKER_URL" --marketplace us --purge
```

---

## L2：测官方 Sender CLI

Sender 类在 `__init__` 里会调用 `get_product_service()` / `get_offer_service()` 并 `ensure_indice`，因此需要配置文件和 ES。

### 配置文件

```bash
mkdir -p ~/.em_celery
cp local_dev/config.ini.sample ~/.em_celery/config.ini
# 编辑 ~/.em_celery/config.ini，填入 ES 地址（docker compose 默认可用）
```

### 发送 catalog task

```bash
export BROKER_URL=redis://127.0.0.1:6379/0

# -f 强制发送，跳过 ES TTL 过滤；-q 限制 QPS
spapi_catalog_items_task_sender \
  -b "$BROKER_URL" \
  -m us \
  -f \
  -q 1 \
  local_dev/sample_asins.txt
```

### 发送 offer task

```bash
spapi_item_offers_task_sender \
  -b "$BROKER_URL" \
  -m us \
  -f \
  -q 1 \
  local_dev/sample_asins.txt
```

### 验证

```bash
python local_dev/inspect_queue.py --broker "$BROKER_URL" --marketplace us
```

日志文件（sender 自动写入）：

- `~/.em_celery/logs/spapi_update_catalog_items_task_sender.log`
- `~/.em_celery/logs/spapi_update_item_offers_task_sender.log`

---

## L3：测 Worker 消费

开 **两个终端**。

**终端 A — Worker**

```bash
cd /home/sky/src/em-spapi-celery
export BROKER_URL=redis://127.0.0.1:6379/0
export MARKETPLACE=US
# config.ini 中需有有效 [spapi] 凭证

bash local_dev/run_local_worker.sh
# 或：
# celery -A em_celery.worker worker -l info \
#   -Q SpapiCatalogItemsUpdate_US,SpapiItemOffersUpdate_US \
#   --concurrency 1
```

**终端 B — 发送**

```bash
export BROKER_URL=redis://127.0.0.1:6379/0
python local_dev/smoke_test_dispatch.py
# 或跑 L2 的 sender CLI
```

**终端 A 预期日志**（示例）：

```
Received task: em_celery.tasks.spapi_update_catalog_items_task.spapi_update_catalog_items[...]
```

若 SP-API 凭证无效，task 会失败或被 `Ignore`/`Reject`，但 **分发 + 消费链路** 已验证。

### 常用调试命令

```bash
# 查看已注册 task
celery -A em_celery.worker inspect registered

# 查看活跃 worker
celery -A em_celery.worker inspect active_queues

# 查看 reserved / active tasks
celery -A em_celery.worker inspect reserved
```

---

## L4：不测 Celery，直接测 SP-API 逻辑

同步脚本 `spapi_fetch_item_offers_sync` **不读 Redis 队列**，在当前进程直接调用 `SpapiUpdateItemOffersTask.run()`。详见 [docs/SYNC_FETCH_OFFERS.md](../docs/SYNC_FETCH_OFFERS.md)。

```bash
spapi_fetch_item_offers_sync -m us -a B0D1XD1ZV3
```

---

## 队列命名规则

| Task | Queue 名称 |
|------|-----------|
| catalog | `SpapiCatalogItemsUpdate_{MARKETPLACE}`，如 `SpapiCatalogItemsUpdate_US` |
| offer | `SpapiItemOffersUpdate_{MARKETPLACE}`，如 `SpapiItemOffersUpdate_US` |

Worker 的 `-Q` 必须包含 sender 写入的队列，否则消息会堆积。

---

## 常见问题

### Sender 报错找不到 config

默认读 `~/.em_celery/config.ini`。

### 消息进队列但 Worker 不消费

1. Worker 是否监听了正确队列名（大小写一致，如 `_US`）
2. `BROKER_URL` 在 sender 和 worker 是否相同
3. 是否有另一个 worker 已经消费了消息

### Sender 没有发出任何 task（无报错）

不加 `-f` 时，sender 会先查 ES：若 ASIN 在索引里且未过期，则 **不会发送**。本地测试请加 `-f`。

### 想测 ES 数据源 sender

`spapi_catalog_items_task_send_from_es` / `spapi_item_offers_task_send_from_es` 从 ES 索引读 ASIN 列表再分发，需要索引里已有数据，流程同 L2/L3，只是数据源不同。

---

## 本目录文件

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 本地 Redis + Elasticsearch **7.17.10** |
| `config.ini.sample` | 配置文件模板 |
| `sample_asins.txt` | 测试用 ASIN 列表 |
| `smoke_test_dispatch.py` | L1 分发冒烟（不依赖 ES） |
| `inspect_queue.py` | 查看 / 清空队列 |
| `run_local_worker.sh` | 启动本地 worker |
