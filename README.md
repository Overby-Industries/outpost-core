# Outpost Core

**Overby Industries — systems software for surface outposts and repair depots.**

## Status: early -- first software is in

Built and tested (`pip install pytest jsonschema && python -m pytest`):

- **`outpost_core.docking`** -- deterministic docking/handoff scheduler.
  Higher priority wins; equal-priority ties are broken by ETA but recorded as
  a `Contention`. Priority 10 is Tier 0 (emergency) and never leaves the
  deterministic path.
- **`outpost_core.power`** -- solar + battery ledger with lowest-priority-first
  load shedding, mapping state of charge onto OTF-1 `nominal/degraded/safe`.
- **`outpost_core.node`** -- the outpost as an OTF-1 fleet node: emits
  `status`, answers coordinator `assignment`s with `ack`s (it always has the
  final say), and ingests reclaimer `event`s into a feedstock inventory.
- **`outpost_core.advisory`** -- turns an eligible contention into an ADV-1
  advisory request for [`ai-roundtable`](https://github.com/Overby-Industries/ai-roundtable).

Still open: crewed vs. uncrewed, real power hardware, an `outpost` OTF-1 node
type ([`docs/otf1-gap.md`](docs/otf1-gap.md)). Cross-repo scenario:
[`design-studies`](https://github.com/Overby-Industries/design-studies) `integration/`.

## Why This Is Its Own Repo

A surface outpost or repair depot is a fixed installation, not a vehicle --
it has different constraints than anything in
[`power-and-propulsion`](https://github.com/Overby-Industries/power-and-propulsion)
or [`miner-automation`](https://github.com/Overby-Industries/miner-automation):
continuous (not mission-bounded) operation, life-support-adjacent systems
if crewed, and it's the fixed point the rest of the fleet returns to for
resupply, repair, and handoff.

## Relationship to Other Repos

- **[`starlifter-os`](https://github.com/Overby-Industries/starlifter-os)** --
  an outpost is effectively a stationary fleet node from the coordinator's
  perspective: it reports status and receives scheduling the same way a
  vehicle would, but never moves.
- **[`telemetry-protocol`](https://github.com/Overby-Industries/telemetry-protocol)**
  and **[`transparency-protocol`](https://github.com/Overby-Industries/transparency-protocol)** --
  an outpost is both an OTF-1 telemetry source (its own operational health)
  and, once built, an OTB-1 line item (the facility investment itself --
  see that repo's "facility" example).
- **[`space-reclamation`](https://github.com/Overby-Industries/space-reclamation)** --
  a repair depot is a natural place to run reclamation/refurbishment
  processing, not just a place ships dock.

## Draft Scope

See [`docs/subsystems-draft.md`](docs/subsystems-draft.md). At minimum, a
credible outpost needs:

- **Power management** -- almost certainly not the same MHD core as a
  vehicle (a fixed installation has very different mass/size constraints);
  likely solar + battery, evaluated independently.
- **Life support** (if crewed) -- explicitly out of scope for this repo
  until crewed-outpost plans are further along; uncrewed depot automation
  comes first.
- **Docking/handoff coordination** -- receiving vehicles, transferring
  cargo, scheduling repairs.
- **Long-duration fault tolerance** -- unlike a vehicle's bounded mission,
  an outpost needs to keep operating indefinitely between resupply.

## Open Questions

- Crewed vs. uncrewed first -- this changes almost every subsystem
  priority and isn't decided yet.
- How much of `starlifter-os`'s fleet-coordination logic is directly
  reusable for a stationary node vs. needs its own design.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
Systems engineers and life-support/ECLSS-adjacent expertise (for whenever
crewed plans firm up) are especially useful here.

## License

[Apache 2.0](LICENSE).
