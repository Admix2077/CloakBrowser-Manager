# 指纹一致性 QA 计划

## 目标

把 CloakBrowser 的验收目标从“看起来能启动”升级为“多个公开检测站点下核心指纹一致、没有明显自动化和环境泄漏”。

这里的“100% 完美伪装”在工程上定义为：在指定测试矩阵中全部达到 PASS，且没有 P0/P1 红灯。不能承诺对所有未知网站永久不可检测；每个检测站更新规则后都要重新跑矩阵。

## 验收分级

### P0 阻塞

- `navigator.webdriver` 为 `true`。
- BrowserScan / Fingerprint bot detection 明确判定自动化、WebDriver、Playwright、Selenium。
- IP、WebRTC public IP、timezone、language、Accept-Language 明显不一致。
- WebRTC 泄漏容器内网、宿主内网、非出口 public IP 或真实代理外 IP。
- Browser kernel 与 User-Agent 主版本不一致。
- CDP JSON、DevTools browser endpoint 或 remote debugging port 对外可用。

### P1 必须收口

- Canvas / WebGL / Audio / Fonts 显示平台归因与 UA 平台不一致。
- WebGL vendor/renderer 与 Windows Firefox 身份明显不匹配。
- screen / availHeight / viewport / devicePixelRatio 与 VNC 画面不一致。
- 同一 profile 重启后 canvas、webgl、audio、font、timezone、language、hardwareConcurrency 等稳定字段无故变化。
- 不同 seed 的 profile 指纹过度聚类，导致多账号看起来像同一设备批量复制。

### P2 持续优化

- TLS/JA3、HTTP/2、Client Hints、permissions、media devices、storage quota、battery、sensor 等高级面。
- 站点行为层：鼠标轨迹、点击间隔、滚动节奏、输入节奏、页面停留时间。
- 多国家代理矩阵：US、JP、DE、SG 等出口下的语言、时区、货币、搜索地区一致性。

## 测试站点矩阵

| 站点 | 用途 | PASS 口径 |
| --- | --- | --- |
| BrowserScan `https://www.browserscan.net/` | 总览、bot、browser-checker、WebRTC、canvas、timezone | 首页无明显红灯；bot 页无 bot detected；browser-checker 内核与 UA 一致；WebRTC 不泄漏 local IP；timezone 与 IP 一致 |
| BrowserLeaks `https://browserleaks.com/` / `https://browserleaks.io/fingerprints` | WebRTC、Canvas、WebGL、Fonts、Audio、TLS/JA3、Headers | 无 local IP/非出口 IP 泄漏；Canvas/WebGL/Fonts 平台归因不背离 Windows Firefox |
| CreepJS `https://abrahamjuliot.github.io/creepjs/` | lie detection、headless/webdriver、跨 API 一致性 | trust/lie 指标无严重红灯；webdriver/headless/automation 不暴露 |
| Pixelscan `https://pixelscan.net/fingerprint` | IP 与浏览器环境一致性 | IP、timezone、language、WebRTC、fingerprint consistency 全部正常 |
| IPhey `https://iphey.com/` / `https://iphey.com/leaks` | Browser/IP/hardware/software/leak 总览 | browser、location、IP、hardware、software 不出现高风险不一致 |
| EFF Cover Your Tracks `https://coveryourtracks.eff.org/` | tracker/fingerprint uniqueness 参考 | 只作参考，不用“unique/non-unique”单项定生死；重点看明显追踪/泄漏项 |
| AmIUnique `https://amiunique.org/` | 指纹稳定性和唯一性参考 | 同 seed 重启稳定；不同 seed 有合理差异；不追求完全不唯一 |
| Fingerprint demo `https://demo.fingerprint.com/web-scraping` | 商业 bot detection 参考 | 不被直接归类为 bad bot / automation |
| PrintLeaks `https://www.printleaks.com/` | Canvas/WebGL/WebRTC/UA/permissions/storage 综合参考 | 无 WebRTC 泄漏；核心平台归因一致 |

## 当前实测结果

测试环境：

- 镜像：`invisible-browser-manager:fingerprint-webrtc-fix`
- 容器：临时 `127.0.0.1:18086`
- profile：无 proxy，`geoip=true`，`fingerprint_seed=24680`，Windows 10 / Firefox 身份，`1920x1080`，`hardwareConcurrency=8`
- 出口 GeoIP：`23.144.4.92`，US，`America/Los_Angeles`，`en-US`

已通过：

- 创建 profile 成功。
- `POST /api/profiles/{id}/launch` 成功，返回 `display=:100`、`vnc_ws_port=6100`、`automation_url=/api/profiles/{id}/automation`。
- REST Automation API 可用，`/api/profiles/{id}/automation`、pages、goto、evaluate、screenshot 均可用。
- CDP 不作为公开能力暴露：`/api/profiles/{id}/cdp` 返回 404；`/json/version`、`/json/list`、`/devtools/browser` 不返回 CDP JSON。
- 基础 JS 指纹：
  - `navigator.userAgent = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0.1`
  - `navigator.platform = Win32`
  - `navigator.webdriver = false`
  - `navigator.language = en-US`
  - `Intl timezone = America/Los_Angeles`
  - `screen = 1920x1080`
  - WebGL 显示 NVIDIA Windows ANGLE 形态
- BrowserScan WebRTC 修复后显示：
  - `WebRTC Leak Test: No Public IP Leak 23.144.4.92`
  - 多个 STUN 项 `Local IP: -`
  - 多个 STUN 项 `Public IP: 23.144.4.92 (USA)`

当前 P0 blocker：

- BrowserScan browser-checker 仍显示：实际检测 `Firefox 149`，UA 声称 `Firefox 150`，即 browser kernel 与 User-Agent 主版本不一致。

## 最近已完成修复

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
- Docker 镜像 `invisible-browser-manager:fingerprint-webrtc-fix` 实测 BrowserScan WebRTC 不再显示 `172.*` local IP。

## 下一步顺序

1. 修 `Firefox 149` vs `Firefox 150` kernel/UA 不一致。
   - 先确认 BrowserScan 检测依据：特性检测、BuildID、UA override、`navigator.userAgentData` 不存在性、CSS/JS API 特征还是底层 patched binary 实际特征。
   - 不盲目把 UA 降到 149；如果底层二进制实际特征仍被识别为 149，优先让 UA 与真实可检测内核一致，或者升级 patched Firefox/指纹常量到一致版本。
2. 把 BrowserScan 分项验收自动化成脚本：
   - 创建临时 profile。
   - 启动。
   - 跑 BrowserScan browser-checker、webrtc、timezone、canvas、bot-detection。
   - 保存低敏 JSON 摘要和截图。
   - 输出 PASS/FAIL。
3. 扩展到 BrowserLeaks、CreepJS、Pixelscan、IPhey、EFF、AmIUnique、Fingerprint demo。
4. 增加稳定性验收：
   - 同一 seed 停止/重启后关键 hash 不变。
   - 不同 seed 关键 hash 有合理差异。
5. 增加多出口验收：
   - 无 proxy。
   - US proxy。
   - JP proxy。
   - DE proxy。

## Project Mileage 边界

- 这些检测和修复只属于 CloakBrowser 本仓。
- 不修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。
- App 不能直连 CloakBrowser runtime、automation、diagnostics 或未来 fingerprint QA API。
- 如果未来 Project Mileage 需要展示“远程账号环境健康 / 指纹验收状态”，必须由 Payload 输出低敏 DTO，例如 `fingerprintHealth: pass|warning|fail` 和固定 reason code；不能返回检测页面截图、cookie、local storage、真实 proxy URL、viewer token、runtime service token 或 automation payload。
