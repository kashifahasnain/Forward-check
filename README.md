# Forward Check

Forward Check extracts claims from pasted text or OCR text, identifies warning
signals, and can search for source leads. With explicit opt-in, it can retrieve
eligible search-result pages and assess text for evidence related to a claim.
These assessments describe retrieved source text only; they are not final fact
checks. The report uses a small set of deterministic labels; most claims remain
**Unverified**, and no label is a complete fact-check.

## Run on Windows

Open the project folder in VS Code and use its integrated PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open the local address printed by Flask. Ollama is optional: when available, it
assists with extraction, and local rules supplement its claims. If Ollama is
unavailable, returns malformed or incomplete output, or does not respond within
the configured 3-second connection / 12-second read timeout, local extraction
is used. The Requests timeout is not a guaranteed wall-clock deadline. Each
claim identifies whether local rules or Ollama-assisted extraction produced it;
Ollama only assists extraction and does not verify claims.
The Flask development server runs with debug mode off by default. To enable the
interactive debugger for local development only, set `$env:FLASK_DEBUG = "1"`
before starting it; never enable this debugger on a network-facing deployment.
The built-in Flask server is for local development, not production hosting.

## Enable source search

Source search prefers the Tavily Search API and can fall back to Brave Search
from the Flask backend. Check each provider's current pricing, query limits,
and terms before use. Do not put either key in JavaScript, HTML, or a committed
file.

The search checkbox is **off by default**. When checked, claim wording,
grounded entities, and available speaker/context details for attributed
statements are used to form claim-specific queries sent to Tavily (or Brave
when Tavily is unavailable). Do not opt in for messages containing private or
sensitive information. Submitted links are not sent as URLs for fetching and
are never opened automatically.

Set Tavily's key, and optionally Brave's fallback key, in the same PowerShell
terminal used to start Flask:

```powershell
$env:TAVILY_API_KEY = "paste-your-tavily-key-here"
# Optional fallback:
$env:BRAVE_SEARCH_API_KEY = "paste-your-brave-key-here"
.\.venv\Scripts\python.exe app.py
```

Keys are only sent from Flask to their fixed HTTPS provider endpoints. Tavily
is used first; Brave is tried if Tavily is not configured or a Tavily request
fails. If the checkbox is off, no search request is made even when keys are
configured. If neither key is configured, source discovery is reported as
unavailable. The report states the provider, attempted queries, results,
retrieved pages, and provider errors; claims remain unverified when source
pages do not provide sufficient evidence. Provider requests, including
fallbacks, are capped at nine per analysis; this may leave fewer than nine
distinct claims searched when fallback is needed.
Each provider query returns up to three leads.

When enabled, search runs a claim-specific query for each searchable factual
claim and displays up to three HTTPS result leads per claim. Queries use the
claim wording and available context, entities, alleged speaker, and topic
category; category-specific terms help prioritize relevant primary or
authoritative material without treating any publisher as conclusive. Leads
include the query and provider, and indicate when a publication date was not
supplied. Search-result snippets remain discovery metadata, separate from
retrieved page text and evidence passages.

Forward Check retrieves only HTTP(S) URLs returned by the configured search
provider; URLs submitted in message text are never fetched. Retrieval rejects
non-public destinations, checks resolved IP addresses, pins connections to a
validated address, revalidates redirect targets, and applies redirect, time,
and response-size limits. Only HTML and plain text are accepted. Retrieved
content is treated as untrusted data and is not passed to Ollama. A deterministic
assessment may label a passage Supports, Contradicts, Contextualizes, Does Not
Address, Insufficient Information, or Retrieval Failed. These are evidence
statuses, distinct from claim-level verdicts.

## How claim verdicts are assigned

The verdict engine uses only retrieved-page evidence assessments. Search
snippets, URL appearance, caution signals, and the risk score are never verdict
evidence. The report keeps source links, supporting passages, contradictory
passages, retrieval failures, and limitations visible even when evidence
conflicts.

- **Supported by Evidence**: reserved for multiple complete, directly relevant
  and independently corroborated sources. The current schema cannot establish
  publisher independence, so this verdict is not assigned automatically.
  Different hostnames and non-identical passages are not proof of independent
  corroboration and may include syndicated or copied reporting.
- **Mostly True**: reserved for claims whose separately assessed material
  components are mostly supported and whose qualifications are covered. The
  current extraction/evidence schema does not record component coverage, so the
  app does not assign this verdict.
- **Misleading or Missing Context**: a retrieved contextual passage explicitly
  narrows a claim containing universal language (such as “every” or “all”) with
  an eligibility or scope restriction (such as “only” or “some”). Other
  contextual evidence remains Unverified unless material impact is explicit.
- **Mostly False**: reserved for claims with separately assessed components
  where strong, directly relevant evidence contradicts most material parts.
  The current schema does not establish source quality, independence, or
  component coverage, so this verdict is not assigned.
- **False**: requires strong, directly relevant contradictory evidence with
  adequate coverage of the whole claim. The current schema cannot establish
  source quality or completeness to this standard, so this verdict is not
  assigned automatically.
- **Unverified**: the default for absent, inaccessible, malformed, partial,
  irrelevant, or conflicting evidence; a single support/contradiction; or
  context whose material effect is unclear. Retrieval failure and no search
  results are not evidence against a claim.
- **Not a Factual Claim**: used for clear opinions and instructions. A narrow
  set of explicitly marked causal clauses can be separated into a second
  factual claim while the opinion remains non-factual. Other mixed opinion/fact
  wording may not be separated reliably and can remain unverified and unsearched.

The engine requires evidence assessments to match the exact claim and an actual
retrieved source. It ignores duplicate URLs and identical copied passages when
counting support, but does not reliably recognize syndicated or paraphrased
copies. Verdicts are automated and may be wrong. **Unverified does
not mean false**, search-result snippets are not proof, retrieved text may be
incomplete, sources may disagree, and the caution score is not a truth score.
No verdict guarantees truth or implies deliberate deception.
The lexical passage matcher, scope/qualification rules, and language handling
can miss paraphrases, negation, Hindi/Hinglish nuance, and contradictory
context. Date matching recognizes selected numeric dates, English spelled-out
years, common English/Hindi month names, and Hindi numeric digits, but does not
reliably interpret arbitrary date wording or prove that a date belongs to the
same event. Historical date mismatches do not establish falsity; source quality
and complete claim coverage are not verified.
A future correction should use explicit independent-source and claim-component
evidence before expanding any verdict category.

## Run automated tests

The tests do not require live Ollama or Brave calls:

```powershell
.\.venv\Scripts\python.exe -m unittest test_language_support test_text_route test_risk_assessor test_analysis_pipeline test_source_search test_verdict_engine
```

For the complete offline audit regression set, including source retrieval and
synthetic end-to-end flows:

```powershell
.\.venv\Scripts\python.exe -m unittest test_source_retrieval test_source_search test_verdict_engine test_analysis_pipeline test_language_support test_text_route test_risk_assessor test_phase6_audit
```

`REAL_WORLD_VALIDATION.md` contains a manually reviewable, explicitly synthetic
case set. These are test prompts, not verified claims or evidence about actual
people or events. Live Brave/Ollama validation is outstanding unless separately
configured and reviewed; mocked tests do not establish live source quality.

## Current scope

- Working: text and screenshot/OCR analysis, English/Hindi/Hinglish reports,
  claim extraction with local fallback for common factual sentence forms,
  warning signals, separate caution scoring, URL-format analysis without
  fetching submitted URLs, opt-in Brave source discovery, and constrained
  retrieval, deterministic source assessment, and conservative claim-level
  verdicts. Heuristic extraction and evidence matching may miss relevant
  language or context.
- Requires configuration and explicit per-analysis opt-in: search-result
  discovery through Brave. Claim wording, grounded entities, and available
  speaker/context details are sent.
- Retrieval is limited to discovered source leads and does not crawl linked
  pages, download documents, or fetch user-submitted URLs. Evidence assessment
  is deterministic and lexical; it is not a comprehensive semantic review.
- Not implemented: source-page crawling, robust source-reliability and
  independence analysis, compound-claim component assessment, or automatic
  Mostly True, Mostly False, and False verdicts. Unsupported assertions stay
  **Unverified**.
