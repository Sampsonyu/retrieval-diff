# First-user launch kit

Status: **prepared, not posted**. No invitations, platform posts, or user trials
have been sent or fabricated. The public demo is live:

- [Interactive demo](https://retrieval-diff-demo.sampsonyu.chatgpt.site)
- [Source repository](https://github.com/Sampsonyu/retrieval-diff)
- [Public-document case](../case-study.md)
- [LinkedIn draft](linkedin-post.md)
- [RAG community draft](community-post.md)
- [Technical article draft](article.md)
- [Individual trial invitation](trial-invitation.md)
- [Trial feedback form](https://github.com/Sampsonyu/retrieval-diff/issues/new?template=trial-feedback.yml)
- [Feedback tracker](feedback-tracker.csv)

## First two weeks: proposed sequence

| Phase | Action | Evidence to collect |
| --- | --- | --- |
| Days 1–3 | Share the demo with up to five relevant engineers who are open to testing retrieval tools | Whether they opened a report, could export their own stages, and found an actual issue |
| Days 4–7 | Fix the largest observed integration obstacle; publish one technical walkthrough on a suitable English channel | Concrete replies and opt-in trial feedback, not assumed views |
| Days 8–14 | Publish the RAG-focused explanation where community rules allow; follow up with willing trial users | A second run, a useful bug report, or a reason the tool was not useful |

Targets, not forecasts: five independent trials, two substantive feedback reports,
one returning user. A successful integration report includes the stack, a setup
obstacle, a finding, and whether the user would run it again. Anonymous report
visits alone do not count as verified trials. GitHub stars/forks are observed
separately and never substituted for usage evidence.

## Channel selection

1. Start with a small relevant professional audience and individual willing users.
   Explain the exact problem and ask for feedback rather than a star.
2. LinkedIn or a technical article can explain the case with a link to the demo.
3. A RAG community can provide more focused engineering feedback. Confirm its
   current self-promotion rules and disclose project authorship before posting.
   The official r/Rag rules page did not expose its rule contents during research;
   no permission to self-promote there is assumed.
4. Hacker News is deferred. Its [Show HN guidelines](https://news.ycombinator.com/showhn.html)
   require a usable project and personal involvement. Its
   [site guidelines](https://news.ycombinator.com/newsguidelines.html) prohibit
   generated/AI-edited posts and automated posting. The owner must write any HN
   submission themselves; this kit intentionally includes no HN post draft.

## Claims supported today

- A working open-source Python comparator and portable report.
- An executed LangChain/BM25 chain over 12 pinned FastAPI documents and 144 chunks.
- Eight authored questions; two source-level regressions from a deliberately
  narrowed path filter; zero after restoring scope.
- An independently reproducible, controlled example with licensed source files.

Not supported: external customers, production incidents, proven time savings,
accuracy improvements in general, product-market fit, or production-scale use.

All public-facing material is English. The drafts are reviewable writing assets,
not evidence of outreach. Only send messages or publish platform posts when the
user has requested the specific external action and the account/channel is known.
