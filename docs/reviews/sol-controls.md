# GPT-6.1 Sol control critique

Read-only baseline b5d21c556e288c1bb6216cfacf8defda1e98a345. Independent reviewer reproduced four issues in synthetic temporary state with deterministic providers; real PDFium/Tesseract extraction for document cases. No live writes/private-state reads or checkout edits.

1. During SDK semantic processing, a new literal tool rule can forbid propose_payment, yet the in-flight proposal remains allow and is bound to the new feed. Fresh tool call blocks, original proposal still releases. Missing across-await feed authority check (`payments.py` baseline lines605–612 and431).
2. Real hybrid PDF with visible assistant bypass prose and benign nonempty machine text passes evidence; the chosen `machine_text or visible_text` omits the prose (`payments.py` lines517/610, API evidence endpoint). This is an inspection blind spot, not proof of arbitrary money movement.
3. Optional compatible-provider valid JSON with absent usage records zero tokens/cost and completed reservation under nonzero configured rates (`gateway.py`127–128).
4. Genuine two-page PDF processed under five-page policy still passes evidence after tightening max_pages to one (`payments.py`108/active evidence checks); fresh approval can bind the tightened policy.

Suggested follow-ups: complete worker evidence schema validation; provider overrun through full model boundary; explicit tested last-good policy fallback. These were hardening suggestions, not reproduced exploits.
