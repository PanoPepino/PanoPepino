# Project content and profile synchronisation

## Current scope

Five public project repositories own their root `README_FOR_WEBPAGE.md` files.
The profile repository owns the public Da Timeless description and Manim
Ecosystem introduction under `content/`. Da Timeless private source is never
read by automation. Fencing, Dark Bubble Figures and legacy MTGA are excluded.

This implementation updates only the profile's Selected Projects section.
Existing technical project READMEs are unchanged. Website integration is deferred;
no website source, workflow or deployment is changed.

## Edit content

Each file contains exactly three ordered, nonempty comment-delimited blocks:

- `SHARED`: plain `# Name`, then one technology line separated by ` · `.
- `WEBPAGE`: website description, reserved for future website integration.
- `PANOPEPINO`: concise GitHub profile description.

Write plain Markdown paragraphs and bullet lists. No raw HTML or extra headings
inside destination blocks. Inline links must use absolute HTTPS URLs. Keep claims
consistent across blocks. The profile uses SHARED name/technologies and PANOPEPINO
copy; WEBPAGE copy never enters the profile. Canonical public links and ordering
live in `content/projects.json`. Only three Manim components are registered.

## Local generation and preview

Run from `portfolio/PanoPepino` with Python 3.10 or newer:

```bash
python3 scripts/sync_projects.py
python3 scripts/sync_projects.py --check
python3 -m unittest discover -s tests -v
python3 scripts/preview_profile.py
```

The first command reads sibling project checkouts and updates local README.md.
Use `--workspace /path/to/portfolio` for a different checkout layout.
The second command checks drift without writing. All source files and README
markers are validated before any output is written. Invalid or missing sources
leave the previous README intact. Bytes outside PROJECTS markers are preserved.
Repeated generation with unchanged inputs produces no diff.

Preview requires GitHub CLI with API access. It sends this public README text to
GitHub's Markdown rendering API, then creates `.preview/index.html`. Open that
file in a browser. Rendering uses GitHub Markdown; dark-theme styling approximates
GitHub rather than recreating the complete profile interface. External badges
and images still require internet access. Preview output is ignored by Git.

## GitHub automation

1. Publish each public project's `README_FOR_WEBPAGE.md` to its default branch.
   Publish content before the receiving workflow so its first fetch can succeed.
2. Publish the profile implementation to its default branch.
3. Create a fine-grained personal access token restricted to
   `PanoPepino/PanoPepino`, with **Contents: Read and write**. Repository dispatch
   requires that permission. Add it as the Actions secret `PROFILE_SYNC_TOKEN`
   in each of the five public project repositories. Use a token expiry and
   renew the secret when required. Do not put a token in source files.
4. Publish the five `notify-profile.yml` workflows, then push an edit to
   `README_FOR_WEBPAGE.md` on a source repository's default
   branch. Its notifier sends `projects-updated` to the profile repository.
5. The profile workflow fetches all five approved public files, pins each read
   to a resolved default-branch commit, logs those revisions, validates all
   content, and commits README.md only when generated text differs.

The profile workflow also runs after changes to its own content/tooling, on
manual dispatch and hourly at minute 17 as recovery if notifications fail.
Notifications are hints: payload values never select repositories, refs, paths
or commands. Sources come exclusively from the checked-in registry and current
public default branches. Rapid edits may be combined into one latest update.

The profile writes using its own GITHUB_TOKEN. Concurrent runs are serialised.
If a normal push is rejected, the job fetches the latest profile branch and
regenerates once, preserving concurrent README edits outside markers. A second
rejection fails; it never force-pushes. Branch rules may require a PR-based
publication flow instead of direct bot commits; repository policy is not changed
by this implementation. See Actions logs for missing files, invalid content,
expired notification tokens and rejected pushes.

Hourly/manual profile synchronisation needs the published source files and
receiving workflow, plus permission for the profile bot to commit. Immediate
notifications additionally require the five source workflows and secrets.
Local generation performs no publication or token setup.

To configure all five secrets after creating the restricted token, run from
the profile repository:

```bash
python3 scripts/configure_notifications.py
```

The helper prompts securely without echo and passes the token through stdin
to GitHub CLI. It never writes the token to a file or prints it. GitHub CLI must
already be signed in with permission to administer source repository secrets.
Never paste the token into chat. An expired token must be replaced with the same
command. This helper stores secrets only; it does not create a token or alter its
permissions.

## References

- [Repository dispatch API and required token permission](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [Triggering GitHub workflows](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
