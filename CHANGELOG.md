# Changelog

## 0.2.1

- Search matches unchanged sources and missing sources named in diagnostics.
- Expanded queries and stage selections survive search and filtering.
- Stage chips select the corresponding recorded output.
- Source highlighting uses the configured top-k cutoff; later context is labeled.
- Unlabeled reports fit narrow viewports and show a readable no-labels status.
- Hosted reports include overview and companion-report navigation.
- Public-demo builds render current templates from recorded snapshots and reject
  measurements that do not match those snapshots.
- Recorded configurations are isolated from later caller mutations.
- Invalid policies and oversized JSON integers produce clean validation errors.
- Report output aliases cannot overwrite snapshots through hard links.
- Added browser and unit regression checks for these behaviors.
