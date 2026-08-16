# The Math Under Transformers: An 8-Week Plan

**Goal:** by the end, every symbol in the transformer equations should feel like a *mechanism* you could rebuild, not notation you recognize.

**Format:** 8 weeks, 30 minutes a day, 5 days a week plus 2 buffer days. Same shape as your inference roadmap.

**The artifact:** one file, `nanograd.py`, that grows every week. By week 8 it's a working transformer — forward and backward — in pure NumPy, with no autograd, verified against PyTorch. If you can build that, you understand the math. There is no way to fake it.

**The rule that makes this work:** implement in NumPy first, then check against PyTorch. NumPy has no autograd and no `nn.Linear`, so it won't let you skip a step. PyTorch is your answer key, not your tool.

---

## Read this before you start

**Why math-first is the right call here, but only if you bound it.**

The failure mode of "learn the math first" is spending four months on measure-theoretic probability and never building anything. The failure mode of "just build it" is `attention = softmax(Q @ K.T / sqrt(d)) @ V` as an incantation you can type but not modify.

This plan avoids both by making every mathematical concept earn its place: it appears only when a specific line of transformer code needs it. If a topic doesn't show up in a transformer, it's not here — no determinants, no eigendecomposition proofs, no Lagrange multipliers.

**What you can safely not learn** (common time sinks that don't appear in transformers): matrix determinants, Cramer's rule, eigendecomposition by hand, most of multivariable integration, real analysis, measure theory, and the vast majority of a standard linear algebra course. You need a specific 20% of it.

**Prerequisites.** High school algebra, and comfort reading a function definition. That's it. If you've forgotten what a derivative is, week 3 rebuilds it.

---

## Diagnostic: what to skip

Answer these honestly before starting. Each one you can answer confidently in 30 seconds means you can compress that week to its build session.

1. Why does the dot product of two vectors tell you anything about their similarity?
2. What does it mean geometrically to multiply a vector by a matrix?
3. What is the gradient of `f(x,y) = x²y` at `(2,3)`, and what does that vector *point at*?
4. Why does `softmax` need to subtract the max before exponentiating?
5. What is cross-entropy actually measuring, in units?
6. Why does Adam converge faster than plain SGD?
7. Why does LayerNorm help training, given it throws away scale information?
8. In `Q @ K.T / sqrt(d_k)`, where does the `sqrt(d_k)` come from?

You already have #4 and probably #8 in rough form from the sampling and roofline work. If you got 6+, skip to week 8 and build the thing — you'll find your gaps fast.

---

## Python setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install numpy torch matplotlib jupyterlab einops
```

CPU-only PyTorch is fine for all eight weeks. Nothing here needs a GPU.

**Five practices that will save you more time than anything else:**

**1. Shape assertions everywhere.** 90% of your bugs will be shape bugs, and NumPy's broadcasting will silently do something plausible instead of erroring.

```python
def attention(Q, K, V):
    B, H, T, d = Q.shape
    assert K.shape == (B, H, T, d), f"K shape {K.shape}"
    scores = Q @ K.transpose(0, 1, 3, 2)
    assert scores.shape == (B, H, T, T), f"scores {scores.shape}"
    ...
```

Write the assertion *before* the line that produces the value. It turns a debugging session into an immediate error.

**2. Name your dimensions in comments — or use einsum.**

```python
# B=batch, T=time/tokens, H=heads, d=head_dim, D=model_dim
scores = np.einsum('bhtd,bhsd->bhts', Q, K)
```

`einsum` is slower but self-documenting. Use it while learning, optimize later. The letters *are* the shape assertion.

**3. Gradient-check every backward pass you write.** This is non-negotiable and it's how you'll know your math is right:

```python
def grad_check(f, x, eps=1e-5):
    """Compare analytic gradient against finite differences."""
    analytic = f.backward(x)
    numeric = np.zeros_like(x)
    it = np.nditer(x, flags=['multi_index'])
    for _ in it:
        i = it.multi_index
        old = x[i]
        x[i] = old + eps; plus = f.forward(x)
        x[i] = old - eps; minus = f.forward(x)
        x[i] = old
        numeric[i] = (plus - minus) / (2 * eps)
    rel_err = np.abs(analytic - numeric) / (np.abs(analytic) + np.abs(numeric) + 1e-9)
    return rel_err.max()
```

Relative error below `1e-7` means correct. Above `1e-4` means a bug. Between them, usually float32 noise — rerun in float64 to check.

**4. Verify against PyTorch on every component.**

```python
import torch
mine = my_softmax(x)
theirs = torch.softmax(torch.from_numpy(x), dim=-1).numpy()
assert np.allclose(mine, theirs, atol=1e-6)
```

**5. Plot things.** A histogram of activations, a heatmap of attention weights, a loss curve. Numerical intuition comes from seeing distributions, and half the "aha" moments in this plan are visual.

**On AI assistance:** use it to explain concepts and check your reasoning. Do not use it to write your implementations. The implementations *are* the learning; outsourcing them leaves you exactly where you started.

---

# Week 1 — Vectors: meaning as geometry

**The real-world question:** how can a list of numbers represent the meaning of a word?

**The answer that makes it click:** it can't, on its own. A single embedding vector means nothing in isolation. Meaning lives in *relationships between* vectors — which directions are close, which are far, which differences are parallel. A word embedding is a position in a space where geometric relationships mirror semantic ones.

## Concepts

**Vectors as points and as directions.** A 768-dimensional embedding is a point in 768-space. You cannot visualize this and you should stop trying. Instead, trust that every operation you understand in 2D or 3D works identically in 768D — the algebra doesn't care about the dimension count.

**The dot product.** The single most important operation in this entire plan.

```
a · b = Σᵢ aᵢbᵢ = |a| |b| cos θ
```

Those two expressions being equal is the thing to internalize. The left side is a mechanical sum of products. The right side says it measures *alignment*: maximal when the vectors point the same way, zero when perpendicular, negative when opposed.

**In the real world:** the dot product answers "how much do these two things agree?" In attention, `q · k` is literally the question *"how relevant is this token to that one?"* — a query vector asks something, a key vector advertises something, and their dot product is the match score. When you understand this you understand attention, and the rest is bookkeeping.

**Norms and normalization.** `|a| = √(a·a)` is length. Dividing by it gives a unit vector — direction with magnitude stripped out.

**Cosine similarity.** The dot product of two unit vectors: alignment with magnitude removed. Used everywhere in retrieval because for embeddings, direction carries the meaning and magnitude is mostly an artifact of token frequency.

**Projection.** The component of `a` lying along `b`: `(a·b̂)b̂`. This is the geometric core of what every weight matrix does.

**Orthogonality and the curse (blessing) of dimensionality.** In 2D you can fit 2 mutually perpendicular directions. In 768D you fit 768 — but if you allow *near*-orthogonal (say within 5°), you can pack **exponentially** many. This is why a 768-dimensional space can store far more than 768 distinct concepts, and it's the foundation of the superposition hypothesis in interpretability. Features share the space by being nearly, not exactly, independent.

## Python

```python
# Day 1-2: build from scratch, no np.dot
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def norm(a): return dot(a, a) ** 0.5
def cosine(a, b): return dot(a, b) / (norm(a) * norm(b))

# Verify the geometric identity holds
import numpy as np
a, b = np.random.randn(5), np.random.randn(5)
angle = np.arccos(cosine(a, b))
assert np.isclose(dot(a, b), norm(a)*norm(b)*np.cos(angle))
```

```python
# Day 3-4: the experiment that makes dimensionality real
def near_orthogonal_count(dim, n_vectors=10000, threshold=0.1):
    """What fraction of random vector pairs are near-orthogonal?"""
    V = np.random.randn(n_vectors, dim)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    sims = V[:500] @ V[:500].T
    off_diag = sims[~np.eye(500, dtype=bool)]
    return np.mean(np.abs(off_diag) < threshold), off_diag.std()

for d in [2, 3, 10, 100, 768, 4096]:
    frac, sd = near_orthogonal_count(d)
    print(f"dim {d:5d}: {frac:.1%} near-orthogonal, std {sd:.4f}")
```

Watch the standard deviation shrink as `1/√d`. In 4096 dimensions, two random vectors are *almost always* nearly perpendicular. Sit with that — it's why high-dimensional spaces have enormous representational room, and why "random init" is a reasonable starting point at all.

```python
# Day 5: real embeddings
# Download GloVe 50d (small, fast). Then:
#  - nearest neighbours by cosine for a few words
#  - the analogy: king - man + woman ≈ ?
#  - compare cosine vs raw dot ranking. Which words does raw dot favour, and why?
```

That last question matters: raw dot product favours high-magnitude vectors, which tend to be frequent words. That's a real bias, and noticing it yourself is worth more than reading about it.

**Aha to reach:** attention is a similarity search. Every token asks a question (query), every token advertises an answer (key), and the dot product scores the match.

---

# Week 2 — Matrices: learned lenses

**The real-world question:** what is a weight matrix actually *doing* to my data?

**The answer:** it's a learned change of perspective. It takes a vector expressed in one set of concepts and re-expresses it in another. `W_q` doesn't "compute a query" so much as *rotate the embedding into a space where dot products mean relevance*.

## Concepts

**Matrix-vector multiply as a linear map.** `y = Wx`. Two readings, and you need both:

- *Row view:* each output element is a dot product of one row of `W` with `x`. Each row is a "detector" asking one question about the input.
- *Column view:* the output is a weighted sum of the columns of `W`, with `x` supplying the weights. The columns are a set of building blocks, and `x` says how much of each to use.

The column view is the one most people never internalize and it's the more useful of the two for understanding what a network stores.

**Matrix-matrix multiply as composition.** `(AB)x = A(Bx)` — apply `B`, then `A`. Two stacked linear layers with no nonlinearity between them collapse into one matrix. **This is exactly why activation functions exist.** Without them, a 93-layer network is algebraically identical to a 1-layer network. That's the whole justification, and it's a one-line proof you should write out yourself.

**Batched matmul.** In practice you never transform one vector. `X @ W` with `X` of shape `(B, T, D)` applies the same map to `B×T` vectors at once. This is the entire reason GPUs are relevant — and, connecting to your roofline work, it's why prefill (many rows, one weight load) is compute-bound while decode (one row, one weight load) is memory-bound. **The arithmetic intensity difference you computed in week 1 of the inference roadmap is a direct consequence of this shape.**

**Rank and low-rank structure.** Rank is the number of genuinely independent directions a matrix can produce. A `4096×4096` matrix of rank 8 is doing very little — it can be factored as `(4096×8) @ (8×4096)`, using 0.4% of the parameters.

**In the real world:** this is LoRA. It's also the MLA you just read about in the K3 spec — the KV cache is compressed through a low-rank latent projection, which is why the head dimension didn't divide evenly into the hidden dimension. Same math, two applications.

**Transpose.** `(AB)ᵀ = BᵀAᵀ`. Mechanical, but you'll use it in every backward pass in week 3, and getting it wrong is the most common gradient bug.

## Python

```python
# Day 1: implement matmul three ways, verify identical
def matmul_naive(A, B):  # triple loop
    ...
def matmul_rows(A, B):   # each output row = dot products
    ...
def matmul_cols(A, B):   # each output col = linear combo of A's columns
    ...
# Time all three against np.matmul. The gap is ~1000x. That gap is BLAS,
# and it's why nobody writes loops in numerical Python.
```

```python
# Day 2: prove the collapse yourself
W1 = np.random.randn(64, 32)
W2 = np.random.randn(32, 16)
x  = np.random.randn(100, 64)
assert np.allclose((x @ W1) @ W2, x @ (W1 @ W2))
# Now insert a ReLU between them and show it no longer holds.
# Write down in one sentence why this justifies activation functions.
```

```python
# Day 3: low-rank in practice
A = np.random.randn(200, 50) @ np.random.randn(50, 200)  # rank 50, shaped 200x200
U, S, Vt = np.linalg.svd(A)
# Plot S on a log scale. Count how many singular values are non-negligible.
# Then: reconstruct A using only the top k. Plot reconstruction error vs k.
# This one plot explains LoRA, MLA, and low-rank compression generally.
```

```python
# Day 4-5: build a Linear layer as a class with forward().
# Backward comes in week 3, so leave a stub. Match torch.nn.Linear's output
# given the same weights (careful: torch stores weight transposed).
```

**Aha to reach:** `Q = X @ W_q` is not "computing queries." It's projecting every token into a space that was learned specifically so that dot products in it mean relevance. `W_q` and `W_k` are trained as a *pair* — what matters is the bilinear form `W_q W_kᵀ`, not either matrix alone.

---

# Week 3 — Derivatives and the chain rule: how learning happens

**The real-world question:** the model got the answer wrong. How does it know which of 100 billion knobs to turn, and in which direction?

**The answer:** the chain rule, applied mechanically, backwards. Every parameter gets a number saying "if you nudge me up, the loss changes by this much." That's all backpropagation is. It's not an algorithm someone invented for neural networks — it's the chain rule with the intermediate results cached.

## Concepts

**Derivative as sensitivity.** `df/dx` = if `x` moves a tiny bit, how much does `f` move, and in which direction? Forget limits and epsilon-delta. Sensitivity is the working definition.

**Gradient as the steepest-ascent direction.** For `f(x₁...xₙ)`, the gradient `∇f` is the vector of partial derivatives. **In the real world:** you're standing on a hillside in fog. The gradient points directly uphill, and its magnitude is the steepness. Gradient *descent* is walking the other way.

**The chain rule.** `d/dx f(g(x)) = f'(g(x)) · g'(x)`. Sensitivities multiply along a path. A deep network is one long composition, so the gradient at layer 1 is a product of ~93 terms.

**In the real world:** this product is why deep networks are hard to train. Terms consistently under 1 → the product vanishes → early layers get no signal. Terms consistently over 1 → it explodes. Residual connections exist to add a `+1` path through every layer, giving the gradient a route that doesn't multiply down to nothing. That's the entire justification for `x + f(x)` — and it's why K3's "Attention Residuals" are worth a name.

**Jacobians.** When `f: ℝⁿ → ℝᵐ`, the derivative is an `m×n` matrix. The chain rule becomes matrix multiplication. You will rarely build one explicitly — you compute *vector-Jacobian products* instead — but knowing that's what's happening demystifies the shape gymnastics in backward passes.

**The backward pass as bookkeeping.** Forward: compute and cache. Backward: walk in reverse, each node receiving `∂L/∂output` and producing `∂L/∂input` plus `∂L/∂params`. Every layer is one local rule. That's it.

**Key gradients to derive by hand this week** (do these on paper — it's 20 minutes and it converts backprop from magic to arithmetic):

```
y = xW           →  ∂L/∂x = (∂L/∂y) Wᵀ      ∂L/∂W = xᵀ (∂L/∂y)
y = ReLU(x)      →  ∂L/∂x = (∂L/∂y) ⊙ [x>0]
y = a ⊙ b        →  ∂L/∂a = (∂L/∂y) ⊙ b
L = softmax + CE →  ∂L/∂logits = p - y_onehot        ← derive this one twice
```

That last line is worth the whole week. Softmax and cross-entropy have ugly gradients individually, but composed they collapse to `predicted − actual`. Beautifully simple, numerically stable, and the reason the two are always fused in real implementations. Deriving it yourself is the single highest-value 30 minutes in this plan.

## Python

```python
# Day 1-2: build a scalar autograd engine (~100 lines).
class Value:
    def __init__(self, data, _children=(), _op=''):
        self.data, self.grad = data, 0.0
        self._backward = lambda: None
        self._prev, self._op = set(_children), _op

    def __mul__(self, other):
        out = Value(self.data * other.data, (self, other), '*')
        def _backward():
            self.grad  += other.data * out.grad
            other.grad += self.data  * out.grad
        out._backward = _backward
        return out
    # add __add__, tanh, exp, __pow__, and a topological-sort backward()
```

This is Karpathy's micrograd, and rebuilding it from scratch is the best use of two sessions in this entire plan. Once you've written `_backward` for four operations, backprop stops being mysterious permanently.

```python
# Day 3: array-level gradients. Implement Linear.backward() and grad-check it.
# Day 4: derive and implement softmax+cross-entropy fused. Grad-check.
#        Then implement them separately and compare numerical stability
#        at logit magnitudes of 100, 1000. Watch the unfused version blow up.
# Day 5: train a 2-layer MLP on XOR using only your own code. ~30 lines.
#        If the loss goes down, your backward passes are correct.
```

**Aha to reach:** backpropagation is not an algorithm. It's the chain rule with caching, applied to a graph. And `∂L/∂logits = p − y` is why the loss you use and the output activation you use are chosen together, not independently.

---

# Week 4 — Probability: prediction as a distribution

**The real-world question:** the model doesn't output "the next word." It outputs a probability for all 160,000 of them. Why is that the right formulation, and what do those numbers actually mean?

You have a head start here from the sampling and logits work — this week is about making it rigorous and connecting it to *training*, not just inference.

## Concepts

**Random variables and distributions.** A distribution over a vocabulary is a length-`V` vector of non-negative numbers summing to 1. Nothing more exotic than that.

**Conditional probability, and the factorization that defines the whole enterprise.**

```
P(w₁, w₂, ..., wₙ) = ∏ᵢ P(wᵢ | w₁...wᵢ₋₁)
```

**In the real world:** this chain rule of probability is why LLMs are autoregressive, why generation is inherently sequential, and therefore — connecting to your inference work — why decode is memory-bound while prefill isn't. You can evaluate all conditionals in parallel when you already know the tokens (teacher forcing, prefill). You cannot when you're generating them. The entire prefill/decode asymmetry that drives disaggregation traces back to this single equation.

**Softmax as a distribution-maker.**

```
softmax(z)ᵢ = exp(zᵢ) / Σⱼ exp(zⱼ)
```

Three properties to verify yourself:
- Shift-invariance: `softmax(z + c) = softmax(z)`. You know this one — it's why the stable implementation subtracts the max, and why raw logits are only log-odds up to a constant.
- Temperature: `softmax(z/T)`. As `T→0` it becomes argmax; as `T→∞` it becomes uniform. It's a smooth interpolation between "confident" and "clueless."
- It's the maximum-entropy distribution given the logits as constraints — the least-committed distribution consistent with the evidence.

**Expectation and variance.** `E[X]`, `Var(X)`. You need these for two specific purposes: understanding why `√d_k` appears in attention, and understanding weight initialization.

**The `√d_k` derivation.** Do this one properly — it's the single best example of probability theory directly determining an architectural constant. If `q` and `k` have independent components with mean 0 and variance 1, then:

```
q · k = Σᵢ qᵢkᵢ
E[q·k]   = 0
Var(q·k) = d_k        (variance adds over independent terms)
so std(q·k) = √d_k
```

At `d_k = 128`, dot products have a standard deviation of ~11. Feed values that large into softmax and it saturates into a near-one-hot distribution — which means (from week 3) gradients near zero, which means the layer stops learning. Dividing by `√d_k` restores unit variance. **The scaling factor is not a heuristic. It's a variance calculation.**

**Sampling.** Multinomial sampling, and the truncation methods you already know — with the connection made explicit: top-k and top-p are *modifications of the distribution*, applied after softmax, before sampling. Temperature is applied before. That ordering is why the knobs interact.

## Python

```python
# Day 1: implement softmax with and without max-subtraction.
#        Find the logit magnitude where the naive one produces nan.
#        Plot the distribution at T = 0.1, 0.5, 1, 2, 10.

# Day 2: THE key experiment — verify the sqrt(d_k) claim empirically.
for d in [8, 64, 128, 512, 4096]:
    q = np.random.randn(10000, d)
    k = np.random.randn(10000, d)
    dots = np.einsum('ij,ij->i', q, k)
    print(f"d={d:5d}  std={dots.std():8.2f}  sqrt(d)={np.sqrt(d):8.2f}")
# Then: softmax those raw dots vs the scaled ones. Compute the entropy of each.
# Plot max-probability against d for both. The unscaled curve saturating
# toward 1.0 is the failure mode the scaling prevents.

# Day 3: build a bigram character model on any text file. Count pairs,
#        normalize to a distribution, sample from it. ~30 lines, no ML.
#        This is a language model. Everything after is a better estimator
#        of the same conditional.

# Day 4: implement top-k, top-p, min-p from scratch. Verify against
#        an engine's output on the same logits and seed.

# Day 5: entropy of your bigram model's predictions. Which characters
#        is it confident about? Plot the distribution of entropies.
```

**Aha to reach:** `√d_k` is a variance correction, temperature is a distribution reshape, and the autoregressive factorization is the reason your inference stack has two phases with opposite bottlenecks.

---

# Week 5 — Information theory: what the loss function measures

**The real-world question:** why is the training loss called "cross-entropy," and what does a loss of 2.3 actually mean?

**The answer:** it's measured in **nats** (or bits, if you use log₂), and it's literally the average surprise of the model when it sees the true next token. A loss of 2.3 nats means the model is about as surprised as if it were choosing uniformly among 10 options. That's a physically meaningful number, and once you see it that way, loss curves stop being abstract.

## Concepts

**Surprisal.** `I(x) = -log P(x)`. A certain event carries zero surprise; an impossible one carries infinite surprise. The logarithm is what makes surprise *additive* over independent events — two independent surprises sum rather than multiply, which is the property that makes the whole framework work.

**Entropy.** `H(P) = -Σ P(x) log P(x)` — expected surprise. **In the real world:** the theoretical minimum average message length to encode samples from `P`. English text is roughly 1 bit per character; a fair coin is exactly 1 bit per flip; a two-headed coin is 0.

**Cross-entropy.** `H(P, Q) = -Σ P(x) log Q(x)` — your *actual* average cost when you encode using the wrong distribution `Q` while reality follows `P`.

**In the real world:** you built a compression scheme assuming English letter frequencies, then used it on German text. Cross-entropy is your resulting message length. It is always ≥ entropy, with equality only when `Q = P`. **Minimizing cross-entropy = building the best possible compressor of the training data.** This equivalence between prediction and compression is not a metaphor — it's exact, and it's one of the genuinely deep ideas in the field.

**KL divergence.** `KL(P‖Q) = H(P,Q) − H(P)` — the *excess* cost from using the wrong distribution. Zero iff identical, always non-negative, and asymmetric (`KL(P‖Q) ≠ KL(Q‖P)`).

You'll meet KL in three places later: as the regularizer in RLHF/DPO that keeps a fine-tuned model near its base, as the acceptance criterion in speculative decoding, and as the objective in distillation.

**Perplexity.** `PPL = exp(cross-entropy)`. Cross-entropy in "effective vocabulary size" units instead of nats. A perplexity of 10 means the model is as uncertain as if picking uniformly from 10 options. Report it because it's interpretable — a drop from 20 to 10 is a genuine halving of confusion, whereas a loss drop from 3.0 to 2.3 doesn't *look* like much.

**Why cross-entropy and not squared error.** Two reasons, both worth understanding: (1) MSE on probabilities gives tiny gradients when the model is confidently wrong, which is exactly when you need large ones; (2) cross-entropy is the maximum-likelihood estimator for a categorical distribution, so it's the principled choice, not just the convenient one.

## Python

```python
# Day 1: entropy of English. Take a large text file.
#  - order-0 (character frequencies)
#  - order-1 (conditioned on previous char)
#  - order-2, order-3
# Plot entropy in bits/char against context order. It falls from ~4.1 to
# ~2 and keeps dropping. That curve IS the argument for context length.

# Day 2: cross-entropy and KL between your order-1 model and an order-3
#        model. Verify KL >= 0 and KL(P||Q) != KL(Q||P) numerically.

# Day 3: compression, made concrete.
#  - Compute your model's cross-entropy on held-out text, in bits/char
#  - Multiply by the character count -> theoretical compressed size
#  - Run gzip on the same file and compare
# A decent order-3 character model beats gzip. That result should feel
# surprising, and then obvious.

# Day 4: implement cross-entropy loss from scratch, fused with softmax
#        (reuse your week 3 derivation). Grad-check it. Then compute
#        perplexity and sanity-check: an untrained model on a 160K vocab
#        should have PPL ~= 160000 and loss ~= log(160000) ~= 11.98.
#        If your untrained loss isn't ~ln(V), your init or your loss is wrong.

# Day 5: plot loss vs perplexity to build intuition for what loss deltas
#        mean. 11.98 -> 6 -> 3 -> 2. Notice how much harder each step is.
```

**Aha to reach:** training loss is average surprise in nats, `ln(vocab_size)` is your untrained baseline and a free correctness check, and next-token prediction is compression.

---

# Week 6 — Optimization: actually descending

**The real-world question:** you have the gradient. Why is `weights -= lr * grad` not good enough, and what are Adam's `β₁` and `β₂` really doing?

## Concepts

**Gradient descent.** `θ ← θ − η∇L`. Walk downhill. The learning rate `η` is your step size, and it's the single most important hyperparameter in deep learning.

**Why the loss landscape is hard.** Not because of local minima — in high dimensions those are rare, because a critical point needs *all* million eigenvalues negative to be a true local max, which essentially never happens. The real problems are:
- **Saddle points** (some directions up, some down) — these are everywhere.
- **Ravines** — steep in one direction, nearly flat in another. Plain SGD oscillates across the steep walls while crawling along the flat floor. This is the dominant practical problem.

**In the real world:** you're descending a long narrow canyon. Plain gradient descent bounces wall to wall, making almost no progress toward the exit. Every optimizer improvement below is a fix for this specific geometry.

**Stochastic gradient descent.** Estimate the gradient from a minibatch instead of the full dataset. Noisier, but vastly cheaper per step, and the noise itself helps escape saddles. Batch size trades gradient quality against step count.

**Momentum.** `v ← βv + ∇L; θ ← θ − ηv`. An exponentially weighted average of past gradients. **In the real world:** a ball rolling downhill rather than a hiker taking discrete steps. Consistent directions accumulate; oscillating ones cancel. This alone largely fixes the ravine problem.

**Adaptive learning rates (RMSProp).** Track a running average of *squared* gradients and divide by its root. Parameters with consistently large gradients get smaller steps; rarely-updated ones get larger. Effectively a per-parameter learning rate.

**Adam = momentum + RMSProp + bias correction.**

```
m ← β₁m + (1-β₁)g          # first moment  — direction
v ← β₂v + (1-β₂)g²         # second moment — scale
m̂ = m/(1-β₁ᵗ),  v̂ = v/(1-β₂ᵗ)    # bias correction (m,v start at 0)
θ ← θ − η · m̂/(√v̂ + ε)
```

Understand the bias correction: `m` and `v` initialize at zero, so early estimates are biased toward zero. Without correction your first steps are far too small. Defaults `β₁=0.9, β₂=0.999` mean the first moment averages ~10 recent steps and the second ~1000.

**AdamW.** Decoupled weight decay — apply decay directly to weights rather than folding it into the gradient. It's a genuine bug fix, not a tweak, and it's why AdamW is the default for transformers.

**Learning rate schedules.** Warmup then cosine decay. Warmup exists because Adam's second-moment estimate is garbage for the first few hundred steps, so large early steps are dangerous. Decay exists because you want big exploratory steps early and fine adjustments late.

**Initialization.** Deeply connected to week 4's variance math. Xavier/Glorot: `var = 2/(fan_in + fan_out)`. He: `var = 2/fan_in` for ReLU. **The goal is keeping activation variance ≈ 1 through every layer.** Too small and signal vanishes through depth; too large and it explodes. This is the same variance argument as `√d_k`, applied to weights instead of dot products.

## Python

```python
# Day 1: implement SGD, SGD+momentum, RMSProp, Adam as classes with
#        a common step() interface.

# Day 2: THE experiment. Optimize the Rosenbrock function
#        f(x,y) = (1-x)^2 + 100(y-x^2)^2  -- a textbook ravine.
#        Plot the trajectory of each optimizer over a contour plot.
#        SGD zigzagging while Adam walks the floor is the clearest
#        picture of what optimizers do that you will ever see.

# Day 3: learning rate sweep on a small MLP. Log-spaced, 1e-5 to 1e0.
#        Plot final loss vs lr. You get the classic U-curve: too small
#        (no progress), just right, too large (divergence). Find the edge.

# Day 4: initialization. Build a 20-layer linear net. Plot the std of
#        activations at each layer under: all-zeros, N(0,1), N(0,0.01),
#        Xavier, He. Watch three of them die or explode by layer 20.
#        Then add a residual connection and re-plot. The difference is
#        why deep networks are trainable at all.

# Day 5: implement warmup + cosine decay, plot the schedule, then train
#        your XOR MLP with and without it.
```

**Aha to reach:** Adam is momentum for direction plus normalization for scale, warmup exists because of bias correction, and initialization is the same variance argument as `√d_k` in a different costume.

---

# Week 7 — Numerical reality: floats, stability, normalization

**The real-world question:** the math is exact; the hardware is not. Where does that gap bite, and what do LayerNorm and RMSNorm actually fix?

This week connects directly to your quantization work — you'll be deriving from first principles the reason MXFP4/MXFP8 with QAT behaves differently from post-training INT4.

## Concepts

**Floating point as a number system.** `value = sign × mantissa × 2^exponent`. Exponent bits give *range*; mantissa bits give *precision*. Two very different things, and formats trade them differently:

| Format | Exponent | Mantissa | Notes |
|---|---|---|---|
| FP32 | 8 | 23 | baseline |
| FP16 | 5 | 10 | narrow range — overflows easily |
| BF16 | 8 | 7 | FP32's range, less precision — hence its dominance in training |
| FP8 E4M3 | 4 | 3 | inference activations |
| FP4 (MX) | 2 | 1 | plus a shared per-block scale |

**In the real world:** BF16 beat FP16 for training precisely because gradients span an enormous dynamic range, and range matters more than precision when you're summing many small numbers. This is a design choice you can now derive rather than memorize.

**Catastrophic cancellation and why summation order matters.** `(a + b) + c ≠ a + (b + c)` in floating point. Summing a million small numbers naively loses accuracy; pairwise or Kahan summation fixes it. This is why reductions in GPU kernels are written the way they are.

**The stable softmax, revisited with the reason.** `exp(1000)` overflows FP32 instantly. Subtracting the max costs nothing (shift-invariance, week 4) and bounds every exponent at ≤ 0. You knew the trick; now you know it's free because of an algebraic property, not a hack.

**The log-sum-exp trick.** Same idea, generalized. Work in log space wherever you're multiplying many probabilities — which is always, in a language model.

**Normalization layers.**

```
LayerNorm(x) = γ · (x − μ) / √(σ² + ε) + β     # μ, σ over the feature dim
RMSNorm(x)   = γ · x / √(mean(x²) + ε)          # no mean subtraction, no β
```

**In the real world:** LayerNorm puts every token's representation on a comparable footing before the next layer reads it — like converting exam scores to z-scores so different graders' marks can be compared. Without it, activations drift in scale through depth, and (from week 6) that means gradients drift too.

RMSNorm drops the mean-centering. The empirical finding was that re-centering contributes little while re-scaling does the work, and dropping it saves a reduction pass. Nearly every modern LLM uses RMSNorm for exactly this reason — it's a performance win with no measured quality cost.

**Pre-norm vs post-norm.** Pre-norm (`x + f(norm(x))`) leaves the residual path completely clean — the gradient has an unobstructed route from loss to embedding, with no normalization in the way. This is what made very deep transformers trainable without elaborate warmup schedules. Post-norm (the original 2017 design) puts the norm on the residual path and is markedly harder to train deep.

**Quantization error, derived.** You now have everything needed to see why QAT differs from PTQ. Post-training quantization perturbs weights *after* the loss surface is fixed — the model sits at a minimum for the FP16 weights and you've just moved off it. Quantization-aware training makes the perturbation part of the forward pass during training, so gradient descent finds a minimum that is *flat with respect to quantization noise*. It's not that QAT quantizes better; it's that it optimizes a different, more robust objective.

## Python

```python
# Day 1: float exploration.
np.float32(0.1) + np.float32(0.2) == np.float32(0.3)   # False. Why?
np.finfo(np.float32).eps, np.finfo(np.float16).max     # know your limits
# Find the smallest x where 1 + x != 1 in fp32 and fp16.
# Sum 1e6 copies of 0.1 naively, pairwise, and with math.fsum. Compare errors.

# Day 2: stability. Implement naive and stable softmax; find the
#        overflow threshold for each in fp32 and fp16. Implement
#        logsumexp and use it to compute a sequence log-probability.

# Day 3: implement LayerNorm and RMSNorm forward AND backward.
#        (LayerNorm's backward is genuinely fiddly -- mu and sigma both
#        depend on every x_i, so terms you'd expect to vanish don't.
#        Grad-check it. This is the hardest derivation in the plan and
#        the one that most confirms you actually understand the chain rule.)

# Day 4: the depth experiment. 50-layer stack, plot activation std by
#        layer with: no norm, LayerNorm, RMSNorm. Then pre-norm vs
#        post-norm residuals, plotting GRADIENT magnitude by layer.
#        The post-norm gradient decay is visible and dramatic.

# Day 5: quantization from scratch. Write quantize/dequantize for
#        int8 and a block-scaled 4-bit format. Measure reconstruction
#        error on a real weight matrix. Then measure END-TO-END output
#        error through a 10-layer net. Note how per-layer error compounds
#        -- that compounding is what QAT trains the model to absorb.
```

**Aha to reach:** normalization is variance control (again — the third appearance of the same idea), pre-norm exists to keep the residual gradient path clean, and QAT works because it changes the optimization objective, not the arithmetic.

---

# Week 8 — Assembly: the transformer, from the math up

**The real-world question:** put it together. What is attention, in the language of the previous seven weeks?

**The answer:** a differentiable, content-addressed lookup table. Every token emits a query; every token advertises a key and holds a value. Relevance is a dot product (week 1), scaled by a variance correction (week 4), turned into weights by softmax (week 4), and used to take a weighted average of values (week 2). Nothing in it is new. It's a *composition* of things you've now built.

## The equations, fully annotated

```
Q = X W_q     K = X W_k     V = X W_v          # wk 2: learned projections
S = Q Kᵀ                                        # wk 1: pairwise similarity
S = S / √d_k                                    # wk 4: variance correction
S = S + M                                       # causal mask: -inf above diagonal
A = softmax(S)                                  # wk 4: rows become distributions
O = A V                                         # wk 2: weighted sum of values
O = O W_o                                       # wk 2: project back to model dim
```

**The mask, and why `-inf`.** Setting masked positions to `-inf` makes `exp(-inf) = 0` exactly, so future tokens get *precisely* zero weight — not "very small," zero. This is what makes teacher forcing valid: every position can be trained in parallel while remaining honest about what it was allowed to see. And it's the reason prefill can process the whole prompt in one pass while decode cannot go faster than one token at a time.

**Multi-head, and why it isn't just "more attention."** Split `d_model` into `h` heads of size `d_model/h`, attend independently, concatenate. Each head gets a *lower-rank* projection (week 2) and can therefore specialize — one tracking syntax, another coreference, another position. The parameter count is identical to single-head; what changes is that you get `h` separate low-rank similarity structures instead of one full-rank one. That's the real argument for it.

**Where the FFN fits.** `FFN(x) = W₂ · act(W₁x)`, usually expanding 4x. Attention *moves information between* tokens; the FFN *processes* each token independently. Two genuinely different operations, and the FFN holds most of the parameters — which is exactly why MoE replaces the FFN and not attention. The K3 spec you were reading makes this explicit: 896 experts, each a small GLU MLP, and attention left alone.

## The build

```
Day 1: Single-head attention, forward only, NumPy. Verify against
       torch.nn.functional.scaled_dot_product_attention.
       Visualize the attention matrix as a heatmap on a real sentence.

Day 2: Causal mask. Prove to yourself position i cannot see i+1 --
       change a future token and assert earlier outputs are bit-identical.
       This test is the whole justification for parallel training.

Day 3: Multi-head. Get the reshape/transpose right:
       (B,T,D) -> (B,T,H,d) -> (B,H,T,d) -> attend -> back.
       This is where your shape assertions earn their keep.

Day 4: Attention BACKWARD by hand. No autograd. Grad-check every input.
       This is the capstone -- it requires week 3's matmul gradients,
       the softmax Jacobian, and careful transposes.

Day 5: Assemble one full block:
         x = x + attn(rmsnorm(x))
         x = x + ffn(rmsnorm(x))
       Stack 4. Add embeddings + positional encoding + output head.
       Train on tiny Shakespeare. Watch the loss fall from ln(vocab).

Buffer: sampling loop -- reuse your week 4 top-k/top-p code. Generate text.
```

When that generates recognizable English, you're done. You built every piece from the math up.

---

## Positional encoding (the one thing week 8 doesn't cover)

Attention is **permutation-equivariant** — shuffle the input tokens and the outputs shuffle identically. It has no inherent notion of order. Position must be injected.

Worth a buffer session: sinusoidal encodings (the original — different frequencies so relative offsets are linearly recoverable) and **RoPE**, which is what everything modern uses. RoPE rotates query and key vectors by an angle proportional to position, so that `q_m · k_n` depends only on `m − n`. It's a 2D rotation matrix applied to coordinate pairs — pure week 1 and week 2 material, and a satisfying payoff for the geometry work.

---

## What comes after

You'll be ready for these in a way you wouldn't have been before:

- **"Attention Is All You Need"** — read it after week 8, not before. It'll be a recap.
- **Karpathy's "Let's build GPT"** — as verification of your own build.
- **The Illustrated Transformer** (Alammar) — for the visual mapping.
- **3Blue1Brown's neural network and transformer series** — best intuition-building video work available, good for the buffer days.
- **Your K3 spec sheet** — reread it. `7168 / 96` not dividing evenly, the latent MoE dimension, the KDA/MLA split: all of it should read differently now.

---

## Why the weeks are ordered this way

Four dependencies drive it:

**Vectors before matrices.** A matrix is a collection of dot products. Learning matmul before the dot product means memorizing a procedure instead of understanding an operation.

**Calculus before probability.** Backprop is the harder concept and everything depends on it. Getting `∂L/∂logits = p − y` in week 3 means week 4's softmax discussion lands on prepared ground.

**Probability before information theory.** Cross-entropy is an expectation over a distribution. You need the distribution first.

**Numerics last, but before assembly.** Week 7's material looks like implementation detail until you realize normalization, initialization, and `√d_k` are the *same variance-control idea* in three costumes — which only becomes visible after you've met all three.

---

## One meta-note

Thirty minutes is enough for exactly one of: reading a concept, or writing code. Not both. Alternate — read on odd days, build on even ones. Trying to do both in one session produces half-understood concepts and half-working code.

And keep `nanograd.py` in git with a commit per session. The diff history is the record of what you actually learned, and around week 6 you'll want to look back at week 3's code and see how much clearer it could be. Rewrite it then. That rewrite is a better signal of understanding than any of the exercises.
