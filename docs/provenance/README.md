# Authorship metadata and validation provenance

At the repository owner's request, the 34 fork-added commits after unchanged upstream
`1870d9e16e16fd6daeac0bd05122e851029ddedc` were reattributed to Justin Vassantachart.
Upstream authors/history, each rewritten commit's exact content tree, parent
ordering and original author/committer dates were preserved. The mapping records
the old and new SHA for every changed commit. This is metadata-only historical
rewriting, not a new execution of earlier tests.

Earlier validation reports retain the commit IDs that actually ran. Use the
matching tree hashes in [author-history-map.json](author-history-map.json) to
relate those reports to the rewritten history. New source/packaging changes
require their own CI run and are not covered merely by that mapping.

The historical `apple-silicon-preview-1` release tag and downloadable bytes are
not retargeted or rewritten. Its BUILD_INFO therefore continues to name the
original source commit, and its historical authorship is retained. A subsequent
preview must be rebuilt and tested from its own exact published commit.
