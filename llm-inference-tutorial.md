# LLM Inference Engineering: A Tutorial for All 21 Items

A companion to the *time-to-first-token* roadmap. That repo tells you **what to read and build**. This tells you **what each thing actually is**, the numbers behind it, and the specific mistake most people make.

**How to use this:** read one section (5–10 min), then spend the rest of your 30 minutes on the corresponding build task from the repo. Reading without touching the service is how this becomes trivia.

---

## Part I — The physics (Items 1–3)

Everything downstream is a move on one plot. Get this part wrong and the rest is a bag of tricks.

---

### 1. The roofline model, and why decode is memory-bound

**The idea.** Any kernel is limited by one of two things: how fast the GPU can do math (FLOPS), or how fast it can move bytes from HBM into the compute units (bandwidth). Which one binds depends on **arithmetic intensity** — FLOPs performed per byte loaded.

Plot achievable FLOPS against arithmetic intensity. You get a slanted line (bandwidth-limited) that flattens into a horizontal line (compute-limited). The bend is the **ridge point**.

**The numbers that matter.** For an H100: roughly 990 TFLOPS of BF16 tensor throughput against roughly 3.35 TB/s of HBM bandwidth. Divide them:

```
ridge point ≈ 990e12 / 3.35e12 ≈ 295 FLOPs per byte
```

You need to do ~295 floating-point operations for every byte you load just to keep the tensor cores busy. That's the bar.

**Now the two phases.**

*Prefill* processes the entire prompt at once. A 2,000-token prompt means every weight you load gets used in a 2,000-row matrix multiply. Arithmetic intensity is in the hundreds or thousands. **Compute-bound.** You're above the ridge point.

*Decode* generates one token. For a batch of 1, every weight in the model is loaded from HBM and used for exactly one row of math. Arithmetic intensity ≈ 2 FLOPs per byte. **Memory-bound by a factor of ~150x.** The tensor cores are idle nearly the whole time; you're just streaming weights.

**The consequence — a decode speed ceiling you can compute in your head:**

```
max tokens/sec ≈ memory_bandwidth / model_size_in_bytes
```

An 8B model in FP16 is ~16 GB. On an H100: 3.35 TB/s ÷ 16 GB ≈ **209 tokens/sec**, batch size 1. No kernel optimization gets you past that. The only ways through are: make the model smaller in bytes (quantization), reuse each weight load across more rows (batching), or produce more than one token per weight load (speculative decoding).

That sentence is the entire optimization landscape. Notice how each of the later items is one of those three.

**Why batching is the master lever.** At batch size B, you load the weights once and do B rows of math. Arithmetic intensity scales roughly linearly with B. Batch 128 puts you near the ridge point — which is exactly why serving engines are built around packing the batch as full as possible.

**Your 30-minute exercise.** Take the model you'll serve. Compute its size in bytes at FP16. Compute its per-token decode arithmetic intensity. Look up your GPU's bandwidth and peak FLOPS, get the ridge point, and place both prefill and decode on the plot. Write down your theoretical max decode tok/s. Keep this number — in week 5 you'll compare your measured number against it, and the gap is your optimization headroom.

**Gotcha.** Attention is not the same as the linear layers here. The linears reload weights per step (memory-bound, fixed cost regardless of sequence length). Attention reloads the *KV cache*, which grows with sequence length and with batch size. At long context and large batch, KV traffic — not weight traffic — becomes the dominant term. This is why long-context serving behaves differently, and why item 13 exists.

---

### 2. Deploy vLLM and SGLang, then read their schedulers

**The idea.** These are the two dominant open-source serving engines. They solve the same problem with different core insights, and the contrast is what teaches you the design space.

**vLLM** is organized around **PagedAttention** — KV cache memory as fixed-size blocks with a block table, borrowed straight from OS virtual memory.

**SGLang** is organized around **RadixAttention** — KV cache as a radix tree keyed by token prefix, so any shared prefix across requests is reused automatically rather than recomputed.

**What the scheduler actually does.** Every iteration, it answers: which requests run in this forward pass? It's a constrained packing problem under two budgets — a token budget (how many tokens can go in one batch) and a KV memory budget (how many blocks are free). It must also decide what to do when memory runs out mid-generation: preempt a running request and either swap its KV to CPU or recompute it later.

Read for these specific things:
- Where the token budget is enforced, and what `max_num_batched_tokens` actually gates
- The waiting → running transition, and the admission condition
- The preemption path — this is where your p99 latency comes from
- How prefill and decode requests get mixed in one batch (item 8)

**Your 30-minute exercise.** Serve the same model on both engines, same hardware, same prompt. Save both launch commands verbatim — you'll reuse them for ten weeks. Then send one request with a 2,000-token prompt and one with a 20-token prompt and watch the metrics differ.

**Gotcha.** Don't read the scheduler as literature. Pick one request and trace it: arrival → queue → admission → block allocation → forward pass → block free. If you can't narrate that path in three sentences, you haven't read it yet.

---

### 3. Paged attention from the code, not the blog post

**The problem it solves.** Pre-vLLM, each request got a contiguous KV buffer sized for `max_seq_len`. A request that generates 100 tokens against a 4,096-token reservation wastes 97% of its allocation. Add fragmentation between buffers and published measurements put waste at 60–80% of KV memory. Wasted KV memory means smaller batches, which means (see item 1) worse arithmetic intensity, which means lower throughput. The chain is direct.

**The fix.** Chop KV into fixed-size blocks — 16 tokens is the common default. Blocks live anywhere in a physical pool. Each sequence has a **block table** mapping logical block index → physical block. Internal waste is now bounded by one partial block per sequence, which is where the "under 4% waste" figure comes from.

**The part blogs skip.** Blocks are reference-counted, which enables **copy-on-write sharing**. Two requests with an identical system prompt point at the *same* physical blocks. When one diverges, only the block being written gets copied. This one mechanism is simultaneously: parallel sampling, beam search, and prefix caching (item 7). They aren't three features. They're one feature.

**Read the code in this order:**
1. The block table structure — logical-to-physical mapping
2. The allocator — `can_allocate` / `allocate` / `free`, and how the free pool is managed
3. The fork/COW path — where refcounts increment and where a block gets copied
4. The attention kernel — how it gathers non-contiguous blocks during the attention computation

**Your 30-minute exercise.** Answer in writing: a request is at token 100 with block size 16. It generates token 101. Which blocks exist, what does the block table hold, and what changes? Then: another request arrives sharing the first 64 tokens. What happens to the refcounts? If your answers are vague, read again.

**Gotcha.** The scheduler and the block manager are coupled. The scheduler can only admit a request if the allocator says blocks are available. Read them together or neither makes sense.

---

## Part II — The lens (Items 4–7)

You cannot optimize what you cannot see, and every number below is meaningless without the one after it.

---

### 4. Build observability before you optimize anything

**The idea.** This is sequencing advice, and it's the most commonly ignored item on the list. Instrument first. Every optimization from item 10 onward is a claim, and a claim you can't measure is a vibe.

**Why it's non-negotiable here specifically.** Inference optimizations have *non-monotonic* effects. Speculative decoding helps at low load and hurts at high load. Chunked prefill improves inter-token latency and worsens time-to-first-token. INT4 helps memory-bound decode and can hurt compute-bound prefill. Without measurement across the load curve, you will confidently ship a regression.

**What to instrument, minimum:**
- Request-level: TTFT, inter-token latency, end-to-end latency, input tokens, output tokens
- Engine-level: running requests, waiting requests, KV cache utilization %, preemption count
- Derived: throughput (output tok/s), cost per 1M tokens

**Your 30-minute exercise.** Before touching Grafana, write down the five questions your dashboard must answer. Example: "Is the GPU idle because there's no work, or because requests are blocked on KV memory?" Every panel you build must answer one of those. Panels that answer nothing get deleted.

**Gotcha.** Fix your scrape config now, under trivial load. Discovering that Prometheus is dropping samples while you're running 1,000 concurrent requests wastes an entire session.

---

### 5. Track TTFT, inter-token latency, throughput, queue depth

**The four numbers, and what each one is really telling you.**

**TTFT (time to first token)** = queueing time + prefill time. This is the user-perceived responsiveness of a streaming UI. When TTFT degrades, the question is always *which half* — queueing or prefill? Queue depth (below) is what disambiguates. A rising TTFT with an empty queue means prefill is slow. A rising TTFT with a deep queue means you're admission-limited.

**ITL / TPOT (inter-token latency, time per output token)** = the decode step time. This is the "reading speed" of the stream. It is bounded by item 1's memory-bandwidth ceiling and degrades as batch size grows — you're sharing bandwidth with more sequences.

**Throughput** = total output tokens/sec across all requests. This is the *server's* metric and it is in direct tension with the two above. Bigger batches raise throughput and raise ITL. There is no configuration that optimizes both. Pick which one your SLO cares about.

**Queue depth** (`num_requests_waiting` in vLLM) = requests admitted to the server but not yet in a running batch. This is your leading indicator. It rises *before* latency does, which is why it's the right autoscaling signal (item 15) — CPU utilization tells you nothing on a GPU service.

**The relationship to internalize (Little's Law):**

```
concurrent requests = arrival rate × average latency
```

You cannot independently choose all three. This is why "we'll just add more concurrency" hits a wall.

**Your 30-minute exercise.** Get all four live on one dashboard. Then apply a trickle of load and confirm each panel *moves*. A panel that's flat under load is either broken or measuring the wrong thing.

**Gotcha.** Never average TTFT and ITL into one "latency" number. They come from different phases with opposite bottlenecks and opposite responses to every tuning knob. Collapsing them destroys the finding.

---

### 6. Grafana + Prometheus for inference dashboards

**The idea.** vLLM and SGLang both expose a Prometheus `/metrics` endpoint. Prometheus scrapes and stores; Grafana queries and draws. The engines ship reference dashboard JSON — start there, then delete panels you can't justify.

**The one thing that trips everyone: histograms.** Latency metrics are exported as Prometheus histograms, which are *bucketed counters*, not raw values. You get percentiles via `histogram_quantile()` over `rate()`:

```promql
histogram_quantile(0.99,
  sum(rate(vllm:time_to_first_token_seconds_bucket[5m])) by (le)
)
```

Two consequences most people miss:
- Percentile accuracy is capped by bucket resolution. If the default buckets are coarse in your latency range, your p99 is an interpolation, not a measurement. Check the bucket boundaries against where your latency actually lives.
- **You cannot average percentiles across replicas.** Summing the *buckets* first and then computing the quantile (as above) is correct. Averaging each replica's p99 is not, and it will make your tail look better than it is.

**Your 30-minute exercise.** Build four panels: TTFT p50/p95/p99, ITL p50/p95/p99, throughput, and queue depth + KV utilization on a shared axis. That last pairing is the most informative panel you will own — it shows you whether the engine is starved for work or starved for memory.

**Gotcha.** Scrape interval sets your temporal resolution. At a 15s scrape, a 3-second latency spike is invisible. Go to 5s or lower for benchmark runs.

---

### 7. Prefix caching — turn it on, then find which workloads it helps

**The idea.** If two requests share a token prefix, the KV cache for that prefix is identical. Compute it once, reuse it. vLLM calls this automatic prefix caching (hash-based, block-granular). SGLang's RadixAttention does it with a radix tree over token sequences, with LRU eviction.

**It cuts prefill work — so it moves TTFT, not ITL.** A cache hit skips the compute-bound phase entirely for the shared portion. Decode is untouched.

**Where it wins big:**
- Shared system prompts across all users (near-universal in production)
- Few-shot prompts with a fixed exemplar block
- Multi-turn chat — turn N+1's prefix is turn N's full context. This is a near-100% hit rate on the growing prefix.
- **Agentic loops** — this is your case. Each ReAct iteration re-sends the entire history plus one new observation. Without prefix caching you re-prefill the whole trajectory every single step, and the cost is quadratic in the number of steps.
- Document QA where many questions hit the same document

**Where it does nothing:** unique long prompts with no shared structure — RAG with per-request retrieved chunks placed *before* the shared instructions, for instance.

**The design lesson.** Cache hit rate is a function of *prompt layout*, not of the engine. Put the stable content first — system prompt, tools, exemplars, retrieved documents that repeat — and the volatile content last. If your template interpolates a timestamp or a session ID into the opening line, you have destroyed the hit rate for every request. This is a one-line fix that people spend weeks not finding.

**Your 30-minute exercise.** Run the same workload twice — once with a shared 1,000-token system prompt across all requests, once with unique prompts. Measure TTFT both times, cache on and off. You'll have four numbers and the shape of the win will be obvious. Then, separately: move a variable field from the start of your prompt to the end and re-measure.

**Gotcha.** The prefix cache competes with running requests for the same KV memory pool. On workloads with no reuse, caching is roughly free but not free — you're spending memory on hashing and blocks that never get hit. Measure it, don't assume.

---

## Part III — Scheduling (Item 8)

---

### 8. Continuous batching and chunked prefill

These are two separate ideas that both live in the scheduler, and both exist to keep the GPU from idling.

**Continuous batching (iteration-level scheduling).**

*The problem:* static batching. Group 8 requests, run them together, wait for all 8 to finish. Output lengths are heavy-tailed — one request generates 800 tokens, seven generate 50. Seven slots sit idle for 750 steps. GPU utilization collapses.

*The fix (from Orca, OSDI 2022):* schedule at the granularity of a single decode iteration, not a whole request. A sequence that hits EOS leaves the batch immediately; a waiting request takes its slot on the very next iteration. The batch composition changes every step.

*Why it matters so much:* it's a direct play on item 1. Keeping the batch full keeps arithmetic intensity high. The heavy tail of output lengths is precisely what makes the improvement large — the more variable your output lengths, the bigger the win.

**Chunked prefill.**

*The problem it solves is subtle and worth getting right.* Prefill and decode compete for the same GPU. A long prefill — say 8,000 tokens — is one big compute-bound forward pass that occupies the GPU for hundreds of milliseconds. Every request currently decoding is **stalled** for that entire duration. Users see the stream freeze. Your ITL p99 is destroyed by other people's long prompts.

*The fix (Sarathi-Serve):* split the prefill into chunks — e.g. 512 tokens — and schedule each chunk in a batch *alongside* decode tokens from running requests. Decode never stalls for more than one chunk's time.

*The trade:* that request's own TTFT goes up slightly (its prefill is now spread over several iterations), while everyone else's ITL becomes dramatically smoother. It converts a rare catastrophic tail into a small uniform cost. It's now the default scheduling strategy in both major engines.

*The bonus:* decode batches are memory-bound and leave FLOPs on the table. Prefill chunks are compute-bound. Mixing them uses both resources in the same pass. It's the same insight that motivates disaggregation (item 14), applied within one GPU instead of across two.

**Your 30-minute exercise.** Run a workload mixing short-prompt and 8,000-token-prompt requests. Measure ITL p99 with chunked prefill off, then on. Then sweep the chunk size — you'll find a knee where TTFT damage starts outrunning the ITL benefit. That knee is workload-specific and it's your tuning knob.

**Gotcha.** The chunk size interacts with `max_num_batched_tokens`. Set the chunk too large and you're back to stalling; too small and per-iteration overhead dominates and prefill throughput drops. Sweep it, don't guess.

---

## Part IV — Measurement done right (Items 9–10)

---

### 9. Load tests with 1000+ concurrent requests

**Why the number is high.** Serving systems are non-linear. At low concurrency the batch is never full and you're measuring latency. At high concurrency you're measuring the scheduler, the KV memory ceiling, and the preemption path. Everything interesting about the system lives at the second regime, and you cannot extrapolate to it from the first.

**Sweep, don't pick.** A benchmark at one concurrency level is an anecdote. Sweep 1, 2, 4, 8 … 128 … 1024 and plot throughput against latency. The resulting curve has three regions:

1. **Linear** — throughput rises, latency flat. The batch has room.
2. **The knee** — throughput approaches its ceiling, latency starts climbing. **This is the only interesting point on the curve.** It's your capacity number and your operating point.
3. **Saturation** — throughput flat or falling, latency exploding, KV cache full, requests being preempted. Numbers measured here are not publishable; you're measuring queueing, not serving.

**Get the workload shape right.** Fix input and output token lengths explicitly and report them. KV cache size — and therefore how many requests fit in a batch — depends entirely on sequence length. A benchmark that doesn't state its token lengths is uninterpretable. And avoid uniform-length synthetic traffic: uniformity hides the heavy tail that makes continuous batching matter in the first place, so it flatters your results.

**Cross-check with two tools.** GuideLLM, `vllm bench serve`, genai-perf, LLMPerf. When two tools disagree, that's information — usually about tokenizer differences, or about whether the client is the bottleneck.

**Your 30-minute exercise.** Script the sweep so it's one command. Run it, plot throughput vs p99 latency, and mark the knee. Then verify: at your peak concurrency, is the client machine itself saturated? A Python client with insufficient concurrency will happily benchmark itself instead of your server.

**Gotcha.** Watch `num_requests_waiting` and KV utilization *during* the run. If TTFT spikes and the queue climbs before you reach your target concurrency, the server is preempting — stop and tune `--max-num-seqs`, `--gpu-memory-utilization`, and chunked prefill before collecting any numbers. A run measured at the preemption point is not a result.

---

### 10. Report p50, p95, p99 — never just the mean

**The idea.** Latency distributions in serving systems are heavily right-skewed, and the mean sits well below the experience of a meaningful fraction of your users. If p50 is 200 ms and p99 is 4 s, the mean might be 400 ms — a number that describes nobody.

**Why the tail is fat here specifically.** Three mechanisms, all of which you now understand:
- **Queueing** — a request arriving when the batch is full waits an unbounded time.
- **Preemption** — under KV pressure the scheduler evicts a running request. It gets recomputed later. That request's latency is now several times the median.
- **Head-of-line blocking from long prefills** — the exact thing chunked prefill exists to fix.

Every one of those is invisible in a mean, and every one of them is the thing your users complain about.

**Report percentiles separately for TTFT and ITL.** They have different distributions and different causes. TTFT p99 is a queueing/prefill story. ITL p99 is a batch-pressure/preemption story.

**Always state the load.** "p99 TTFT = 800 ms" is meaningless alone. "p99 TTFT = 800 ms at 64 concurrent, 1024 in / 256 out, on one H100" is a result. Percentiles are properties of a distribution, and the distribution is a property of the load.

**Your 30-minute exercise.** Add p50/p95/p99 panels for TTFT and ITL. Then compute the mean alongside them and watch how far apart the mean and p99 drift as you increase load. That divergence is your intuition calibration.

**Gotcha.** At 100 samples, your "p99" is one data point and it's noise. You need thousands of requests per configuration for a stable p99. And see item 6 — never average percentiles across replicas.

---

## Part V — The tuning knobs (Items 11–14)

Every one of these is a move on the roofline plot. Say which one before you turn it.

---

### 11. Quantization tradeoffs (FP8, INT4, AWQ, GPTQ)

**Why it works at all.** From item 1: decode is bandwidth-bound and the bytes being moved are mostly weights. Halve the bytes, roughly halve the time. Quantization is the most direct attack on the memory-bound regime there is.

**The formats:**

**FP8** (E4M3) — 8-bit float, hardware-accelerated on Hopper and later. ~2x memory reduction, typically near-lossless on quality, and — importantly — the *matmul itself* runs in FP8 on supported hardware, so it helps compute-bound prefill too. This is the current default recommendation for most production serving on modern GPUs.

**INT4 weight-only** — 4x weight memory reduction. Weights are stored at 4 bits and **dequantized to FP16 on the fly** before the matmul. That's the crucial detail: you save bandwidth but *add* compute. Big win when memory-bound (small batch, decode), potentially a *loss* when compute-bound (large batch, prefill). The crossover is real and you should find yours.

**GPTQ** — post-training quantization that minimizes layerwise reconstruction error using second-order (Hessian) information, quantizing weights column by column and updating the remainder to compensate. Calibration-based.

**AWQ** — activation-aware. The insight is that a small fraction of weight channels are salient, identified by *activation* magnitude rather than weight magnitude. Protect those by per-channel scaling before quantizing. No backprop, generally better preservation than naive round-to-nearest, and usually faster kernels.

**KV cache quantization is a separate lever.** FP8 KV cache roughly doubles the number of sequences that fit in memory, which raises max batch size, which raises throughput. On long-context workloads this can matter more than weight quantization — the KV cache is the thing growing.

**Your 30-minute exercise.** Serve FP16, FP8, and an AWQ/GPTQ INT4 checkpoint. Run the *same* sweep from item 9 on each. Build a table: throughput, TTFT p99, ITL p99, peak memory, and a quality proxy. **The table is the deliverable, not the speedup number.**

**Gotcha.** A quantization result without a quality measurement is worthless. Run a fixed eval set or a perplexity proxy on every variant. And a decision rule worth adopting: if INT4 costs you more than 1–2% on your quality proxy, keep FP8 as the default and treat INT4 as a *memory-pressure* lever — something you reach for when you need bigger batches or longer contexts — rather than a throughput default.

---

### 12. Speculative decoding, and where it stops helping

**The idea.** Decode is memory-bound: you're burning bandwidth and leaving FLOPs unused. Speculative decoding spends those free FLOPs to buy back sequential memory loads.

A cheap **draft** model proposes *k* tokens. The **target** model verifies all *k* in a single forward pass — because verification is a parallel operation over the proposed sequence, exactly like prefill. A rejection-sampling scheme accepts the longest correct prefix. Accepted tokens are guaranteed distributionally identical to what the target would have produced alone. **The output distribution is preserved exactly.** This is not an approximation.

The win: you did one target forward pass — one full weight load — and got up to *k+1* tokens instead of 1.

**The metric that decides everything: acceptance rate.** Speedup is roughly the mean accepted length per verification step, minus draft overhead. High acceptance means the draft model agrees with the target, which depends on how well-matched they are and on how predictable the text is. Code and structured output accept well. Creative or high-entropy text accepts poorly.

**Where it stops helping — the crossover.** This is the item's whole point. At **low QPS**, the GPU is memory-bound with idle FLOPs, and the extra verification compute is genuinely free. Published vLLM benchmarks show up to ~2.8x at QPS 1.

At **high QPS**, continuous batching has already filled the batch. You're now near the compute roof — the FLOPs are *not* free anymore. Verification compute directly competes with real work, and every rejected token is pure waste. The same benchmarks show 1.4–1.8x *slowdown* at high QPS.

So the two main throughput techniques are in tension: **batching and speculation both consume the same idle FLOPs, and you can only spend them once.**

**Variants.** EAGLE (draft on the target's hidden features rather than a separate model), Medusa (multiple decoding heads), and n-gram/prompt lookup (no draft model at all — copy from the prompt, which works remarkably well for summarization and code editing where output overlaps input heavily).

**Your 30-minute exercise.** Enable it, then measure ITL across the full QPS range from 1 to saturation. Plot the speedup ratio against QPS and find where it crosses 1.0. **That crossover point is the finding** — it's more useful to publish than any single speedup number, and it tells you whether to enable this in production at all.

**Gotcha.** If your production traffic sits above the crossover, speculative decoding is a pure regression. Many people benchmark at QPS 1, see 2x, ship it, and slow down their production system. Measure at *your* load.

---

### 13. KV cache eviction for long contexts

**The problem.** KV cache size scales linearly with sequence length *and* batch size:

```
KV bytes ≈ 2 × layers × kv_heads × head_dim × seq_len × batch × dtype_bytes
```

(the 2 is K and V). At 128K context this dwarfs the model weights. It's also the term that makes long-context decode slow — from item 1's gotcha, you're now bandwidth-bound on *KV traffic*, not weight traffic.

**Three distinct strategies, often confused:**

**(a) Eviction — drop tokens from the cache.**
- **StreamingLLM / attention sinks:** the observation is that models allocate large attention mass to the first few tokens regardless of semantic content — they act as "sinks." Keep the first few tokens plus a sliding window of recent ones, drop the middle. Enables effectively unbounded streaming at fixed memory, with reported speedups over sliding-window-with-recomputation of over 20x. **Caveat: this does not extend the model's effective context.** Evicted content is gone. It's for endless streaming conversation, not for long-document reasoning.
- **H2O / SnapKV:** score tokens by accumulated attention and evict low scorers. More content-aware, more overhead.

**(b) Offloading — move KV to CPU RAM or NVMe and bring it back on demand.** Nothing is lost; you trade PCIe bandwidth for HBM capacity. Only worth it when the transfer is cheaper than recomputation.

**(c) Prefix cache eviction (LRU).** Different thing entirely — this is managing the *shared* cache from item 7 under memory pressure. Which cached prefixes do you keep when you need blocks back?

**Your 30-minute exercise.** Build a genuinely long-context workload — 32K+ prompts — and watch KV utilization pin. Then configure an eviction strategy and measure memory, TTFT, ITL, **and a quality check on content from the evicted region.** The quality check is the point. Anyone can make it fast by throwing away the context.

**Gotcha.** Eviction is lossy in a way quantization isn't. Before reaching for it, check whether GQA/MQA (fewer KV heads) or FP8 KV quantization gets you the memory you need without dropping anything.

---

### 14. Disaggregated prefill and decode serving

**The idea.** Item 1 established that prefill is compute-bound and decode is memory-bandwidth-bound. On a single GPU they fight: prefill wants big compute-dense passes, decode wants maximum batch and bandwidth, and each interferes with the other's latency profile. Chunked prefill (item 8) mitigates this *within* one GPU. Disaggregation attacks it architecturally — run the phases on **separate GPU pools** and ship the KV cache between them.

**What you gain:**
- Each pool is tuned for its own bottleneck — different batch sizes, different parallelism strategies, potentially different hardware. Splitwise showed prefill on H100s and *power-capped* A100s for decode giving ~1.4x throughput at ~20% lower cost.
- Independent scaling. Prompt-heavy workloads (document analysis) need prefill capacity; generation-heavy workloads (long-form writing) need decode capacity. One cluster no longer has to be sized for both.
- No interference: TTFT and ITL SLOs become independently satisfiable. DistServe reported serving 7.4x more requests or holding 12.6x tighter SLOs under this split.

**What it costs.** You must transfer the full KV cache for the prompt from the prefill GPU to the decode GPU. That's potentially gigabytes per request, and the transfer sits directly in the critical path of TTFT. This is why it needs NVLink or RDMA, and why it only pays off above a certain scale. Mooncake reframes the whole architecture around this — treating the KV cache as the central resource with a distributed pool.

**Your 30-minute exercise.** Read DistServe's motivation section for the SLO argument, then look at how vLLM and SGLang each implement the phase split. Compare *where* they put the KV transfer. If you have the hardware, run it; if not, understanding when the transfer cost is worth paying is 80% of the value.

**Gotcha.** This is a scale technique. Below a few GPUs it's pure overhead. Know why it exists before deciding you need it — the failure mode is adopting a Mooncake-shaped architecture for a two-GPU deployment.

---

## Part VI — Operations and economics (Items 15–18)

---

### 15. Kubernetes for AI workloads, and autoscaling on queue depth

**What's different about GPU serving on Kubernetes.** Almost every default assumption from web-service autoscaling is wrong here:

- **GPUs are indivisible.** Standard Kubernetes scheduling allocates whole GPUs. You can't run 0.3 of a pod.
- **Cold start is minutes, not seconds.** Pulling a container image and loading 16 GB of weights into HBM takes real time. By the time a new replica is ready, your traffic spike is over. This changes autoscaling from reactive to *predictive* — you scale on leading indicators and keep warm capacity.
- **Instances are expensive enough that idle capacity is a real budget line**, which is in direct tension with the previous point. Sizing this trade is the actual job.

**Why queue depth, not CPU.** During heavy decode, the GPU is saturated and the *CPU is nearly idle*. A CPU-based HPA on a GPU inference service will never fire, no matter how badly you're overloaded. It's the single most common deployment mistake in this space.

Scale on `num_requests_waiting` (or a TTFT SLO breach rate). From item 5: queue depth rises *before* latency does. That lead time is exactly what you need to cover cold start. Wire it up with KEDA or the Prometheus Adapter, exposing the engine's metric as a custom metric.

**Your 30-minute exercise.** Deploy your service with a Helm chart (the vLLM production stack charts are a reasonable starting point) on a managed cluster or `kind`. Configure an HPA on the waiting-requests metric. Then drive load and watch it scale. Measure how long from queue-depth-rise to new-replica-ready — that number determines how aggressive your threshold has to be.

**Gotcha.** If Kubernetes plumbing starts eating whole sessions, bail out to single-node Docker and just read the autoscaling material. The *signal choice* is the lesson; the cluster is incidental.

---

### 16. How inference costs break unit economics

**The formula.** Everything follows from this:

```
cost per 1M tokens = (GPU $/hour) / (tokens/sec × 3600 × utilization) × 1,000,000
```

**Utilization is the term that dominates, and it's the one people ignore.** Halving your GPU hourly rate halves cost. Going from 20% to 80% utilization *quarters* it. Most self-hosted deployments run at low utilization because they're provisioned for peak, which means their real cost per token is several times the number they computed from peak throughput. Traffic is diurnal; your GPU bill is not.

**Why this breaks product economics specifically:**

- **Cost is per token, but pricing is usually per seat or per request.** A power user can cost 100x the median user on the same subscription. The distribution of usage is fat-tailed and your pricing model probably assumes it isn't.
- **Output tokens cost far more than input tokens.** Prefill processes the whole prompt in parallel (compute-bound, efficient); decode is one memory-bound step per token. A 100-token output can cost more than a 5,000-token input. Any cost model that treats them as equivalent is wrong.
- **Agentic workloads multiply everything.** N reasoning steps means N inference calls, each with a context that grows monotonically. Cost scales roughly quadratically with trajectory length unless prefix caching (item 7) is doing its job. This is your case, and it's the reason item 7 sits so early in the list.
- **Long context is quadratic in attention and linear in KV memory.** Doubling context more than doubles cost.

**The reason this list ends where it does.** Character.AI reported roughly a 33x serving cost reduction — via int8 across weights, activations *and* KV cache, plus multi-query attention and cross-layer KV sharing. Every one of those levers is something from items 11–13. The optimizations aren't academic; they're the difference between a viable business and a subsidy.

**Your 30-minute exercise.** Take your measured throughput from item 9 (at the knee, not at peak) and your actual GPU hourly rate. Compute your real cost per 1M tokens. Then compute it again at 30% utilization. Compare both against the API price of a commercial model of similar capability. That comparison is the honest answer to "should we self-host," and it's usually more surprising than people expect.

**Gotcha.** Use throughput at the *knee*, not at saturation. Saturation throughput is a number you can't actually serve at without violating your latency SLO.

---

### 17. Build your own model router by cost, latency, quality

**The idea.** Not every request needs your largest model. A router classifies incoming requests and dispatches to the cheapest backend that will satisfy the requirement. It's the one component that forces a dollar figure and a latency budget into actual code.

**Routing strategies, in increasing order of sophistication:**

1. **Static rules** — by endpoint, user tier, or task type. Boring, robust, surprisingly effective. Start here.
2. **Cascade** — try the small model, evaluate the response (a verifier, a confidence signal, a rubric), escalate on failure. You pay the small model's cost on the majority of requests and both models' cost on the minority. Works when your escalation rate is genuinely low and your escalation *check* is cheap.
3. **Learned routing** — a small classifier predicts which model will succeed, trained on labeled request/quality pairs. Best results, most operational burden — the classifier drifts as your traffic changes.

**What to log on every routing decision** (this is the part people skip, and it's what makes the router improvable):
- Which backend was chosen and *why* — the feature values that drove the decision
- Actual cost, actual latency, and any quality signal you can capture
- **Counterfactual estimate:** what would the alternative have cost?

Without that last field you can never answer "is the router better than always using the big model?" — which is the only question that matters about it.

**Your 30-minute exercise.** Build the thin version: two backends (small/cheap, large/expensive), one policy, and Prometheus metrics for chosen-path and per-request cost. Then put cost per request on the dashboard next to latency. Seeing them side by side changes how you tune everything else.

**Gotcha.** The router's own latency is in the critical path of every request. A learned classifier that adds 80 ms of TTFT to save $0.0001 is a bad trade. Measure the router's overhead as carefully as you measure the backends.

---

### 18. Create a token budgeting system per request

**The idea.** Unbounded token consumption is the primary cost failure mode, and in agentic systems it's also a *correctness* failure mode. A budget makes consumption an explicit, enforced parameter rather than an emergent property.

**What to enforce, at three levels:**

**Per request** — a hard `max_tokens` on output, a maximum input length with a defined truncation or rejection policy, and a total budget that is checked *before* dispatch, not discovered after.

**Per session/user** — rolling window quotas, tier-based caps, and graceful degradation (route to the cheaper model when the budget is nearly exhausted, rather than hard-failing).

**Per agent trajectory** — this is the one that matters for what you're building. Carry a token budget *in the graph state* and decrement it at every node. When it's exhausted, the graph must route to a terminal summarization node — not simply error out. This is exactly the "termination pressure" point from your graph list: a token budget is one of the concrete mechanisms that makes a cycle terminate.

**The accounting detail everyone gets wrong.** Count prefill and decode tokens separately with separate prices. They have different costs (item 16) and conflating them makes your cost attribution wrong by a large factor on prompt-heavy workloads. Also account for cached-prefix tokens separately — a cache hit means you didn't pay for that prefill, and if you don't track it you'll never be able to prove prefix caching is earning its keep.

**Your 30-minute exercise.** Write middleware that enforces a per-request budget, rejects or truncates over-budget requests with a clear error, and emits `tokens_in`, `tokens_out`, `tokens_cached`, and `cost_usd` to Prometheus. Then add a cost-per-request panel to the dashboard.

**Gotcha.** Budget enforcement must happen *before* the request enters the engine's queue. Rejecting a request after it has consumed KV blocks and scheduler slots means you paid for it anyway.

---

## Part VII — The habit (Items 19–21)

---

### 19. Build one inference service and benchmark it publicly

**Why one service rather than many experiments.** Seventeen disconnected tutorials spend most of their time on setup and leave you with nothing. One service that grows across ten weeks gives identical topic coverage, forces every optimization to be measured against a consistent baseline, and leaves you with an artifact.

**The publishing checklist — these are the things that get public inference benchmarks taken apart:**

- [ ] Sweep the request rate. One concurrency level is an anecdote.
- [ ] Report exact input and output token lengths — KV size, and therefore everything, depends on them.
- [ ] Report p50, p95, p99. Means hide the tail users feel.
- [ ] Keep TTFT and ITL separate. Collapsing prefill and decode destroys the finding.
- [ ] Don't measure at saturation where the server is preempting. Report the knee.
- [ ] Avoid uniform-length synthetic traffic — it hides the heavy tail that makes continuous batching matter.
- [ ] Account for tokenizer differences before comparing tokens/sec across engines.
- [ ] Pin engine versions and publish exact commands, so a critic can reproduce rather than speculate.

**Publish negative results.** "Speculative decoding slowed us down above QPS 12" is more valuable, more credible, and more distinguishing than another 2x speedup claim. The crossover points are the contribution.

**Gotcha.** A benchmark nobody can reproduce is a blog post. Pinned versions plus copy-pasteable commands is the entire difference.

---

### 20. Read inference research instead of model release news

**Why.** Model releases are marketing with a benchmark table attached, they're obsolete in weeks, and knowing about them doesn't change what you build. Systems papers describe mechanisms that stay true across model generations. PagedAttention (2023) and continuous batching (2022) still govern how every engine works today.

**Where to look:** arXiv cs.DC, MLSys, OSDI, NSDI, ATC, and the efficiency tracks at NeurIPS. For applied writing: the vLLM and LMSYS blogs, and Modal's LLM Almanac.

**How to read one in 30 minutes** — this is a skill, and the trick is to *not* read the whole paper:
1. Abstract — what's the claim and how big is the number?
2. The motivation figure — almost every systems paper has one plot that justifies its existence. Understand that plot and you understand the paper.
3. The method figure — what's the actual mechanism?
4. Evaluation setup — **what's the baseline, and is it fair?** This is where papers oversell.
5. One limitation you can articulate yourself.

Skip the related work and the proofs unless something specific pulls you in.

**Your habit.** One 30-minute session per week. Queue three papers, read one properly. Consistency beats depth here.

**Gotcha.** Treat every performance figure in a paper as "the number that source is willing to defend on their hardware," not as ground truth for yours. Baselines in systems papers are frequently under-tuned. Your own harness is the only number you actually know.

---

### 21. Start sharing your optimization benchmarks

**Why it's on the list.** Three reasons, and only the first is obvious:

1. **Publishing forces rigor.** You will not sweep the request rate for yourself. You will if strangers can check it.
2. **Criticism you can answer is proof the harness is real.** A benchmark that survives scrutiny is a much stronger signal than one that was never examined.
3. **It's the highest-leverage credential in this field right now.** Reproducible inference benchmarks are scarce because they're tedious. That scarcity is your opportunity.

**What to share:** the crossover points and the negative results. Where speculative decoding stopped paying. Where INT4's quality cost exceeded its throughput gain. Where prefix caching hit rate collapsed because of a prompt-layout bug. These are what other engineers actually need and can't get from vendor blogs.

**Gotcha.** Publish the exact configuration alongside every claim. An unqualified "vLLM is faster than SGLang" is both wrong and unhelpful — the honest version is always "on this workload, this hardware, these token lengths, this version."

---

## The dependency graph

The repo's ordering isn't arbitrary. Here's why:

```
    [1] Roofline
         |
    ------------------------------
    |            |               |
[2,3] Engines  [4,5,6] Observability
    |            |
    ------------------------------
         |
    [7,8] Scheduling & caching
         |
    [9,10] Load testing  <-- nothing after this is verifiable without it
         |
    ------------------------------
    |       |       |       |
  [11]    [12]    [13]    [14]   Tuning knobs
    |       |       |       |
    ------------------------------
         |
    [15] Operations
         |
    [16,17,18] Economics
         |
    [19,20,21] Publish & habit
```

Two hard prerequisites: **roofline before any optimization** (otherwise the knobs are a bag of tricks), and **measurement before tuning** (otherwise you can't tell a win from a regression). Everything else has some slack.

---

## Connecting this to your agentic work

Since you're building agentic workflows, four of these items pay off immediately and disproportionately:

**Prefix caching (7)** is the single highest-leverage item for you. Every agent iteration re-sends the full trajectory. Without caching you re-prefill everything on every step and cost grows roughly quadratically with trajectory length. Structure your prompts stable-content-first and this mostly disappears.

**TTFT vs ITL (5)** splits by node type. A router node emitting 20 tokens is TTFT-dominated — optimize prefill and queueing. A synthesis node emitting 2,000 tokens is ITL-dominated — optimize decode. Tuning one config for both is how agent latency stays mysteriously bad.

**Token budgeting (18)** is your cycle-termination mechanism, carried in graph state. It's the same idea as the iteration cap, but denominated in the thing that actually costs money.

**The router (17)** maps directly onto node-level model selection. Classification and routing nodes rarely need your largest model; synthesis usually does. Per-node model selection is often the largest single cost reduction available in an agent system, and it's usually free in quality terms.

The through-line with your graph work: **make the deterministic parts cheap and measurable, and spend expensive inference only where judgment is genuinely required.**
