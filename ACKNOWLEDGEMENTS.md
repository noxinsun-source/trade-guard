# Design references

TradeGuard is an original implementation. No source code was copied from the
projects below. Their public documentation was reviewed to understand common
order and matching-engine concepts:

- [LightMatchingEngine](https://github.com/gavincyi/LightMatchingEngine) (MIT):
  order fields, instrument/side terminology, and price-time matching context.
- [exchange-core](https://github.com/exchange-core/exchange-core) (Apache-2.0):
  separation between an order API and a deterministic risk/matching core.

TradeGuard focuses on a different layer: explainable controls before an order
reaches a matching engine. Its original additions include configurable business
limits, PASS/REVIEW/REJECT routing, retry-safe idempotency, append-only decision
records, queryable audit evidence, and Prometheus-compatible counters.

