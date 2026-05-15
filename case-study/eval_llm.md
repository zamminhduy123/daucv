**Case Study: Making CV Analyzer Output Safer, More Deterministic, and More Useful**

**Problem**
The CV analyzer was producing useful career advice, but the backend had three quality risks:

1. The LLM generated the final `match_score`, making scoring unstable and vibes-based.
2. Suggested rewrites sometimes added unsupported metrics, which could be judged as hallucinations.
3. The eval harness was too binary: if a keyword was not literally in the JD, it treated it as hallucination, even when it was a reasonable inference or adjacent recommendation.

This caused provider failures, noisy eval warnings, and a weaker product experience.

**Upgrade 1: Backend-Owned Scoring**
We split the analyzer schema into two layers:

- `CVAnalysisLLMResponse`: what the LLM returns.
- `CVAnalysisResponse`: what the API returns to the frontend.

The LLM no longer returns `match_score`. It only returns sub-scores and structured analysis.

The backend now computes:

```python
raw_score = (
    0.30 * technical_match
    + 0.20 * experience_relevance
    + 0.15 * keyword_coverage
    + 0.15 * impact_evidence
    + 0.10 * ats_readiness
    + 0.10 * tone_quality
)
```

Then applies deterministic penalties and returns `score_breakdown`.

**Result**
The final score is now explainable, stable, and owned by code instead of the model.

**Upgrade 2: Safe Rewrite Schema**
We replaced the old single rewrite field:

```python
upgraded_text
```

With a safer coaching schema:

```python
improved_safe
improved_with_placeholders
metric_questions
unsupported_assumptions
rewrite_risk
reason
```

This separates the final safe rewrite from metric coaching.

Example:

```json
{
  "improved_safe": "Optimized backend services to improve response time and reliability for user-facing workflows.",
  "improved_with_placeholders": "Optimized backend services, reducing API latency from [X ms] to [Y ms] for [workflow/users].",
  "metric_questions": ["What was the before/after latency?"],
  "unsupported_assumptions": ["Exact latency reduction"],
  "rewrite_risk": "needs_user_input"
}
```

**Result**
The assistant can still teach users to add metrics without inventing facts.

**Upgrade 3: Weighted Missing Requirements**
We changed missing requirement evaluation from simple counts to weighted priority penalties:

```python
priority_weights = {
    "Critical": 12,
    "High": 8,
    "Medium": 4,
    "Low": 2,
}
```

This allows better consistency checks:

- High score despite missing critical JD requirement.
- High score despite large weighted missing penalty.
- High keyword coverage despite many high-priority gaps.

**Result**
The evaluator now distinguishes between a minor missing nice-to-have and a serious missing requirement.

**Upgrade 4: Rich Eval Harness**
The eval harness now returns a structured `EvalResult` instead of only pass/fail warnings.

It tracks:

```python
score_consistency
explicit_jd_keyword_accuracy
semantic_keyword_usefulness
cv_grounding
truthfulness
placeholder_handling
rewrite_safety
actionability
overall
```

And classifies issues into:

```python
hard_hallucinations
soft_inferences
useful_adjacent_recommendations
placeholder_metrics
unsupported_factual_claims
needs_user_confirmation
```

**Result**
The evaluator no longer treats all non-source terms as hallucinations. It allows controlled inference when properly labeled.

**Upgrade 5: More Forgiving Schema Validation**
Provider outputs often failed because lists were too long or too short.

We added pre-validation normalization:

- Trim oversized lists.
- Relax `evidence_analysis` minimum from 3 to 1.
- Add safe fallback content if required lists are empty.
- Keep strict rejection of forbidden fields like model-generated `match_score`.

**Result**
The fallback chain is less brittle. Useful outputs from providers are salvaged instead of rejected for minor shape issues.

**Impact**
The analyzer is now stronger in three ways:

1. **More trustworthy**: fake metrics and unsupported claims are separated from safe rewrites.
2. **More deterministic**: final scoring is computed by backend logic.
3. **More useful**: the system supports adjacent recommendations and metric coaching without mislabeling them as hallucinations.

**Engineering Outcome**
This changed the analyzer from a loosely structured LLM response into a safer AI product pipeline:

```text
LLM analysis
-> schema normalization
-> deterministic scoring
-> rewrite safety classification
-> eval quality scoring
-> API response
```

The product now better balances two goals:

- Avoid hallucinated claims.
- Still coach users toward stronger, quantified CV bullets.