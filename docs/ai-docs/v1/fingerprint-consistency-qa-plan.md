# 指纹一致性 QA 计划

## 目标

把 CloakBrowser 的验收目标从“能启动浏览器”升级为“能承载 Project Mileage 远程账号工作台的账号环境”。用户买到的是一个可远程操作的账号环境，不只是一个网页 VNC 画面；所以浏览器必须同时满足三件事：

- 账号平台看到的浏览器身份要像真实用户设备。
- Project Mileage 看到的运行状态要可信，不能伪造订单、登录、VNC、扣费或成功状态。
- 公开检测站点不能出现明显红灯，例如自动化、WebRTC 泄漏、IP/时区/语言不一致、内核版本和 UA 不一致。

这里的“100% 完美伪装”在工程上定义为：指定测试矩阵全部达到 PASS，且没有 P0/P1 红灯。不能承诺对所有未知网站永久不可检测；检测站规则、账号平台风控和浏览器内核都会更新，因此矩阵要作为持续回归门禁。

## Project Mileage 业务反推

Project Mileage 的账号商品和远程工作台场景决定了 CloakBrowser 不是普通浏览器面板，而是“账号运行环境底座”。按业务倒推，核心目标如下：

1. 用户购买账号后，只能通过 Payload 授权后的安全 DTO 看到自己有权使用的 profile，不允许 App 直连 CloakBrowser runtime。
2. 账号平台看到的环境必须稳定：同一个 profile 重启后指纹不乱跳，cookie/local storage 和浏览器指纹不互相打架。
3. 账号平台看到的环境必须一致：出口 IP、WebRTC、timezone、locale、Accept-Language、screen、viewport、GPU、hardwareConcurrency、browser version 不能互相矛盾。
4. 远程桌面要像真实桌面：VNC 画面大小、浏览器窗口、screen/availHeight/viewport 需要匹配，避免“JS 说 1920x1080，但远程画面像 1280 小窗口”。
5. Automation API 只能作为可信管理能力，不能暴露给 Project Mileage App；自动化执行不得把 URL query、selector、表单值、evaluate result、screenshot、console/network 明细回显到业务前端。
6. CloakBrowser 不判断订单、钱包、扣费、续期、权限和账号归属；这些事实源必须留在 Payload。

## 验收分级

### P0 阻塞

- `navigator.webdriver` 为 `true`。
- BrowserScan / Fingerprint bot detection 明确判定自动化、WebDriver、Playwright、Selenium。
- IP、WebRTC public IP、timezone、language、Accept-Language 明显不一致。
- WebRTC 泄漏容器内网、宿主内网、非出口 public IP 或真实代理外 IP。
- Browser kernel 与 User-Agent 主版本不一致。
- `navigator.buildID` 与当前 Firefox 二进制 BuildID 明显不一致。
- CDP JSON、DevTools browser endpoint 或 remote debugging port 对外可用。
- Project Mileage App 能绕过 Payload 直接拿到 viewer token、runtime service token、automation API 或 CloakBrowser diagnostics。

### P1 必须收口

- Canvas / WebGL / Audio / Fonts 显示平台归因与 UA 平台不一致。
- WebGL vendor/renderer 与 Windows Firefox 身份明显不匹配。
- screen / availHeight / viewport / devicePixelRatio 与 VNC 画面不一致。
- 同一 profile 重启后 canvas、webgl、audio、font、timezone、language、hardwareConcurrency 等稳定字段无故变化。
- 不同 seed 的 profile 指纹过度聚类，导致多账号看起来像同一设备批量复制。
- GeoIP 自动解析失败时静默产生错误 timezone/locale，而不是保持手动覆盖或给出低敏风险提示。

### P2 持续优化

- TLS/JA3、HTTP/2、Client Hints、permissions、media devices、storage quota、battery、sensor 等高级面。
- 站点行为层：鼠标轨迹、点击间隔、滚动节奏、输入节奏、页面停留时间。
- 多国家代理矩阵：US、JP、DE、SG 等出口下的语言、时区、货币、搜索地区一致性。
- Cookie warm-up、账号平台自然访问历史、登录前行为路径。

## 测试站点矩阵

| 站点 | 用途 | PASS 口径 | 自动化程度 | 优先级 |
| --- | --- | --- | --- | --- |
| BrowserScan `https://www.browserscan.net/browser-checker`、`/webrtc`、`/timezone`、`/bot-detection`、`/canvas` | 总览、bot、browser-checker、WebRTC、canvas、timezone | browser-checker 内核与 UA 一致；WebRTC 不泄漏 local IP；timezone 与 IP 一致；bot 页 WebDriver/CDP/Selenium/Headless 为 Normal | 高，可用 Automation API 抽取页面文本和内部 JS 检测结果 | P0 |
| BrowserLeaks `https://browserleaks.com/webrtc`、`/canvas`、`/webgl`、`/fonts`、`/ssl` | WebRTC、Canvas、WebGL、Fonts、Audio、TLS/JA3、Headers | 无 local IP/非出口 IP 泄漏；Canvas/WebGL/Fonts 平台归因不背离 Windows Firefox；TLS/HTTP 结果记录为参考 | 中，页面结构可抽取，但 TLS/字体细节需要人工复核 | P0/P1 |
| Pixelscan `https://pixelscan.net/fingerprint` | IP 与浏览器环境一致性 | IP、timezone、language、WebRTC、fingerprint consistency 全部正常 | 中，可能有反自动化/加载等待，建议保存截图和文本摘要 | P0/P1 |
| CreepJS `https://abrahamjuliot.github.io/creepjs/` | lie detection、headless/webdriver、跨 API 一致性 | trust/lie 指标无严重红灯；webdriver/headless/automation 不暴露；平台归因一致 | 中，计算慢且 UI 动态多，适合截图+关键文本抽取 | P1 |
| IPhey `https://iphey.com/` / `https://iphey.com/leaks` | Browser/IP/hardware/software/leak 总览 | browser、location、IP、hardware、software 不出现高风险不一致 | 中，适合人工截图确认最终颜色和风险标签 | P1 |
| Fingerprint demo `https://demo.fingerprint.com/web-scraping` | 商业 bot detection 参考 | 不被直接归类为 bad bot / automation；结果只作外部参考 | 中，第三方商业判断可能变化，作为趋势参考 | P1 |
| PrintLeaks `https://www.printleaks.com/` | Canvas/WebGL/WebRTC/UA/permissions/storage 综合参考 | 无 WebRTC 泄漏；核心平台归因一致 | 中，适合截图+文本摘要 | P1 |
| EFF Cover Your Tracks `https://coveryourtracks.eff.org/` | tracker/fingerprint uniqueness 参考 | 只作参考，不用“unique/non-unique”单项定生死；重点看明显追踪/泄漏项 | 低，交互式测试更适合人工验收 | P2 |
| AmIUnique `https://amiunique.org/` | 指纹稳定性和唯一性参考 | 同 seed 重启稳定；不同 seed 有合理差异；不追求完全不唯一 | 低，长期统计意义大于单次结果 | P2 |
| SannySoft `https://bot.sannysoft.com/`、Are You Headless `https://arh.antoinevastel.com/bots/areyouheadless` | WebDriver/headless/automation 交叉检查 | 不显示 webdriver/headless 明确失败 | 中，Chrome 向站点只作辅助，不替代 Firefox 矩阵 | P1/P2 |

## 当前实测结果

测试环境：

- 镜像：`invisible-browser-manager:fingerprint-webgl-native-fix`
- 容器：`cloakbrowser-fingerprint-webgl-native-fix`
- 服务地址：`http://127.0.0.1:18090`
- profile：`27a6a5c2-2704-4918-b131-1e0096ed16c3`
- page：`02704940-d844-4399-a67c-9991cbe77917`
- profile 配置：无 proxy，`geoip=true`，`fingerprint_seed=24680`，Windows 10 / Firefox 身份，`1920x1080`，`hardwareConcurrency=8`
- 出口 GeoIP：`23.144.4.92`，US，`America/Los_Angeles`，`en-US`

已通过：

- 创建 profile 成功。
- `POST /api/profiles/{id}/launch` 成功，返回 `display=:100`、`vnc_ws_port=6100`、`automation_url=/api/profiles/{id}/automation`。
- REST Automation API 可用，`/api/profiles/{id}/automation/pages/{page_id}/goto` 和 `/evaluate` 可用。
- CDP 不作为公开能力暴露：历史验收中 `/api/profiles/{id}/cdp` 返回 404；`/json/version`、`/json/list`、`/devtools/browser` 不返回 CDP JSON。
- 基础 JS 指纹：
  - `navigator.userAgent = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0`
  - `navigator.appVersion = 5.0 (Windows)`
  - `navigator.platform = Win32`
  - `navigator.oscpu = Windows NT 10.0; Win64; x64`
  - `navigator.webdriver = false`
  - `navigator.language = en-US`
  - `Intl timezone = America/Los_Angeles`
  - `screen = 1920x1080`，`availHeight = 1032`，`devicePixelRatio = 1`
  - WebGL vendor/renderer：`Google Inc. (NVIDIA)` / `ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0), or similar`
- BrowserScan browser-checker：
  - 页面显示 `You are currently using Firefox 149`。
  - 页面显示 `Your browser version and User Agent match`。
  - 内部检测 `detected.version=149`、`reportVersion=149`、`liedCSS=false`、`liedJS=false`、`liedWindow=false`。
- BrowserScan WebRTC：
  - 页面显示 `WebRTC Leak Test: No Public IP Leak`。
  - 多个 STUN 项 `Local IP: -`。
  - 已返回的 STUN public IP 为 `23.144.4.92 (USA)`。
  - 个别 STUN 项在 5 秒等待内未返回 public IP，但未出现 local IP 或非出口 IP。
- BrowserScan timezone：
  - IP timezone、JS Date、Intl timezone 均为 `America/Los_Angeles`。
  - offset 均为 `-420 minutes`，locale 为 `en-US`。
- BrowserScan bot-detection：
  - WebDriver、WebDriver Advance、Selenium、NightmareJS、PhantomJS、Headless Chrome、CDP、Dev Tool 均为 `Normal`。
  - `navigator.webdriver=false`。

## 最近已完成修复

### WebRTC local IP suppression

问题：

- BrowserScan WebRTC 页在未修复前显示 Docker local IP：`172.17.0.x`。

根因：

- 本仓调用 `InvisiblePlaywright` 时未传 `extra_prefs`，底层默认 `media.peerconnection.ice.no_host=false`，host candidate 仍可暴露容器内网地址。

修复：

- `backend/browser_manager.py` 新增 `WEBRTC_LOCAL_IP_SUPPRESSION_PREFS`。
- `_build_invisible_kwargs()` 固定传入：
  - `media.peerconnection.ice.no_host=true`
  - `media.peerconnection.ice.default_address_only=true`
  - `media.peerconnection.ice.obfuscate_host_addresses=false`
  - `media.peerconnection.ice.disableIPv6=true`

验证：

- 单元测试覆盖 `_build_invisible_kwargs()` 必须传 WebRTC host candidate suppression prefs。
- Docker 镜像实测 BrowserScan WebRTC 不再显示 `172.*` local IP。

### Managed Firefox identity alignment

问题：

- BrowserScan browser-checker 报 Firefox 149/150 不一致。
- 进一步调用 BrowserScan 内部检测函数确认：CSS/window/JS 三路特征检测为 `149`，UA 却声称 `Firefox 150`。
- `navigator.buildID` 曾显示旧值 `20181001000000`，而当前二进制 `application.ini` 是 `BuildID=20260521160037`。

修复：

- `_build_invisible_kwargs()` 统一传入 `MANAGED_FIREFOX_IDENTITY_PREFS`，把对外 UA 固定为 `Firefox/149.0`，与 BrowserScan 可检测内核面一致。
- `_browser_init_script()` 读取当前 `invisible_playwright` 二进制目录的 `application.ini`，把 `Navigator.prototype.buildID` 对齐到二进制真实 BuildID。
- 不用 UA 硬说 Firefox 150；长期升级目标是把底层 patched Firefox 的 CSS/window/JS 可检测面真正升级到新版后，再提升 UA。

验证：

- BrowserScan browser-checker 显示 `Your browser version and User Agent match`。
- 内部检测 `version=149`、`reportVersion=149`、`liedCSS=false`、`liedJS=false`、`liedWindow=false`。

### Navigator language / Accept-Language alignment

问题：

- P0 验收要求 IP、timezone、language 和 Accept-Language 不能明显不一致。
- 启动时 HTTP `Accept-Language` 会派生基础语言回退，例如 `en-US,en;q=0.9`，但页面 init script 之前只把 `navigator.languages` 固定成单项 `["en-US"]`。
- 这不一定直接造成所有检测站红灯，但会让 BrowserScan / Pixelscan / IPhey 等语言一致性结果缺少自动 guardrail。

修复：

- `backend/browser_manager.py` 新增 `_navigator_languages()`，统一从 profile locale 生成 JS 语言列表。
- `_accept_language_header()` 和 `_browser_init_script()` 共用同一语言派生逻辑。
- 对 `en-US` 这类区域 locale，HTTP header 为 `en-US,en;q=0.9`，页面端 `navigator.language=en-US`、`navigator.languages=["en-US","en"]`。
- 对 `ja` 这类单项 locale，header 和 `navigator.languages` 都保持单项，避免重复。

验证：

- 单元测试覆盖 init script 必须包含与 `Accept-Language` 回退一致的 `navigator.languages`。
- 该项只是自动化边界补强；BrowserScan `Language mismatch`、Pixelscan/IPhey language consistency 仍需真实浏览器/检测站复验后才能标记完成。

### WebGL renderer consistency

问题：

- 基础 JS 指纹曾显示 WebGL vendor 为 `Google Inc. (NVIDIA)`，但 renderer 为 `Generic Renderer`。
- 这属于 P1：NVIDIA vendor + Generic renderer 与 Windows Firefox/ANGLE 身份不一致。

修复：

- `_coherent_webgl_renderer_override()` 对 NVIDIA/GeForce profile 输出 Firefox sanitize 后的稳定桶：`ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0), or similar`。
- 启动前通过 `_with_coherent_webgl_identity()` 改写传给 `invisible_playwright` 的 profile renderer，让底层 Firefox pref 自己输出一致的 WebGL 身份；不在页面层覆盖 `WebGLRenderingContext.prototype.getParameter()`，避免函数 native 形态被破坏。
- 该补丁只修正 renderer 明显不一致，不读取 secret，不接 Project Mileage DTO。

验证：

- 新 profile 中 WebGL vendor/renderer 为 `Google Inc. (NVIDIA)` / `ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0), or similar`，且 `Function.prototype.toString.call(gl.getParameter)` 仍显示 native code。

## 下一步顺序

1. 把 BrowserScan 分项验收自动化成脚本：创建临时 profile、启动、跑 browser-checker/webrtc/timezone/bot-detection/canvas，保存低敏 JSON 摘要和截图。
2. 扩展到 BrowserLeaks、Pixelscan、CreepJS、IPhey、Fingerprint demo、PrintLeaks。
3. 增加稳定性验收：同一 seed 停止/重启后关键 hash 不变，不同 seed 关键 hash 有合理差异。
4. 增加多出口验收：无 proxy、US proxy、JP proxy、DE proxy。
5. 长期升级底层 patched Firefox：当 CSS/window/JS 可检测面真实达到新版本，再把 `MANAGED_FIREFOX_USER_AGENT` 从 149 提升到对应版本。

## Project Mileage 边界

- 这些检测和修复只属于 CloakBrowser 本仓。
- 不修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。
- App 不能直连 CloakBrowser runtime、automation、diagnostics 或未来 fingerprint QA API。
- 如果未来 Project Mileage 需要展示“远程账号环境健康 / 指纹验收状态”，必须由 Payload 输出低敏 DTO，例如 `fingerprintHealth: pass|warning|fail` 和固定 reason code；不能返回检测页面截图、cookie、local storage、真实 proxy URL、viewer token、runtime service token 或 automation payload。
