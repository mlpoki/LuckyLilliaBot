# LLBot Release mirror

Run **Mirror upstream release** manually from `main`. It resolves the upstream
latest official Release once and mirrors its exact tag and four Windows/Linux
packages. No input version or additional secret is required. The runner uses
the fork `GITHUB_TOKEN` with `contents: write`.

The original lightweight or annotated tag object and reachable source objects
are pushed without changing `main`. Packages are renamed according to `NAMES`
in `mirror.py` and retain their original bytes and signatures. Release notes
retain upstream text and links and append a source marker and provenance.
Runtime functionality is unverified. No application build, npm publication,
macOS asset or Docker dispatch occurs in this path. The fork Docker job is
disabled and its Release trigger is removed.

The optional `v*` push trigger resolves upstream latest too. GitHub loads a tag
push workflow from that tag's source tree, so an unchanged upstream tag can
contain an older workflow. The reliable first entry is dispatch from `main`.
Tag pushes by `GITHUB_TOKEN` do not trigger another run. This run continues
directly through publishing.

New releases stage as drafts until all four assets are uploaded and verified.
Reruns reuse matching assets and fill missing ones. Interrupted uploads retain
the draft or partial published state. A conflicting tag, changed upstream input,
different target bytes or unmarked existing Release stops the run. Unrelated
assets remain in place. A failed upload may leave a GitHub placeholder asset,
which is reported as a conflict and requires inspection before retrying.

Every run uploads `evidence.json`, also included in the job summary. It records
the source Release/asset IDs, workflow and script commits, tag object and commit,
source/target names, sizes, SHA-256 values and partial upload progress. Published
assets are downloaded again and hashed. Mirror behavior tests use temporary
local Git repositories and fake HTTP responses on Actions. They require no
application dependencies and exercise original annotated tags, first sync,
reruns, absent inputs, conflicts, input mutations and upload recovery.

References

- https://docs.github.com/en/rest/releases/releases
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
