TruthLens-AI-powered-News-Verification-Platform

An AI-styled fake news detection platform, presented as an investigative "verification desk" rather than a bare prediction form. This repo currently contains the frontend demo: a landing page and a full investigation-style analysis UI, running on a client-side mock model.

Tagline: Every article deserves a second read.

What this is

A polished frontend for a fake news / misinformation detector. It includes:

A marketing landing page (hero, stats, feature grid, "how it works" procedure)
A working analysis flow: paste an article → optional source → analyze → staged loading sequence → full case-file report
All the trimmings of a real investigation platform: credibility scoring, bias meters, claim extraction, an AI summary, comparison with verified outlets, community feedback, and a live session dashboard

Important: the "AI" in this demo is a deterministic JavaScript heuristic (analyzeText() in script.js), not a trained machine learning model. It's built to look and behave like a real classifier's output so the UI and UX can be evaluated and demoed end-to-end, but the verdicts are not meaningful predictions. See Connecting a real backend below for how to swap it out.

Files
index.html    markup only — links style.css and script.js
style.css     all styling
script.js     all behavior (ES6) — mock analysis engine, DOM wiring, UI state
README.md     this file

No build step, no package manager, no dependencies to install. The only external resource is a Google Fonts stylesheet link in index.html.

Running it

Just open index.html in a browser — or, for GitHub Pages / any static host, push all three files to the repo root and point the host at index.html. Because script.js is loaded as a normal file (<script src="script.js" defer>), the project also works served from a plain local static server (python3 -m http.server, npx serve, etc.) if you'd rather not open the file directly.

Design direction

Instead of a generic SaaS dashboard look, the UI leans into an "investigative desk / case file" aesthetic:

Palette — ink-navy background, warm gold accent, muted real/fake greens and reds (no neon)
Type — Fraunces (serif, for headlines and the case-file voice) + IBM Plex Sans (body) + IBM Plex Mono (data, labels, monospace "evidence" feel)
Signature motif — a rotated ink-stamp SVG (with an SVG turbulence filter for texture) used decoratively in the hero and dynamically as the REAL/FAKE verdict stamp on results
Light/dark toggle — reframed as "print vs. digital" mode rather than a generic theme switch, since the base theme is already dark
Page structure
Section	Contents
Landing	Hero with the case stamp, stats bar, feature grid, "how it works" procedure
Verification desk	Article textarea, optional source field, upload .txt, analyze/clear actions, staged loading sequence
Case file (results)	Verdict stamp, authenticity score, risk level, sentiment, probability split, flagged keywords, explainable checklist
Investigation extras	Source credibility, bias detection (political / language / emotional tone), AI summary, extracted claims, comparison with verified outlets, community verification (agree/disagree/report)
Desk analytics	Live, session-only dashboard: total analyses, real/fake ratio, average confidence, top flagged keywords
Feature details (frontend, mocked)
Source credibility — normalizes whatever is typed into the Source field and checks it against a small in-file list of known outlets (trusted), suspicious-pattern matches (e.g. numeric spam domains), or falls back to an "unrated" score. Leave it blank and the desk just reports "no source given."
Explainable checklist — instead of a single canned paragraph, the verdict is broken into individual signals (sourcing present, punctuation/caps, article length, presence of figures, emotional language) each marked ✓ or !.
Claim extraction — pulls sentences containing numbers or quotation marks out of the pasted text as "claims worth checking," with a "Needs verification" status chip.
Bias meters — three heuristic meters (political, language, emotional tone) derived from the same signal set as the verdict.
AI summary — a template-based synopsis built from the top detected keywords and overall tone/length, not a real abstractive summary.
Compare with verified reporting — a per-article-varied list of outlets (Reuters, BBC, AP News, etc.) with mock similarity percentages.
Community verification — Agree / Disagree / Report buttons; feedback is only logged in memory for the current session (no backend, no persistence).
Desk analytics — aggregates every analysis run in the current browser session (total count, real/fake ratio, average confidence, most frequent flagged keywords). Resets on page reload; nothing is sent anywhere or stored between visits.
Download report — exports the current case file as a plain .txt file via a client-side Blob download.

None of the above reads from or writes to any external service — everything runs in the browser tab.

Connecting a real backend

The original project brief suggested a Flask + scikit-learn backend with a /api/predict endpoint. To wire this demo up to a real model:

In script.js, replace the body of analyzeText(text, sourceRaw) with a fetch() call to your API, e.g.:
js
   async function analyzeText(text, sourceRaw) {
     const res = await fetch('/api/predict', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ text, source: sourceRaw })
     });
     return await res.json();
   }
Make the analyze click handler async and await the call before proceeding to runResults(...).
Keep the returned object shape consistent with what runResults() expects: isFake, realPct, fakePct, confidence, risk, sentiment, keywords, checklist, claims, summary, bias, similar, source. Any field your real model can't produce yet can be dropped from the UI or left as a placeholder.
For source credibility, claim extraction, bias detection, and "similar articles," you'll eventually want real services behind these (a publisher-reputation database, a proper NLP claim extractor, a bias classifier, and a live news-search API respectively) — the current versions are all local heuristics standing in for that.
The community verification buttons and desk analytics are good candidates for a real backend too, if you want feedback and usage stats to persist across sessions rather than resetting per browser tab.
Known limitations
All "AI" output is a deterministic client-side heuristic — do not use the verdicts, credibility scores, or bias readings as real signal.
No persistence: refreshing the page clears the desk analytics and any in-progress analysis.
No authentication, no admin panel, and no real dataset — those remain open items from the original project brief if you want to build the full platform out further.
