## What and why

<!-- One concern per PR. Link the Workflow ticket or spec. -->

## Checklist

- [ ] Tests added or updated, and `pytest tests/ -m "not slow"` exits 0 with `JUSTDATA_AI_DISABLED=1`
- [ ] pyflakes run on every new or changed Python module
- [ ] If this changes any figure, label or narrative text in a report, the app's cache revision is bumped in `REPORT_REVISIONS` (`justdata/shared/utils/analysis_cache.py`), so cached reports are regenerated instead of served with the old output. An app with no entry there (BranchSight, MergerMeter) needs one added first
- [ ] No secrets, tokens or env files in the diff
- [ ] Monday update posted on the item, in the spec 00 format
