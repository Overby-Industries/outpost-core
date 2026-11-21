# OTF-1 gap: no `outpost` node type

[OTF-1](https://github.com/Overby-Industries/telemetry-protocol) defines
`nodeType` as `reclaimer | miner | refinery | shuttle`. A surface outpost or
repair depot is none of these, so `OutpostNode` currently advertises as
`refinery` with capabilities `["process", "store"]` in zone `surface` --
the closest existing fit, because a depot's job is processing and storing
material.

That is a stand-in, not a design decision. Proposed change to
`telemetry-protocol` (not made here, since that repo owns the schema):

- add `"outpost"` to `nodeType`;
- add `"service"` (docking/handoff, repair) to `taskAction`, so a
  coordinator can offer docking slots as tasks rather than only
  processing work.

Until then the coordinator should not infer anything from the type alone;
OTF-1 already says capabilities are advertised by the node, so behaviour is
correct either way.
