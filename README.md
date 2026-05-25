<p align="center">
<img src="https://i.imgur.com/cqkp6fG.png" width="500" alt="CloakBrowser">
</p>

<h3 align="center">CloakBrowser Manager with invisible_playwright</h3>

<p align="center">
创建、管理和启动隔离的指纹浏览器 profile。<br>
本分支保留 CloakBrowser Manager 管理面板和 noVNC 网页操控，后端浏览器内核切换为 invisible_playwright patched Firefox。
</p>

<p align="center">
<a href="https://github.com/CloakHQ/CloakBrowser"><img src="https://img.shields.io/github/stars/cloakhq/cloakbrowser?label=CloakBrowser" alt="Stars"></a>
<a href="https://hub.docker.com/r/cloakhq/cloakbrowser-manager"><img src="https://img.shields.io/docker/pulls/cloakhq/cloakbrowser-manager?label=docker&logo=docker&logoColor=white" alt="Docker Pulls"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
</p>

---

<p align="center">
<img src="https://i.imgur.com/twdX81Q.png" width="800" alt="CloakBrowser Manager — Browser View">
<br>
<img src="https://i.imgur.com/XFYn1qY.png" width="800" alt="CloakBrowser Manager — Profile Settings">
</p>

每个 profile 都是一个隔离的 invisible_playwright Firefox 持久化上下文，拥有独立 fingerprint seed、代理、cookies 和 session 数据。Profiles 会跨重启持久化，服务运行在一个 Docker 容器中。

```bash
docker build -t cloakbrowser-invisible-manager .
docker run -p 8080:8080 -v cloakprofiles:/data cloakbrowser-invisible-manager
```

Or build from source:

```bash
git clone https://github.com/CloakHQ/CloakBrowser-Manager.git cloakbrowser-invisible-manager
cd cloakbrowser-invisible-manager
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) in your browser. Create a profile. Click Launch. Done.

> **迁移阶段说明**：当前第一阶段目标是 profile 管理、启动/停止和 noVNC 网页操控可用。Chromium CDP 自动化接口在 invisible_playwright Firefox 后端下暂不可用，后端会返回 `501 Not Implemented`。

## Why Not Just Use a VPN?

A VPN only changes your IP. Incognito only clears cookies. Chrome profiles share the same hardware fingerprint underneath. Platforms use 50+ signals to link your accounts — canvas, WebGL, audio, GPU, fonts, screen size, timezone.

每个 profile 会基于独立 seed 生成不同的设备身份。对网站来说，每个 profile 都像一台不同的电脑。

| Solution | What it changes | Accounts linked? |
|----------|----------------|-----------------|
| VPN | IP address only | Yes — same fingerprint |
| Incognito | Clears cookies | Yes — same fingerprint |
| Chrome profiles | Separate bookmarks/cookies | Yes — same hardware fingerprint |
| **invisible_playwright profile** | **Everything — full device identity per profile** | **No** |

## Features

- **Profile management** — create, edit, delete browser profiles with unique fingerprints
- **Per-profile settings** — fingerprint seed, proxy, timezone, locale, user agent, screen size, platform
- **One-click launch/stop** — each profile runs as an isolated invisible_playwright Firefox context
- **Session persistence** — cookies, localStorage, and cache survive browser restarts
- **In-browser viewing** — interact with launched browsers via noVNC, directly in the web GUI
- **CDP status** — CDP toolbar entry is retained but disabled in phase one because Firefox does not expose Chromium CDP
- **Optional authentication** — protect the web UI and API with a single token, or run wide open locally
- **Powered by invisible_playwright** — deterministic stealth profiles on patched Firefox

## Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Tailwind CSS
- **Browser viewer**: noVNC (WebSocket-based VNC client)
- **Database**: SQLite
- **Browser engine**: [invisible_playwright](https://github.com/feder-cr/invisible_playwright) (patched Firefox)

## Development

### Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker compose up --build
```

## Requirements

- Docker (20.10+)
- ~2 GB disk (image + binary)
- ~512 MB RAM per running profile

## Updating

重新构建本地镜像并重启：

```bash
docker build -t cloakbrowser-invisible-manager .
docker stop <container-id>
docker run -p 8080:8080 -v cloakprofiles:/data cloakbrowser-invisible-manager
```

Your profiles and session data are stored in the `cloakprofiles` volume and persist across updates.

## Automation API

第一阶段不再伪装 Chromium CDP。`invisible_playwright` 使用 patched Firefox，运行中的 profile 仍可通过 noVNC 网页操控，但以下接口会返回 `501 Not Implemented`：

```text
GET /api/profiles/<profile-id>/cdp
GET /api/profiles/<profile-id>/cdp/json/version
GET /api/profiles/<profile-id>/cdp/json/list
```

前端 toolbar 保留 code 图标，但在 `cdp_url=null` 时禁用并提示 CDP 当前不可用。后续自动化能力需要单独设计 Firefox/Juggler 或自建桥接 API。

## Remote Access

The container binds to localhost only. To access from a remote server:

```bash
ssh -L 8080:localhost:8080 your-server
```

Then open `http://localhost:8080`.

## Authentication

By default, there is no authentication (ideal for local use). To protect the web UI and API when hosting on a network, set the `AUTH_TOKEN` environment variable:

```bash
docker run -p 8080:8080 -v cloakprofiles:/data -e AUTH_TOKEN=your-secret-token cloakbrowser-invisible-manager
```

Or in `docker-compose.yml`:

```yaml
environment:
  - AUTH_TOKEN=your-secret-token
```

When `AUTH_TOKEN` is set:

- The web UI shows a login page. Enter the token to unlock.
- API consumers pass the token via `Authorization: Bearer <token>` header.
- VNC WebSocket connections are authenticated via the login cookie.
- The `/api/status` endpoint remains unauthenticated (for Docker healthcheck).

> **Note**: The auth token is transmitted in cleartext over HTTP. If you expose the Manager to the internet, put it behind a reverse proxy with HTTPS (Caddy, nginx, Traefik).

## License

- **This application** (GUI source code) — MIT. See [LICENSE](LICENSE).
- **invisible_playwright** — MIT. The Docker image pre-downloads its patched Firefox binary with `python -m invisible_playwright fetch`.

本分支不再下载或运行 CloakBrowser Chromium binary。旧的 `BINARY-LICENSE.md` 仅用于上游历史背景，不代表当前运行依赖。

## Contributing

Contributions are welcome. Please [open an issue](https://github.com/CloakHQ/CloakBrowser-Manager/issues) first to discuss what you'd like to change.

## Links

- **invisible_playwright** — [github.com/feder-cr/invisible_playwright](https://github.com/feder-cr/invisible_playwright)
- **Upstream Manager** — [github.com/CloakHQ/CloakBrowser-Manager](https://github.com/CloakHQ/CloakBrowser-Manager)
- **Website** — [cloakbrowser.dev](https://cloakbrowser.dev)
- **Bug reports** — [GitHub Issues](https://github.com/CloakHQ/CloakBrowser-Manager/issues)
- **Contact** — cloakhq@pm.me
