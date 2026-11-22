# Web previews of branches

Runs the multithreaded web build of any branch of this repository at its own address on the
owner's preview server, so a change can be looked at in the browser before it is merged or sent
upstream. One container per branch; the address is `https://<name>.<preview domain>/webgpu_app.html`.

`<name>` is the last part of the branch name, lower case, only `a-z 0-9 -`, at most 40 characters:
`am/lifetime-fixes` becomes `lifetime-fixes`.

## Use

- **Build and publish:** GitHub -> Actions -> *Preview* -> *Run workflow*, input the branch name.
  It builds the web release and pushes the image `webigeo-preview:<name>` to the registry. The first
  run after a change of Qt or Emscripten builds Qt from source (long); later runs restore it from
  the cache. The workflow starts by hand only; it does not run on push or pull request and does not
  change the other workflows.
- **Show it:** the preview server is a Portainer stack that updates from a git repository (GitOps):
  one service per preview, each running `webigeo-preview:<name>` with `pull_policy: always`. After
  the push the workflow calls the stack's webhook (secret below), which redeploys the stack and
  fetches the new image. The webhook can only redeploy that one stack; no server credentials are
  stored in GitHub. Without the secret the step is skipped and the stack's *Pull and redeploy*
  button does the same by hand.
- **New preview:** run the workflow once for the branch (the image has to exist), then add a service
  named `webigeo-preview-<name>` to the stack's compose file in git.
- **Remove a preview:** delete its service from the compose file.

## How it works

```
Preview workflow (workflow_dispatch, runs from main)
  checkout <branch> -> Qt/Emscripten build (wasm_mt, as in deploy.yml)
  -> image: nginx + build, with the cross-origin isolation headers
  -> push to the registry   <registry>/webigeo-preview:<name>
  -> POST to the stack's webhook (optional)

Portainer stack "previews" (compose file in git, pull_policy: always)
  -> container webigeo-preview-<name> on the reverse proxy's Docker network
  -> the server routes <name>.<preview domain> to the container of that name
```

The compose file names the reverse proxy's network, so it lives in the owner's own infrastructure
repository, not here. Each service needs `container_name: webigeo-preview-<name>` and the proxy network.

## Settings

Environment **previews** (Settings -> Environments). Set *Deployment branches* to the `main` branch
only: the workflow file is read from `main`, and the secrets must not be reachable from other branches.

| Name | Kind | Content |
| --- | --- | --- |
| `DOCKER_REPO_USERNAME` | secret | registry user that may push the preview images |
| `DOCKER_REPO_PASSWORD` | secret | its password |
| `PORTAINER_WEBHOOK_URL` | secret | webhook URL of the preview stack; optional, makes a push show up at once |
| `PREVIEW_REGISTRY` | variable | registry host, no `https://` |
| `PREVIEW_DOMAIN` | variable | the domain below `<name>.`, only used to print the address |

No host names, addresses or account names are written in this repository: they live in these
settings and in the infrastructure repository.
