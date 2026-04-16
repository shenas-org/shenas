# Privacy architecture for population-level learning

Status: proposed (no code yet). Authors: shenas team.

This document describes the privacy architecture shenas uses to let peers
contribute to population-level statistics and trained models **without their
raw data ever leaving their device**. It's the reference for the protocol
shape, the threat model, and the phased path to get there.

## The promise

> Your data never leaves your device. What comes back is the collective
> wisdom of the population, in the form of trained models and aggregate
> statistics.

The rest of this document is the cost of making that promise literally
true rather than approximately true.

## Scope

- Population-level **cross-user** learning and analytics: many peers
  contribute, the shenas server aggregates, results flow back.
- Two deliverables on the same protocol: aggregate statistics (first) and
  supervised models (later). Both are FL rounds differing only in what the
  aggregator does with the sum.

Out of scope here:

- The **per-user mesh** (`app/mesh/`, currently being ported to libp2p).
  That path is for a single user's own devices and has a different threat
  model — the user trusts their own devices; mixnet-style anonymity is
  unnecessary there.
- UI / UX for privacy-budget surfacing. Flagged as a follow-up below.

## Stack at a glance

Four independent layers, each solving a distinct part of the promise:

| Layer | Component | Solves |
| --- | --- | --- |
| Training | **Flower (flwr)**, async (FedBuff / FedAsync) | Training runs on-device; only gradient updates travel. |
| Per-record privacy | **DP-SGD via OpenDP** on client | Gradient-inversion attacks; formal ε budget. |
| Per-message privacy | **SecAgg** (flwr's SecAgg+) | Aggregator only ever sees sums, never individuals. |
| Network privacy | **Nym** mixnet, upload path only | Sender-anonymity against a global passive observer. |

Model **retrieval** uses plain HTTPS — the global model has no per-peer
signal, so anonymizing its download would waste latency and bandwidth
without buying anything. Participation is public; contributions are
anonymous. This asymmetry is an intentional design choice, not an
oversight.

## Data flow

Two asymmetric channels.

```
┌── DOWNLOAD PATH: server → peer (plain HTTPS) ────────────────┐
│                                                              │
│  peer device                    aggregator                   │
│    └─ fetch current global ───→  serves versioned global     │
│       model over HTTPS           model artifact              │
│                                  (CDN-cacheable, resumable)  │
│                                                              │
│  What the server sees: peer X pulled model version N at      │
│  time T. This is intentionally public — participation is     │
│  public, contributions are anonymous.                        │
└──────────────────────────────────────────────────────────────┘

┌── UPLOAD PATH: peer → server (Nym + SecAgg + DP-SGD) ────────┐
│                                                              │
│  peer device                                                 │
│    ├── DuckDB local metrics (raw records stay here, always)  │
│    ├── Flower client (async)                                 │
│    │     - uses the model it just downloaded over HTTPS      │
│    │     - runs local SGD steps on the local DuckDB slice    │
│    │     - per-step DP-SGD: clip norm, add Gaussian noise    │
│    │       (OpenDP ε budget)                                 │
│    │     - emits a noised gradient update for the round      │
│    ├── SecAgg layer                                          │
│    │     - masks gradient with pairwise-cancelling masks     │
│    │       (cancellation happens on the aggregator in sum)   │
│    └── Nym client (Rust SDK, sibling to the libp2p port)     │
│          - Sphinx-packet-wraps the masked update             │
│          - mixes into the cover-traffic stream               │
│          - delivers to the aggregator gateway                │
│                                                              │
│  aggregator                                                  │
│    ├── Flower server (async, FedBuff / FedAsync)             │
│    │     - collects masked updates until the epoch closes    │
│    │     - requires a threshold of contributors per round    │
│    │       (minimum batch size, otherwise round is dropped)  │
│    ├── SecAgg sum — pairwise masks cancel → clean aggregate  │
│    ├── Apply aggregate gradient → new global model version   │
│    ├── OpenDP bookkeeping: ε spent per model, per epoch      │
│    └── Publish: new model version available on the HTTPS     │
│       download path for next round.                          │
│                                                              │
│  What the operator can see: per-epoch timing and total       │
│  contributor count; nothing about who contributed or what.   │
└──────────────────────────────────────────────────────────────┘
```

The two paths are decoupled in time. A peer downloads when convenient,
trains locally at its own pace, and uploads when the next epoch opens.
**Async FL plus a minimum-batch-size per closed round is what prevents
download↔upload timing correlation.** An adversary that saw peer X
download at T and observed "only one upload arrived between T+15 and
T+30" would otherwise be able to link them. The round threshold and
async window are the mitigation; both are tunable parameters the
operator commits to at deployment time.

## Threat model

### In scope

- **Network observer** (ISP, LAN, global passive).
  Cannot tell which peer *contributed* in a given round. Can see peer X
  pulled the global model at time T — this is intentionally public.
  Contribution-unlinkability is preserved because (a) uploads go through
  Nym, and (b) the async-FL round threshold ensures each published
  aggregate mixes K≥K_min contributors. Parameter K_min is specified at
  deployment; see "Open parameters" below.
- **Honest-but-curious aggregator.**
  Cannot see individual gradient updates; only their sum. Handled by
  SecAgg.
- **Malicious aggregator running gradient-inversion attacks.**
  Cannot invert individual records because no individual updates are
  visible — only the sum, which has already aggregated away the
  per-record signal. DP-SGD on-client provides a second line of defense
  if a subset of peers is also adversarial (reducing the honest-sum's
  signal-to-noise ratio relative to the attacker's reconstruction).
- **Model-memorisation attacks** against the released global model.
  Bounded by the DP-SGD ε used during training. *The "your data never
  leaves your device" claim carries a footnote: "the model released to
  you is DP-bounded to have learned at most ε worth about any
  individual."* That footnote must be visible in docs and in-product UI
  near the contribute toggle.
- **Weak sybil** (one peer submitting twice in a round).
  Handled by simple per-epoch rate limits at the Nym gateway.

### Known gaps (out of scope for v1, required before production)

- **Strong sybil** (one peer dominating the aggregate by submitting
  10,000×). Requires anonymous credentials: zk-nym, or a Coconut-style
  blind-signed token scheme. Each peer receives N tokens per epoch;
  each upload spends one; the server verifies validity without learning
  which peer submitted. Without this, DP guarantees are asterisked —
  the attacker's records dominate the sum. **This must be closed before
  any production rollout.**
- **Malicious-majority SecAgg.** SecAgg's content-unlinkability
  guarantee assumes a threshold of honest participants per round. If
  the attacker controls more than that threshold, the sum can be
  back-solved. The aggregator must drop the round (not publish a
  weakened aggregate) when the honest-participant estimate is too low;
  the threshold parameter is committed to at deployment.
- **Compromised client device.** Out of scope: not shenas-specific.
- **Covert-channel side channels** (CPU timing, power analysis on
  mobile). Out of scope.

### Explicitly not claimed

- **Pre-contribution privacy isn't perfect deniability.** Downloading
  the global model tells the server the peer is *eligible to
  contribute* and *currently active*. That's what "participation is
  public" means in practice. A peer who never downloads the model never
  reveals participation, but also can't contribute.
- **DP ε is a real number, not "nothing learned."** The model has
  learned *some* bounded amount about each contributor. The doc and
  UI must name the ε explicitly per published artifact.

## Why this stack

### Why FL instead of "local DP + upload noised data"

Local DP at 100–1,000 users destroys utility for anything finer than
crude histograms. More importantly, uploading a noised record still
means a derivative of the user's data leaves the device — the
peer-facing promise would have to read "your noised data leaves your
device," which is a different promise than the one we're making. FL
keeps training on-device and lets only gradient updates travel, which
maps directly to the promise.

### Why SecAgg on top of DP-SGD

DP-SGD alone still sends individual (noised) gradients to the
aggregator, and gradient-inversion research has repeatedly shown
that individual noised gradients leak non-trivially (see Zhu et al.,
"Deep Leakage from Gradients," NeurIPS 2019; Geiping et al., "Inverting
Gradients," NeurIPS 2020). SecAgg ensures the aggregator never sees an
individual gradient — only the sum — eliminating the inversion attack
surface rather than trying to outrun it with noise.

### Why async FL (FedBuff / FedAsync)

Mixnet delivery latency is seconds per hop. Synchronous rounds that
wait for N specific clients would tail-latency out of any reasonable
timeout. Async FL closes rounds on a time basis, tolerates arbitrary
client delivery delays, and degrades gracefully when fewer peers
contribute in a given window.

### Why Nym, not Tor hidden services

Tor gives circuit-level anonymity but is vulnerable to end-to-end
traffic correlation — which is exactly the attack a global observer of
aggregator ingress would mount. For periodic, one-shot gradient uploads
with no long-lived connection, Nym's Sphinx batching + cover traffic is
the right design. Tor's strength is long-lived connections to hidden
services; ours is the opposite workload.

### Why Flower specifically

- Mature Python FL framework.
- Ships SecAgg+ already.
- Present in the shenas tree (`app/fl/`, `server/fl/`), so we're not
  adding a new dependency — we're giving the existing one a concrete
  job instead of deprecating it.

### Why plain HTTPS for model download

The global model is identical for every peer. Fetching it leaks only
"this peer participated in some round," which is already public by
design. Routing a multi-megabyte download through Nym would slow every
peer and consume mixnet bandwidth for no anonymity gain. CDN-cacheable
HTTPS on the download path, Nym on the upload path, is the cheap right
answer.

## Privacy-budget accounting

This is the hard part, and it's where well-intentioned privacy
architectures most often collapse in practice.

Every published model update and every published statistic spends
from each contributor's ε budget. The protocol must commit to:

1. **A per-peer lifetime ε.** The maximum ε a single peer can
   accumulate across their time on the platform. Once reached, the
   peer can still download models but not contribute.
2. **A per-epoch ε** that sums (under advanced composition) to the
   lifetime ε over a reasonable horizon.
3. **A UX surface.** The peer sees how much of their budget has been
   spent, when the next epoch opens, and what they've contributed to.
   Without this, the promise is backed by vibes, not by a real number.

Concrete values for (1), (2), and the composition theorem used are
deployment-time decisions, not protocol-time decisions. Both should be
version-pinned alongside each released model so the ε claim is
auditable after the fact.

## Phased path

Each phase independently shippable; each phase de-risks the next.

1. **Async Flower on a single statistic, plain HTTPS.**
   Use the existing `app/fl/` client and `server/fl/` coordinator.
   Pick one metric (daily HRV mean) and implement it as an FL round:
   on-device computation, unnoised update, HTTPS. This validates the
   round / epoch machinery end-to-end. **No privacy claims yet.**
2. **Add DP-SGD / OpenDP on the client.**
   Per-client contributions are now noised; ε budget tracked per peer.
   The promise starts being substantively true, though the aggregator
   still sees individual (noised) contributions.
3. **Add SecAgg.**
   flwr's SecAgg+. Aggregator now only sees sums. Gradient-inversion
   attacks no longer have individual updates to attack.
4. **Swap HTTPS for Nym on the upload path.**
   Network-layer anonymity. Measure Nym gateway latency, mobile
   battery/data cost, and tail-failure behavior. Feature-flagged
   rollout. Highest surprise risk of any phase.
5. **Anonymous credentials.**
   Close the strong-sybil gap. Evaluate zk-nym vs. a Coconut-style
   scheme based on ecosystem maturity at the time. **Required before
   production use.**
6. **Open the pipe to supervised models.**
   Add model training (starting with `plugins/models/sleep-forecast/`)
   using the same stack. No new privacy work needed — the whole point
   of choosing this architecture now is that models are a trivial
   extension of the same protocol.

## Open parameters

These must be resolved before v1 code lands. The doc lists them here
so follow-up PRs can cite specific decisions.

- **Nym gateway.** Public Nym mixnet vs. self-hosted gateway(s). Cost,
  availability, and credential-issuance implications differ.
- **SecAgg implementation.** flwr's SecAgg+ vs. an extracted standalone
  library. The former keeps the dependency surface tight; the latter
  makes it easier to reuse SecAgg for non-FL tasks later.
- **Anonymous-credential scheme.** zk-nym vs. Coconut vs. a custom
  blind-signature scheme. Depends on Nym's zk-nym maturity at the time
  of implementation.
- **Epoch length and K_min.** How long a round stays open, and the
  minimum number of contributors required to close it. Trade-off: too
  short / too small → weak mixing, easier correlation attacks; too long
  / too large → laggy UX, underutilized DP budget.
- **Lifetime ε, per-epoch ε, composition theorem.** See
  "Privacy-budget accounting" above.
- **Mobile cost.** Nym cover traffic is continuous; measure
  battery / data impact on Tauri mobile before shipping. A
  "contribute only when plugged in and on WiFi" client-side gate is
  the likely mitigation and should be a v1 default.

## FAQ

### Why not federated learning only? Why add Nym on top?

FL hides *content* (raw records never leave) but not *identity*
(the aggregator sees which IP uploaded which gradient). Nym hides
identity on the upload path. DP-SGD + SecAgg harden content
unlinkability further. Each layer solves a different attack; none of
them is redundant.

### Why not Nym-only, drop the FL?

Then the peer is uploading their actual data (noised or not) through
the mixnet. The promise becomes "your data never leaves, except the
version that does — but anonymously." That's a different promise and a
weaker one. FL is what makes the promise literal.

### Why not a trusted third-party aggregator (TPA)?

A TPA requires a legal entity that can see raw contributions and is
trusted not to collude with the shenas operator. That's an
organizational cost, not a cryptographic one — it adds governance
complexity, trust-onboarding, and "what if the TPA is subpoenaed"
questions. SecAgg replaces the TPA with math.

### What happens if a peer goes offline mid-round?

Async FL's "close the round on a time basis" behavior handles this
naturally. SecAgg's standard protocol requires a share-recovery step
for dropped peers (encrypted shares held by other peers let the
aggregator reconstruct the offline peer's mask contribution). flwr's
SecAgg+ implements this.

### Can a peer audit what was learned from them?

Not directly — SecAgg deliberately destroys the link between a peer's
contribution and the aggregate it ended up in. The peer *can* audit
(a) that their device performed the DP-SGD with the committed ε, (b)
that the claimed ε was spent on the claimed artifact. This is the
equivalent of "I can verify my vote was cast, not which candidate it
counted toward." It's the right trade: auditability of the protocol,
not linkability of the contribution.

## References

- The Nym mixnet: Diaz, Halpin, Kiayias, "The Nym Network" whitepaper.
- SecAgg: Bonawitz et al., "Practical Secure Aggregation for
  Privacy-Preserving Machine Learning," CCS 2017.
- Async FL: Nguyen et al., "Federated Learning with Buffered
  Asynchronous Aggregation" (FedBuff), AISTATS 2022.
- DP-SGD: Abadi et al., "Deep Learning with Differential Privacy,"
  CCS 2016.
- Gradient-inversion attacks: Zhu et al., "Deep Leakage from
  Gradients," NeurIPS 2019; Geiping et al., "Inverting Gradients —
  How easy is it to break privacy in federated learning?" NeurIPS 2020.
- OpenDP library: https://opendp.org
