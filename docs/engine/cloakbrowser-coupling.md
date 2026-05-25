# CloakBrowser Manager 旧内核耦合点

本文记录 Manager 当前与 CloakBrowser Chromium 的耦合点，作为替换为 `invisible_playwright` 的手术清单。

## 后端依赖与启动

- `backend/requirements.txt` 依赖 `cloakbrowser[geoip]>=0.3.14`。
- `backend/browser_manager.py` 直接导入 `from cloakbrowser import launch_persistent_context_async`。
- `BrowserManager.launch()` 构造 Chromium 参数后调用 `launch_persistent_context_async(...)`，并传入：
  - `user_data_dir`
  - `headless`
  - `proxy`
  - `args`
  - `timezone`
  - `locale`
  - `humanize`
  - `human_preset`
  - `geoip`
  - `color_scheme`
  - `user_agent`
  - `viewport`
  - `env={..., "DISPLAY": f":{display}"}`

## Chromium 专属参数

`BrowserManager._build_fingerprint_args()` 输出 CloakBrowser Chromium 专属命令行参数：

- `--fingerprint=<seed>`
- `--fingerprint-platform=<windows|macos|linux>`
- `--fingerprint-gpu-vendor=<vendor>`
- `--fingerprint-gpu-renderer=<renderer>`
- `--fingerprint-hardware-concurrency=<n>`
- `--fingerprint-screen-width=<width>`
- `--fingerprint-screen-height=<height>`
- `--disable-infobars`
- `--test-type`
- `--use-angle=swiftshader`

这些参数不能直接传给 `invisible_playwright` Firefox，必须改为 `seed`、`pin`、`extra_args`、`locale`、`timezone` 等 Python API 参数。

## CDP 耦合

Manager 当前为每个 profile 分配 `5100-5199` 之间的 CDP 端口，并追加 `--remote-debugging-port=<port>`。

后端暴露以下 Chromium CDP 代理端点：

- `GET /api/profiles/{profile_id}/cdp`
- `GET /api/profiles/{profile_id}/cdp/json/version`
- `GET /api/profiles/{profile_id}/cdp/json/list`
- `WS /api/profiles/{profile_id}/cdp`
- `WS /api/profiles/{profile_id}/cdp/devtools/{path:path}`

`invisible_playwright` 基于 Firefox/Juggler，不提供 Chromium DevTools Protocol。第一阶段保留 UI 入口但禁用提示，后端上述端点返回 `501 Not Implemented`。外部自动化能力作为第二阶段独立设计。

## noVNC 与 Xvnc 耦合

以下能力与浏览器内核无强耦合，应保留：

- `backend/vnc_manager.py` 分配 `DISPLAY=:100+` 和 KasmVNC websocket 端口 `6100+`。
- `BrowserManager.launch()` 在启动浏览器前调用 `vnc.start_vnc(...)`。
- 前端通过 `WS /api/profiles/{profile_id}/vnc` 连接 noVNC。

替换内核后的关键要求是：`invisible_playwright` 启动的 Firefox 必须运行在 Manager 分配的 `DISPLAY` 上，才能继续通过 noVNC 网页操控。

## Profile 初始化耦合

`_init_profile_defaults()` 当前创建 Chrome profile 结构：

- `Default/Bookmarks`
- `Default/Preferences`

Firefox persistent profile 不使用该结构。第一阶段应停止写入 Chrome 专属文件，避免污染 invisible Firefox profile。默认书签/搜索引擎如需支持，应后续按 Firefox profile 格式单独实现。
