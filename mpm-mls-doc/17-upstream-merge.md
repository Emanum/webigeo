# 17 — Upstream merge: state of the preparation

State of 2026-11-14. The avalanche simulation goes to **weBIGeo/webigeo** as one merge request. This
file records how the code is prepared for it, what is done, what is open and how to keep it current.

> **Provisional.** weBIGeo is going to move to a plugin-based structure. The avalanche simulation will
> then become a plugin rather than a merge of these files into the app, so the branches, the file list
> and the history plan below describe the preparation as it stands, not the final way in. The course
> submission is this fork's `main`; the upstream merge is not part of it.

## 1. Repositories and branches

```
AlpineMapsOrg/renderer  ←  weBIGeo/webigeo  ←  Emanum/webigeo (this fork)
   remote `upstream`          remote `webigeo`        remote `origin`
```

The merge target is **weBIGeo/webigeo**, not AlpineMapsOrg/renderer. The git remote named `upstream`
points to AlpineMapsOrg/renderer and is not the target.

| Branch (on `origin`) | Purpose |
|---|---|
| `main` | Our development and release branch. Keeps everything: project notes, iOS, validation tooling, tests. |
| `upstream-candidate` | `main` minus everything weBIGeo should not get. The source of the merge request. |
| `upstream-main` | A mirror of `webigeo/main` (1b3f3cbb), only the base of the staging pull request. |

[Emanum/webigeo#19](https://github.com/Emanum/webigeo/pull/19) (draft, `upstream-candidate` →
`upstream-main`) shows exactly the diff weBIGeo would receive. It is a staging view: it is not merged
here, and no pull request exists on weBIGeo/webigeo yet. weBIGeo's CI does not run on it, because its
workflows only trigger on pull requests into `main`.

`main` already contains all of weBIGeo's `main`, so `upstream-candidate` needed no rebase. Day-to-day
work happens on `main`; the candidate only receives merges from `main`. Build on `main` in the IDE:
the candidate's wasm preset has weBIGeo's own Windows Qt path, which does not load on this machine.

## 2. What `upstream-candidate` contains

Against `webigeo/main` (at `35dbee35`): **143 files** (71 new, 72 changed), +15 586 / −203 lines, 147 commits.

| Area | Files | Content |
|---|---|---|
| `webgpu/compute` | 50 | Solver node, WGSL kernels, simulation driver, AvaFrame nodes; PR #2's node lifetime changes |
| `webgpu/engine` | 34 | 3D avalanche rendering; PR #2's pipeline registration handles in the renderers and overlays |
| `apps/webgpu_app` | 25 | Avalanche panel, sandbox view, AvaFrame download, node renderers |
| `docs/avalanche` | 14 | Technical reference: theory, files and API, shaders, data layout, tuning, constitutive models, rendering, simulation driver, release areas on the map, entrainment, raw grid view, references |
| `webgpu/base` | 6 | PR #2's `PipelineRegistration` in the resource registry and the raii read-backs; Objective-C++ for macOS |
| `nucleus/camera`, `unittests` | 2 + 4 | Orbit camera zoom limit and its tests, the registry lifetime tests |
| other | | `README.md` (links), `.gitignore` (`.idea`), `CMakePresets.json` (macOS presets), `cmake/alp_macos_deploy.cmake`, `docs/webgpu_app.md` (macOS build), `docs/camera_controls.md`, `docs/time_stepped_simulations.md`, `misc/scripts/serve_wasm.py` |

### Left out of the candidate (stays in Emanum/webigeo)

- `claude_log.md`, `AVALANCHE_SIM_PLAN.md`, `CMAKE_FOR_WEBDEVS.md`, `WEBGPU_OVERVIEW.md`, `imgui.ini`.
- The iOS port: app code, presets, Dawn/SDL cross-build options, `docs/webgpu_app_ios.md`.
- Auto-load of the avalanche graph at launch (checkbox, stored settings, the web default and its
  `?avalanche=` switches).
- `.github/workflows/`, `docs/webgpu_app.md`, `docs/webgpu_app_dev.md`: as on weBIGeo's `main`.
- Verification, benchmarks, the AvaFrame comparison pipeline, the Python reference implementations,
  the GPU golden tests and the audit reports (all of `mpm-mls-doc/` except the 15 docs above). Links
  and code comments in the candidate point to `Emanum/webigeo` on GitHub.
- Local paths: the macOS presets read Qt from `$env{HOME}/Qt/6.11.1/macos`; the wasm preset is
  weBIGeo's original.

## 3. Verification

| What | State |
|---|---|
| macOS release build of the candidate | builds (last checked after merging `main` with PR #2, `35dbee35`) |
| Web (wasm) build | links (same state) |
| Unit tests (macOS) | `webgpu_compute` all pass (with the MPM golden tests, which are not in the candidate); `nucleus` 2 failing cases and `webgpu_engine` 1: timing checks in the tile scheduler and two benchmarks, not our code |
| App launched on the candidate | **no** |
| Web: IndexedDB storage of the sandbox folder | tested in a browser on `main`: the download survives a reload; dropping data of an older AvaFrame commit not separately tested |

## 4. Open before the merge request

- [ ] **Smoke-test the app** built from `upstream-candidate` (map, panel, a run on the map, the AvaFrame sandbox).
- [ ] **History.** Decided: weBIGeo does not get the candidate's 147 commits (they add and later
      delete the iOS port, `claude_log.md`, personal paths and the validation tooling). The history is
      rewritten into a clean one for the merge request, see section 6. `main` keeps its full history.
- [x] **macOS bundling** goes upstream: presets, `cmake/alp_macos_deploy.cmake`, documented in `docs/webgpu_app.md`.
- [ ] **Tests.** Only the two `nucleus` tests are in the candidate. Decide whether the golden tests
      and the benchmark belong in the merge request.
- [ ] **PR #19 description** still lists the state of 10 November; update it.
- [ ] Check the 3 failing test cases against plain weBIGeo `main`.

## 5. Keeping the candidate current (until the merge)

1. Work and commit on `main`.
2. Merge `main` into `upstream-candidate` (not a rebase; no force-push). Conflicts are expected in
   files the candidate deleted (`claude_log.md`, `mpm-mls-doc/…`): keep them deleted. For
   `CMakePresets.json` and `docs/avalanche/*` keep the candidate's version and re-apply the change by hand.
3. Build both builds, run the tests, push.
4. When weBIGeo's `main` moves: `git fetch webigeo`, merge it into `main`, then into the candidate, and
   push `webigeo/main` to `upstream-main` (`git push --force-with-lease=upstream-main origin webigeo/main:refs/heads/upstream-main`).

## 6. Clean history for weBIGeo, full history for the fork

Implemented as: the candidate stays the working branch for what ships. The merge request is made from a
separate branch with new commits, and `main` is never rewritten. This is due to two limits: weBIGeo
should not see the 147 commits that add and delete the bloat, and the fork has to keep its own history
(the merged pull requests #1–#19 link to it) and keep receiving weBIGeo's updates after the merge.

**Before the merge request**

1. `git switch -c upstream-history webigeo/main`, then commit the candidate's final tree on it as one
   commit or a few meaningful ones (for example solver and shaders, rendering, simulation driver,
   AvaFrame, docs), for instance with `git checkout upstream-candidate -- <paths>` per commit.
   The last commit must give a tree identical to `upstream-candidate`
   (`git diff upstream-candidate upstream-history` is empty).
2. Open the merge request from `upstream-history`. `upstream-candidate` stays as the reference and is
   not sent.

**After weBIGeo merged it** (a squash or rebase merge makes new commits in weBIGeo's `main` with the
same file contents as `main` has)

1. `git fetch webigeo` and merge `webigeo/main` into `main`. Changes that both sides made identically
   merge without conflict, and files that only exist in `main` (the bloat) are untouched. If a file
   differs because weBIGeo's review changed it, keep weBIGeo's version (`git checkout --theirs`).
2. From then on the fork's `main` follows weBIGeo's `main` by plain merges, as before.

**Later changes to the avalanche code** (the candidate branch is then obsolete, because the history
behind it is not weBIGeo's)

1. Make `upstream-candidate-2` from the new `webigeo/main`.
2. Bring over what changed in `main` since the last synced commit, only for the shipped paths
   (`webgpu/`, `apps/webgpu_app/`, `docs/avalanche/`, the two docs, the presets, …):
   `git diff <last-synced-main> main -- <paths> | git apply`, or `git cherry-pick` of the commits
   that touch only those paths.
3. Merge request from that branch. Keep the path list and the last synced commit of `main` in this file.

## 7. Pitfalls found on the way

- The `upstream` remote is AlpineMaps. A rebase onto it was started by mistake and undone; AlpineMaps
  has since restructured its CMake and moved `Raster` into radix, which weBIGeo's `main` does not have.
- Build experiments in a worktree need their own copy of `extern/` (`cp -cR` is instant on APFS).
  Symlinking the shared folder lets another branch's pinned dependency versions move its checkouts.
- Rider drops its generated run configurations when the CMake profile fails to load, as on the
  candidate's wasm preset. Use `main` in the IDE.
- In a hidden browser pane the page's animation loop is paused, so Qt timers (including the web
  startup wait for the stored data) do not run: test web changes in a visible tab.
