# Invisible Browser Manager

一个可视化指纹浏览器管理面板。后端使用 `invisible_playwright` patched Firefox；每个 profile 都是独立持久化浏览器上下文，支持 noVNC 网页操控和 Automation REST API。

启动 profile 时，如果 `timezone` 或 `locale` 留空，后端会根据当前出口 IP 自动解析并补齐。配置了代理时，GeoIP 查询会通过代理发出；未配置代理时，查询使用 manager 容器自己的出口 IP。手动填写的 `timezone` / `locale` 始终优先，不会被自动检测覆盖。

GeoIP 解析按 `ip-api.com`、`ipapi.co`、`ipwho.is` 顺序 fallback。每次成功解析都会写入 profile 的 `last_geoip_*` 字段，包括出口 IP、国家代码、时区、语言、来源服务和解析时间；`timezone` / `locale` 字段仍只表示手动覆盖配置。

## 直接运行

本镜像当前只支持 `linux/amd64`：

```bash
cd /home/jeff/code/cloakbrowser-invisible-manager
docker build --platform linux/amd64 -t invisible-browser-manager .
docker run --rm -p 127.0.0.1:8080:8080 -v invisible-browser-profiles:/data invisible-browser-manager
```

打开：

```text
http://localhost:8080
```

如需登录保护：

```bash
docker run --rm \
  -p 127.0.0.1:8080:8080 \
  -v invisible-browser-profiles:/data \
  -e AUTH_TOKEN=your-secret-token \
  invisible-browser-manager
```

默认命令只绑定 `127.0.0.1`，避免无认证时暴露到局域网。远程测试建议用 SSH tunnel：

```bash
ssh -L 8080:127.0.0.1:8080 your-server
```

## UI 验收路径

1. 打开 `http://localhost:8080`
2. 点击 `New Profile`
3. 填写 profile name，按需配置代理、时区、语言、屏幕尺寸、GPU、标签和启动参数
4. 点击 `Create`
5. 点击 `Launch`
6. 右侧 viewer 显示 `Connected` 后即可在网页中操作 Firefox
7. 点击 viewer 工具栏的 code 图标复制 Automation API endpoint
8. 点击顶部 `Stop` 停止当前 profile

## Automation API

当前产品不对外暴露 Chromium CDP WebSocket。自动化入口是 manager 提供的 REST API；如果旧脚本依赖 `puppeteer.connect()` 或 `chromium.connectOverCDP()`，需要改造成 REST API 调用，或在产品层保留单独的 Chromium/CDP 引擎。

运行中的 profile 会返回：

```json
{
  "automation_url": "/api/profiles/<profile-id>/automation"
}
```

可用接口：

```text
GET    /api/profiles/{profile_id}/automation
GET    /api/profiles/{profile_id}/automation/pages
POST   /api/profiles/{profile_id}/automation/pages
POST   /api/profiles/{profile_id}/automation/pages/{page_ref}/goto
POST   /api/profiles/{profile_id}/automation/pages/{page_ref}/evaluate
POST   /api/profiles/{profile_id}/automation/pages/{page_ref}/screenshot
DELETE /api/profiles/{profile_id}/automation/pages/{page_ref}
```

`page_ref` 可以是页面 index，例如 `0`，也可以是 `/pages` 返回的稳定 `page_id`。自动化脚本建议先创建新页面，再使用 `page_id` 控制，避免 Firefox 内置页面限制。

最小示例：

```bash
PROFILE_ID=<running-profile-id>

curl "http://localhost:8080/api/profiles/$PROFILE_ID/automation/pages"

PAGE_ID=$(
  curl -s -X POST "http://localhost:8080/api/profiles/$PROFILE_ID/automation/pages" \
    | python -c 'import json,sys; print(json.load(sys.stdin)["page_id"])'
)

curl -X POST "http://localhost:8080/api/profiles/$PROFILE_ID/automation/pages/$PAGE_ID/goto" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","wait_until":"domcontentloaded","timeout_ms":30000}'

curl -X POST "http://localhost:8080/api/profiles/$PROFILE_ID/automation/pages/$PAGE_ID/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"expression":"document.title"}'

curl -X POST "http://localhost:8080/api/profiles/$PROFILE_ID/automation/pages/$PAGE_ID/screenshot" \
  -H "Content-Type: application/json" \
  -d '{"full_page":true}' \
  --output screenshot.png
```

开启 `AUTH_TOKEN` 后，API 请求加：

```bash
-H "Authorization: Bearer <token>"
```

`evaluate` 会在页面中执行 JavaScript，只应在可信网络或认证保护下使用。

## Compose

```bash
docker compose up --build
```

Compose 默认绑定：

```text
127.0.0.1:8080
```

数据目录：

```text
~/.invisible-browser-manager
```

## 本地开发

后端：

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
uvicorn backend.main:app --reload --port 8080
```

前端：

```bash
cd frontend
npm install
npm run dev
```

测试：

```bash
. .venv/bin/activate && python -m pytest backend/tests -q
cd frontend && npm test
cd frontend && npm run build
```

## 运行依赖

- Docker 20.10+
- `linux/amd64`
- 约 2 GB 磁盘空间
- 每个运行中的 profile 建议预留 512 MB 以上内存

## License

本应用源码使用 MIT License。浏览器内核来自 `invisible_playwright`，Docker 构建时通过：

```bash
python -m invisible_playwright fetch
```

下载 patched Firefox。
