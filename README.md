# TradeGuard｜证券交易前风控网关

一个可本地运行的金融中台个人项目：订单进入交易系统前，先完成单笔金额、可用持仓、价格偏离、集中度和日累计交易额检查，输出 `PASS / REVIEW / REJECT`，并保存完整规则证据用于审计回放。

> 仅使用模拟数据，不连接真实券商账户，不构成交易或投资建议。

## 为什么做这个项目

证券中后台不仅要“把订单传下去”，还要解决三个工程问题：异常订单不能漏、网络重试不能重复处理、事后必须解释为什么通过或拒绝。公开撮合项目多关注订单簿与撮合速度，本项目补上交易进入撮合前的风险控制层。

## 核心能力

- 5 类交易前检查：单笔限额、可用持仓、价格偏离、持仓集中度、日累计交易额。
- 分级处置：硬性违规直接拒绝，灰区进入人工复核，正常订单放行。
- 幂等控制：相同幂等键和相同报文返回原决策；同键不同报文返回 HTTP 409。
- 审计留痕：SQLite 保存请求摘要、规则命中、阈值、观测值与最终决策。
- 工程化：FastAPI、Pydantic、Docker、pytest、ruff、GitHub Actions、Prometheus 文本指标。

## 业务流程

```text
委托请求 → 字段校验 → 5类风控规则 → PASS / REVIEW / REJECT
                          ↓
                    决策证据与审计记录
```

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/docs` 调用接口。

示例：

```bash
curl -X POST http://127.0.0.1:8000/v1/risk/check \
  -H 'Content-Type: application/json' \
  -d '{
    "account_id":"ACC-001","instrument":"600000.SH","side":"BUY",
    "quantity":100,"price":"10.00","reference_price":"10.00",
    "current_position":100,"portfolio_value":"100000",
    "daily_traded_notional":"10000","idempotency_key":"order-key-0001"
  }'
```

## 测试与容器

```bash
pytest -q
ruff check app tests
docker build -t trade-guard .
docker run --rm -p 8000:8000 trade-guard
```

## 公开项目参考与原创边界

项目从零实现，没有复制公开仓库代码。调研来源及与本项目的差异见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。

## 可继续扩展

- 将静态规则迁移到配置中心并增加双人复核发布。
- 接入 Redis 实现分布式幂等，接入 PostgreSQL 保存审计数据。
- 增加账户组、行业和产品级限额以及盘中限额占用/释放。

