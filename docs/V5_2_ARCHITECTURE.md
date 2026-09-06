# V5.2 Architecture

V5.2 owns every source module and resource under the `v5_2` namespace. It has
no shared package, source checkout, data root, editable dependency or runtime
relationship with an earlier project.

```text
V5.2-owned foundations
  -> PIT facts and repositories (future phase)
  -> dated universe and daily bars
  -> deterministic features and market regime
  -> explainable ranking and WatchlistFact
  -> isolated future labels
  -> walk-forward evaluation
```

Phase 0 contains only strict validation, TradingCalendar, immutable facts and
quantity rules. Full-market realtime providers, MorningPool, CloseScan,
confirmation choreography, mandatory next-open exit, schedulers, notifications
and production runtime are not architecture components.

Static gates reject imports from prior namespaces, active references to sibling
paths, local/Git dependencies on earlier repositories and prohibited root
content. Clean-room installation and wheel smoke testing are release gates.
