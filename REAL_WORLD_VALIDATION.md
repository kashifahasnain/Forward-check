# Manual validation set (synthetic)

Every message, person, organization, program, record, and event below is
**synthetic test data**. None is presented as real evidence, verified news, or
a claim about a real person or event. Use these cases for manual review of
extraction and report behavior; do not score accuracy from the wording alone.

| Case | Synthetic input text | Expected extraction | Expected with no evidence | Evidence needed for a reliable verdict | Common failure modes |
|---|---|---|---|---|---|
| Fake-quote allegation | `A viral post says Minister Mira Sen said, "Every student receives 20000 credits by Friday." Forward now.` | Preserve the attribution as a checkable statement that Mira Sen said the quoted words. Do not treat the quoted benefit as proof that it exists. | **Unverified**; inability to find a transcript is not disproof. | Original recording/transcript or an authenticated statement from the speaker's office, plus independent corroboration where available. | Verifying quote content but not attribution; stripping the speaker's name; treating no search results as a contradiction. |
| Government-scheme eligibility | `Every student is eligible for the fictional Udaan Scholarship.` | Preserve the universal eligibility claim and the program name. | **Unverified** without the official rules. | Current official scheme guidelines identifying eligible years, income/region limits, dates, and exceptions. | Missing “every”; treating one narrower rule as proof about all eligibility conditions; confusing similar program names. |
| Historical date | `The fictional Rivergate Accord was signed in 1898.` | Preserve the named event and exact date. | **Unverified**. | A relevant primary record or authoritative archive, with the event identity and date directly visible. | Losing the date; confusing agreement date with signing/ratification date; treating a single textual mismatch as a complete False verdict. |
| Biology/science | `The fictional blue moss produces oxygen only at night.` | Preserve organism and the “only at night” limitation. | **Unverified**. | Relevant peer-reviewed studies, methods, controls, and independent replication; identify the organism precisely. | Dropping “only”; substituting a similar species; mistaking a search snippet or lab observation for consensus. |
| Health/nutrition | `A fictional herb cures every respiratory infection.` | Preserve the broad “cures every” scope and distinguish it from a narrower symptom claim. | **Unverified**; no evidence is not evidence of ineffectiveness or effectiveness. | High-quality clinical evidence for the specific preparation and outcome, systematic reviews, safety information, and relevant health-authority guidance. | Turning “may help” into “cures”; missing safety/dose/population limits; treating related research as proof of this claim. |
| Financial claim | `This fictional fund guarantees 4 percent returns every month with no risk.` | Keep the rate, period, guarantee, and no-risk assertion distinct. | **Unverified** and a reason to verify independently, not a financial-risk verdict. | Regulator records, audited filings, contract terms, and independently verified performance/risk disclosures. | Dropping the monthly period; treating promotional material as evidence; equating caution score with fraud probability. |
| Hindi/Hinglish viral benefit | `तुरंत रजिस्टर करें! सरकार हर छात्र को मुफ्त लैपटॉप दे रही है। आज रात 8 बजे तक फॉर्म भरें और संदेश 10 लोगों को भेजें।` | Preserve urgency, government attribution, universal student eligibility, laptop benefit, 8 PM deadline, and forwarding instruction. | **Unverified**; urgency does not prove a false claim. | Current official notice with issuing body, scope, eligibility, deadline, and the original application destination. | Losing `हर`/“every” or negation; misreading transliteration; dropping the time/amount; treating urgency as evidence. |
| Misleading-context example | `Every fictional district resident receives the travel grant.` | Extract the universal grant claim. | **Unverified** until qualifying evidence is available. | Official grant rules showing whether residency, age, income, or application conditions materially narrow the claim. | Missing an eligibility qualifier; treating unrelated eligibility text as relevant; over-triggering on “some” without establishing material scope. |
| Unverified claim | `The fictional Northbridge school will close next Tuesday.` | Preserve the school name, action, and relative date; resolve “next Tuesday” only with the message date. | **Unverified** if no dated school notice is supplied. | A current notice from the school/district and the date/time context of the forwarded message. | Inventing an absolute date; confusing similarly named schools; interpreting absent search results as disproof. |
| Pure opinion | `The fictional Bluebird transit plan is the worst idea ever.` | Classify the evaluative statement as an opinion, not a factual verdict. | **Not a Factual Claim**. | No factual evidence is needed for the opinion; separately check any factual assertions attached to it. | Treating emotional wording as proof; overlooking a factual clause after “because”; labeling criticism as misinformation. |

## Review checklist

- Confirm the extracted wording preserves names, dates, amounts, scope words,
  negations, and attribution.
- Confirm each claim's evidence is about that exact claim, not only the topic.
- Confirm unavailable, irrelevant, conflicting, or failed retrieval remains
  **Unverified**, not **False**.
- Confirm caution signals and risk scores do not change a factual verdict.
- Review English, Hindi, and Hinglish reports and inspect what the copy/share
  report contains before sharing.
- Record any language or evidence-association errors; deterministic rules do
  not establish reliable Hindi/Hinglish comprehension.

Automated offline fixtures use mocked providers and synthetic pages. Live
Brave/Ollama validation and human assessment of real source quality remain
outstanding unless performed separately.

## Phase 7 controlled validation

### What was reviewed

The ten-case table above is entirely synthetic. Those fixtures were created to
exercise pipeline branches and are not real-world evidence. Before this phase,
no case in that table had been manually reviewed against a real primary source.

This phase separately ran ten harmless inputs through `analyze_message` with
source search explicitly disabled. `OLLAMA_URL` was the local
`http://localhost:11434/api/generate`; `/api/tags` responded and listed two
models, including the configured `gemma3:4b`. All ten model generation calls
timed out at the configured 12-second read timeout. The pipeline therefore
used deterministic local fallback extraction for all ten. No claim in this run
was sent to Brave, and no live source search, app-managed page retrieval, or
live claim verdict was tested.

These Phase 7 inputs are controlled test wording, not collected viral posts or
claims established as true. A few use real public institutions or topics; only
the explicitly described source comparisons below were checked against actual
public pages.

Status distinguishes what was observed: **PASS** means only the named
extraction or offline check met its stated expectation; **FAIL** means an
observed mismatch; **NOT TESTED** means no real provider/retrieval evidence was
available. An `Unverified` result with search disabled is not a successful
fact-check.

### Controlled input observations

1. **P7-01 — Quote attributed to a public figure (synthetic input)**
   - **Input:** `A viral post says Minister Mira Sen said every student receives 20000 credits by Friday. Forward now.`
   - **Topic / expected extraction:** Quote attribution; retain Mira Sen as the
     alleged speaker and distinguish the attribution from the quoted benefit.
   - **Evidence needed / unavailable behavior:** An original recording,
     transcript, or authenticated statement. With none, remain **Unverified**.
   - **Actual result:** Ollama timed out. Fallback returned the entire text as
     one `factual_assertion`; it did not identify an `attributed_quote` or a
     speaker. Search status was `not_enabled`; verdict was `unverified`.
   - **Pipeline evaluation:** Extraction **FAIL** (attribution not separated);
     source relevance, retrieval, evidence assessment, and report display
     **NOT TESTED**. An `Unverified` result here is only the no-search default.
   - **Mismatch:** The extracted type cannot distinguish whether the public
     figure made the statement from whether the benefit itself exists.

2. **P7-02 — Federal Pell Grant eligibility (real claim wording)**
   - **Input:** `Every U.S. college student is eligible for a Federal Pell Grant.`
   - **Topic / expected extraction:** Government/student-aid eligibility;
     preserve `Every`, `U.S.`, and `Federal Pell Grant`.
   - **Evidence needed / unavailable behavior:** Current official Federal
     Student Aid eligibility rules. With evidence unavailable, remain
     **Unverified**.
   - **Actual result:** Ollama timed out. Fallback returned
     `college student is eligible for a Federal Pell Grant.` It dropped the
     universal quantifier and `U.S.`. Search was disabled; verdict was
     `unverified`. The Federal Student Aid page timed out when manually fetched,
     so its eligibility rules were not reviewed.
   - **Pipeline evaluation:** Extraction **FAIL** (scope loss); source
     relevance, retrieval, evidence assessment, and report display
     **NOT TESTED**.
   - **Mismatch:** Dropping `Every` changes a universal eligibility claim into
     a weaker proposition.

3. **P7-03 — U.S. Constitution date (real claim)**
   - **Input:** `The U.S. Constitution was signed on September 17, 1787.`
   - **Topic / expected extraction:** Historical event/date; retain the
     Constitution's name and date.
   - **Evidence needed / unavailable behavior:** A primary transcription or
     archival record. Without usable evidence, remain **Unverified**.
   - **Actual result:** Ollama timed out. Fallback returned
     `Constitution was signed on September 17, 1787.` It preserved the date but
     dropped `U.S.`. Search was disabled; the pipeline verdict was
     `unverified`.
   - **Manual source comparison:** The National Archives transcript below
     includes the date written out in words and a subscription/signature
     section. When the relevant manually copied excerpt was passed to the
     deterministic evidence assessor before the follow-up date change, it
     returned `Does Not Address`. Date normalization now recognizes the
     written-out year, but a regression still expects `Does Not Address` for
     that excerpt: it does not explicitly identify the Constitution or say it
     was signed, so matching a date alone would overstate relevance.
   - **Pipeline evaluation:** Extraction **FAIL** (entity qualifier loss);
     manual source comparison **PASS** for the date; automatic source
     association **FAIL** for this passage; app retrieval and report display
     **NOT TESTED**.

4. **P7-04 — Photosynthesis (real claim wording)**
   - **Input:** `Plants produce oxygen during photosynthesis.`
   - **Topic / expected extraction:** Biology/science; retain plants, oxygen,
     and photosynthesis without strengthening the claim.
   - **Evidence needed / unavailable behavior:** Relevant scientific or
     educational primary material explaining the process. Without it, remain
     **Unverified**.
   - **Actual result:** Ollama timed out. Fallback preserved the input as a
     factual assertion. Search was disabled; verdict was `unverified`. No
     source was manually reviewed for this case.
   - **Pipeline evaluation:** Extraction **PASS** for wording only; source
     relevance, retrieval, evidence assessment, verdict accuracy, and report
     display **NOT TESTED**.

5. **P7-05 — Antibiotics and viral infections (real claim)**
   - **Input:** `Antibiotics treat viral infections such as flu.`
   - **Topic / expected extraction:** Health; preserve the positive assertion
     and the flu example.
   - **Evidence needed / unavailable behavior:** Authoritative clinical
     guidance. If no evidence is available, remain **Unverified**.
   - **Actual result:** Ollama timed out; fallback preserved the sentence.
     Search was disabled, so the app pipeline returned `unverified`.
   - **Source/retrieval result:** The public CDC URL was fetched directly using
     `SafeSourceRetriever` (outside Brave discovery). It returned the page title
     “Healthy Habits: Antibiotic Do's and Don'ts,” publication date
     `2025-09-23`, and complete text (`partial_content=false`).
   - **Actual mismatch found and fix:** Before the fix, the assessor selected
     the nearby sentence “Antibiotics ONLY treat certain infections caused by
     bacteria, such as:” for both claim polarities. It classified the positive
     claim as `Contextualizes` and the negative claim as `Contradicts`, despite
     the retrieved page explicitly saying “Antibiotics do not treat infections
     caused by viruses such as those that cause:” and listing “Flu.” The
     matcher now normalizes `viral` and `viruses` to a shared token, so the
     specific passage wins. A post-fix direct retrieval returned
     `Contradicts` for the positive claim and `Supports` for the negative one,
     with the explicit virus passage selected for both. In either direction,
     the claim-level result remains `unverified` with one source.
   - **Pipeline evaluation:** Extraction **PASS**; direct constrained
     retrieval and passage selection **PASS** after the fix; one-source
     conservative verdict **PASS** in the regression. Brave discovery and
     report display for this actual page **NOT TESTED**.

6. **P7-06 — Guaranteed monthly returns (synthetic offer)**
   - **Input:** `This fictional fund guarantees 4 percent returns every month with no risk.`
   - **Topic / expected extraction:** Finance; retain the guarantee, amount,
     period, and no-risk assertion.
   - **Evidence needed / unavailable behavior:** Applicable regulator records,
     audited documents, contract terms, and independent performance/risk
     information. Without these, remain **Unverified**; caution is not proof.
   - **Actual result:** Ollama timed out. Fallback preserved the full wording.
     Search was disabled; verdict was `unverified`. No real issuer or evidence
     was involved.
   - **Pipeline evaluation:** Synthetic extraction **PASS**; source relevance,
     retrieval, evidence assessment, and report display **NOT TESTED**.

7. **P7-07 — Hindi viral benefit message (synthetic)**
   - **Input:** `तुरंत रजिस्टर करें! सरकार हर छात्र को मुफ्त लैपटॉप दे रही है। आज रात 8 बजे तक फॉर्म भरें और संदेश 10 लोगों को भेजें।`
   - **Topic / expected extraction:** Hindi government-benefit viral message;
     preserve urgency, `सरकार`, `हर`, benefit, 8 PM deadline, and forwarding
     request as distinguishable information.
   - **Evidence needed / unavailable behavior:** A current official notice
     identifying the issuing body, scope, eligibility, deadline, and
     application destination. Without it, remain **Unverified**.
   - **Actual result:** Ollama timed out. Fallback extracted **no claims**.
     Search was not run; there was no claim-level verdict.
   - **Pipeline evaluation:** Extraction **FAIL**; evidence association,
     retrieval, verdict, and claim report display **NOT TESTED**.
   - **Mismatch:** Urgency and sharing language appear to prevent extraction of
     the central benefit claim; the app did not silently replace the missing
     claim with a corrected one.

8. **P7-08 — Hinglish scholarship message (synthetic)**
   - **Input:** `Har student ko ₹10,000 scholarship milegi. Kal 8 baje tak form bharo aur 10 logon ko forward karo.`
   - **Topic / expected extraction:** Hinglish government-benefit message;
     preserve universal eligibility, ₹10,000, deadline, and forwarding request.
   - **Evidence needed / unavailable behavior:** An official scheme notice
     with eligibility, amount, dates, and application steps. Without it,
     remain **Unverified**.
   - **Actual result:** Ollama timed out. Fallback returned only
     `Message mein scholarship ka zikr hai.` It lost `Har`, the amount, deadline,
     and instruction. Search was disabled; this generic claim was unverified.
   - **Pipeline evaluation:** Extraction **FAIL**; evidence association,
     retrieval, verdict accuracy, and report display **NOT TESTED**.

9. **P7-09 — Opinion plus factual assertion (real health wording)**
   - **Input:** `I think the antibiotic rule is confusing because antibiotics do not work on viruses.`
   - **Topic / expected extraction:** Opinion plus separately checkable health
     assertion; preserve the subjective opinion and extract the “do not work
     on viruses” clause independently.
   - **Evidence needed / unavailable behavior:** The factual clause needs
     clinical guidance such as the CDC source below; absent evidence, keep
     that factual clause **Unverified** while retaining the opinion as opinion.
   - **Actual result:** Ollama timed out. Fallback returned the complete
     sentence as one `factual_assertion`, not an opinion plus a separate
     assertion. Search was disabled; verdict was `unverified`.
   - **Pipeline evaluation:** Extraction **FAIL** (type and clause separation);
     evidence association, retrieval, verdict, and report display
     **NOT TESTED** for the actual input.

10. **P7-10 — Conflicting date claim (synthetic)**
    - **Input:** `The fictional Rivergate Accord was signed in both 1898 and 1899.`
    - **Topic / expected extraction:** Historical/date conflict; retain both
      years and do not resolve the conflict by guessing.
    - **Evidence needed / unavailable behavior:** Relevant primary records for
      the event and the meaning of “signed.” With no records, remain
      **Unverified**.
    - **Actual result:** Ollama timed out. Fallback preserved the complete
      sentence and both dates. Search was disabled; verdict was `unverified`.
      No conflicting sources were supplied.
    - **Pipeline evaluation:** Extraction **PASS** for retaining both dates;
      conflicting-source association, retrieval, evidence assessment, and
      report display **NOT TESTED**.

### Manually inspected source references

These pages were manually inspected and also passed directly to the
constrained `SafeSourceRetriever` using their known public URLs. That direct
retrieval check bypassed Brave discovery; it does not establish that Brave
would return either page.

1. **The Constitution of the United States: A Transcription** — publisher:
   U.S. National Archives; `SafeSourceRetriever` read publication-date metadata
   `2015-11-04` (not independently confirmed from the visible transcription
   body).
   [Source](https://www.archives.gov/founding-docs/constitution-transcript)
   - **Exact passage:** “done in Convention by the Unanimous Consent of the
     States present the Seventeenth Day of September in the Year of our Lord
     one thousand seven hundred and Eighty seven and of the Independance of
     the United States of America the Twelfth In witness whereof We have
     hereunto subscribed our Names,”
   - **Relation:** The official transcript records the convention date in
     words and is followed by the subscription/signature section. It supports
     the date claim in the historical document context.
   - **Retrieved-page observation:** The constrained retriever returned
     `retrieval_status=retrieved` but `partial_content=true`; its 15,000
     character limit cut off before the relevant end-of-document date. A
     complete text copy was separately inspected through the public Archives
     page fetch. The new offline regression supplies the exact excerpt and
     still returns `Does Not Address` because the excerpt lacks explicit claim
     event wording; the date is not promoted into evidence by itself.
   - **Missing context / limit:** The transcription is not an independent
     examination of the physical parchment or a complete study of
     ratification. Date normalization is limited and does not resolve event
     identity or verify a historical claim by itself.

2. **Healthy Habits: Antibiotic Do's and Don'ts** — publisher: U.S. Centers
   for Disease Control and Prevention; page date: September 23, 2025.
   [Source](https://www.cdc.gov/antibiotic-use/about/index.html)
   - **Exact passage:** “Antibiotics do not treat infections caused by viruses
     such as those that cause:” followed by a list that includes “Flu.”
   - **Retrieved-page observation:** `SafeSourceRetriever` returned
     `retrieval_status=retrieved`, `partial_content=false`, and the date
     `2025-09-23`. After the fix, the local assessor selected the explicit
     virus passage and labeled the positive/negative wording appropriately.
   - **Relation:** Directly contradicts the test claim “Antibiotics treat viral
     infections such as flu.”
   - **Missing context / limit:** The page discusses antibiotics and viral
     infections; it is not individualized medical advice and does not address
     every respiratory illness or treatment.

The following source attempts did not produce inspectable evidence and were
not used to assess claims: the Federal Student Aid Pell page timed out, and
Investor.gov/SEC, the FTC investment page, and some other attempted pages
returned access errors or timeouts. No source title, quotation, date, or
conclusion is inferred from those failures.

### Provider and search-limit observations

- **Brave Search:** `BRAVE_SEARCH_API_KEY` was absent from the process
  environment, and no `.env` file was present in the workspace root. No live
  Brave request was made. Live discovery and live provider response quality
  are **NOT TESTED**.
- **Direct page retrieval:** The CDC page and National Archives transcript
  were each requested through `SafeSourceRetriever` using their known public
  URLs, without search queries or credentials. CDC retrieval was complete; the
  Archives page was marked partial and omitted its relevant date from the
  returned text. This manually selected-URL test is not a full
  search-to-report run.
- **Ollama:** The local API responded to `/api/tags` and listed two models;
  the configured `gemma3:4b` generation timed out on all 10 controlled inputs
  at the configured 12-second read timeout. Fallback was used 10/10 times.
  Ollama generation is therefore available as a local service but too slow
  for these observed requests; response quality was **NOT TESTED**.
- **Search cap:** The offline regression
  `test_search_request_cap_leaves_later_claims_unverified` passed. A synthetic
  provider received exactly 9 requests from 11 searchable claims; the final
  two were marked `not_searched_limit` and remained `unverified`. The UI has
  localized text for this status. This verifies the mocked cap, not live API
  behavior.
- **Report display:** A prior local browser check used a mocked analysis
  response and verified Hindi/Hinglish switching, preserved input, localized
  share text, and report copying. It did not render the ten current Ollama
  outputs or prove live evidence is displayed correctly.

### Regression commands and outcome

Files changed by this follow-up:

- `modules/source_retriever.py` — date normalization and Devanagari token/digit
  handling, while retaining the existing viral/viruses fix.
- `modules/verdict_engine.py` — do not equate different hostnames with
  independent corroboration.
- `modules/claim_extractor.py` — preserve original Hinglish/Hindi negated
  assistance wording and expose extraction method metadata.
- `static/script.js` — identify extraction-only/fallback behavior in claims and
  no-claim reports in all three report languages.
- `test_source_retrieval.py`, `test_verdict_engine.py`,
  `test_source_search.py`, and `test_language_support.py` — focused regressions.
- `README.md` and `REAL_WORLD_VALIDATION.md` — update behavior, limits, and
  observed outcomes.

Offline test command:

```powershell
.\.venv\Scripts\python.exe -m unittest -q test_source_retrieval test_source_search test_verdict_engine test_analysis_pipeline test_language_support test_text_route test_risk_assessor test_phase6_audit
```

**174 passed, 0 failed.** These offline regressions use fixtures/mocks; the
count does not include the ten earlier Ollama probes or earlier direct
public-page retrievals. The follow-up test cases cover spelled-out and numeric
date matching, date conflicts and incompleteness, event association, Hindi
digits, source-independence limits, and paired Hindi/Hinglish negation through
fallback extraction and search-query generation.

Compilation command:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py modules test_source_retrieval.py test_source_search.py test_verdict_engine.py test_analysis_pipeline.py test_language_support.py test_text_route.py test_risk_assessor.py test_phase6_audit.py
```

Compilation completed successfully.

The suite includes retrieval restrictions, malformed/empty provider responses,
timeouts/rate limits, duplicate caching, verdict conservatism, URL handling,
language fallback, and synthetic scenario/search-cap tests. No live Brave,
Ollama, or public-page request was made for this follow-up. It does not
establish real-world source quality or fact-checking accuracy.
Pylance syntax/diagnostic requests timed out. Python compilation passed, but
static analysis did not complete. JavaScript syntax could not be checked
because Node.js was not installed; the local Flask page was unavailable during
the attempted browser check, so the new extraction-method notice was not
visually validated.

### Highest-priority remaining problems

1. **High — Hindi/Hinglish extraction and claim scope:** the earlier ten-input
   run still found a Hindi benefit message with no claim, lost Hinglish
   eligibility/amount/deadline details, omitted quote attribution, and dropped
   “Every U.S.” from the Pell wording. The negative Hinglish assistance case
   now has paired offline regression coverage, but broad multilingual
   reliability remains unestablished.
2. **High — provider latency:** all ten earlier local Ollama calls hit the
   configured 12-second read timeout. The fallback now reports its extraction
   method, but model warm-up, hardware, and runtime causes were not benchmarked.
3. **High — source independence and overall verdict scope:** no source schema
   establishes independence or component coverage. Multiple supports now stay
   **Unverified**; no automatic Supported by Evidence, Mostly True, Mostly
   False, or False conclusion is justified by current data.
4. **Medium — date/event association:** numeric and selected English spelled
   dates now compare, including numeric Hindi date digits, but the historical
   transcription excerpt still lacks enough event wording to associate it
   automatically with the extracted claim. Date mismatch alone is not proof.
5. **Medium — no live source discovery:** Brave configuration was absent.
   A separately authorized, small, privacy-safe run is needed to validate
   provider operation, source relevance, app retrieval, and displayed passages.

### Follow-up matching, verdict, and fallback changes

After the Phase 7 report above was written, a deterministic offline repro
confirmed that the lexical assessor treated a numeric year mismatch as
`Supports` when the day number happened to overlap, and did not normalize
spellings such as “one thousand seven hundred eighty-seven.” The relevant
passage must also share claim-specific event wording; a date match alone is
not enough. Added handling covers numeric years with date context, selected
English number-word years, month/day forms, common Hindi month names, and
Hindi digits. Ambiguous/multiple date components do not create an automatic
date contradiction, and a passage containing only part of a full date is
contextual rather than supporting. Hindi number words and unrestricted date
parsing remain unsupported.

The existing verdict engine previously promoted support from multiple distinct
hostnames while acknowledging that it did not test source independence.
Different hostnames are not proof of independent publishers, so this promotion
has been removed; support passages remain visible but the claim verdict stays
**Unverified** until independence can be established. No new verdict category
was added.

A paired fallback test also exposed that a Hinglish financial-assistance
sentence with `nahi` could disappear. The local rule now preserves the exact
negated sentence as evidence. Fallback/model use is included in extraction
metadata and shown in claim cards and the no-claims report; Ollama is described
as an extraction aid only.
These follow-up checks used local deterministic tests only. No live Brave,
Ollama, or public-page request was made for this follow-up.

Live Brave search, source discovery, an unmocked full search-to-report run,
real source relevance for the other eight cases, and overall real-world
end-to-end verdict accuracy remain outstanding. Direct constrained retrieval
was tested only for the two manually selected official pages.
Do not treat the manual page review or mocked/offline results as proof of
production readiness.
