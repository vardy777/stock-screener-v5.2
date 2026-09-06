# V5.2 Migration Plan

The migration is extraction, not a runtime dependency. Low-level behavior is
reimplemented in the standalone namespace with characterization tests. Earlier
repositories remain read-only references during migration and are never on the
installed package path.

Phase 0 copies only strict validation/timezone behavior, calendar validation
and session shifting, canonical content hashes, immutable atomic persistence
and A-share quantity rules. It explicitly excludes realtime providers,
decisions, CloseScan, execution choreography, notifications, schedulers,
dashboards, production acceptance and runtime data.

After static, full-suite, build, clean-install and wheel-smoke gates pass, the
standalone repository may be published. Historical PIT data work is a separate
next phase with a separate gate.
