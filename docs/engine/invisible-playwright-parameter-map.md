# invisible_playwright 参数映射初稿

本文记录 Manager profile 字段到 `invisible_playwright` Python API 的第一阶段映射。依据来自 `feder-cr/invisible_playwright` commit `3d8ba0b82c51854aa5fe1fe35240553294be02f8`。

## API 入口

第一阶段后端使用 async 入口：

```python
from invisible_playwright.async_api import InvisiblePlaywright

runner = InvisiblePlaywright(...)
context = await runner.__aenter__()
```

当传入 `profile_dir` 时，`InvisiblePlaywright.__aenter__()` 调用 Playwright 的 `firefox.launch_persistent_context(...)`，返回 `BrowserContext`，这与 Manager 现有 `RunningProfile.context` 的生命周期模型匹配。

## Manager 字段映射

| Manager 字段 | invisible 参数 | 第一阶段策略 |
| --- | --- | --- |
| `fingerprint_seed` | `seed` | 直接传整数；为空时沿用数据库创建时生成的随机 seed。 |
| `user_data_dir` | `profile_dir` | 直接传 profile 持久化目录。 |
| `proxy` | `proxy` | 解析为 `{"server": "...", "username": "...", "password": "..."}`。HTTP/HTTPS 交给 Playwright，SOCKS 写入 Firefox proxy prefs。 |
| `timezone` | `timezone` | 非空时直传 IANA timezone。 |
| `locale` | `locale` | 非空时直传；为空默认 `en-US`。 |
| `screen_width` / `screen_height` | `pin["screen.width"]` / `pin["screen.height"]` | 直传，另外设置 `screen.avail_width` 和 `screen.avail_height`，保持与 noVNC 窗口一致。 |
| `gpu_vendor` / `gpu_renderer` | `pin["gpu.vendor"]` / `pin["gpu.renderer"]` | 仅非空时传；建议与 `gpu.class_tier` 一起使用，否则可能破坏采样一致性。 |
| `hardware_concurrency` | `pin["hardware.concurrency"]` | 非空时传。 |
| `color_scheme` | `pin["dark_theme"]` | `dark` -> `True`，`light` -> `False`，`no-preference` 不 pin。 |
| `launch_args` | `extra_args` | 作为 Firefox extra args 传入；不再解释为 Chromium flags。 |
| `headless` | 暂不直用 | 第一阶段为了 noVNC 网页操控，强制 headed on Xvnc；UI 显示为暂不支持隐藏运行。 |
| `humanize` | `humanize` | 直传布尔值。 |
| `human_preset` | 无直接等价 | 第一阶段忽略 preset；后续可扩展为 `humanize=True` 或秒数上限。 |
| `geoip` | 无直接等价 | 第一阶段不自动解析代理 IP；保留字段但不传。 |
| `user_agent` | 无公开参数 | 第一阶段不支持自定义 UA；invisible 默认锁定为 Windows Firefox 150。 |
| `platform` | 无直接等价 | 第一阶段不支持 windows/macos/linux 切换；invisible 默认报告 Windows Firefox。 |

## GUI / noVNC

Manager 的网页操控依赖 Xvnc，而不是 CDP。第一阶段必须：

- 继续使用 `VNCManager` 启动 `Xvnc :<display>`。
- 启动 invisible Firefox 前把 `DISPLAY=:{display}` 放入进程环境。
- `headless=False`，让 Firefox 真实绘制到 Xvnc display。

`invisible_playwright` 自带 `headless=True` 会创建自己的虚拟显示并仍以 headed 方式运行，这会绕过 Manager 分配的 Xvnc display，因此第一阶段不使用它。

## CDP 不兼容

`invisible_playwright` 使用 Firefox，不提供 Chromium CDP。第一阶段：

- 后端 CDP 路由返回 `501 Not Implemented`。
- 前端保留 CDP 入口但禁用提示。
- 第二阶段单独调研 Firefox/Juggler 或自建自动化桥接接口。

## 源码依据

- `src/invisible_playwright/async_api.py`
  - `InvisiblePlaywright.__init__` 参数定义。
  - `__aenter__` 中 `firefox.launch_persistent_context(...)`。
  - `_build_env()` 传递 `TZ` 和 `STEALTHFOX_WEBRTC_PUBLIC_IP`。
- `src/invisible_playwright/_proxy.py`
  - SOCKS proxy 写入 `network.proxy.*` prefs。
  - HTTP/HTTPS proxy 原样返回给 Playwright。
- `src/invisible_playwright/_fpforge/profile.py`
  - `pin` 支持的 dotted keys。
- `docs/pinning.md`
  - pinning 的一致性风险和推荐用法。
