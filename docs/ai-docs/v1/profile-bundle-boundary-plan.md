# Profile Bundle 边界与分阶段方案

## 目标

为后续完整 profile bundle 导入导出建立安全边界。bundle 目标是帮助可信本地管理侧迁移 profile 配置、cookie、local storage 和必要元数据，但不能把浏览器运行态、Project Mileage 业务事实、凭证或审计事实混进可复制包。

本文件只定义边界和后续切片，不代表已经实现 profile dir 打包 API。

## 当前事实

- profile 创建时，`backend/database.py:create_profile()` 会把 `user_data_dir` 固定生成为 `/data/profiles/{profile_id}`。
- `create_profile()` 当前只写 DB 记录，profile 目录通常由后续浏览器启动流程创建和写入。
- profile 启动时，`backend/browser_manager.py:_build_invisible_kwargs()` 会把 `profile["user_data_dir"]` 作为 invisible_playwright 的 `profile_dir`。
- profile 启动前，`backend/browser_manager.py:_clean_firefox_startup_state()` 只清理 Firefox lock 和 session restore 文件，不触碰站点数据。
- profile 删除时，`backend/main.py:delete_profile()` 会先删 DB，再删除 `user_data_dir` 目录。
- 当前已有安全能力：
  - profile config export 默认脱敏 proxy password，只有 `include_sensitive: true` 才包含完整 proxy。
  - profile config import 只导入白名单配置字段，不导入 cookie/local storage/profile dir/runtime/viewer/automation/Project Mileage 字段。
  - running profile cookie import/export 已支持 Cookie JSON v1 和 Netscape 格式，导出必须显式确认，audit 只写低敏计数。

## Bundle 格式建议

建议先定义 `cloakbrowser.profile-bundle.v1` manifest，作为后续 API 和文件格式的唯一入口。

建议最小结构：

```json
{
  "format": "cloakbrowser.profile-bundle.v1",
  "schema_version": 1,
  "exported_at": "2026-05-27T00:00:00+00:00",
  "profile": {
    "config": {},
    "tags": []
  },
  "cookies": {
    "format": "cloakbrowser.cookie-json.v1",
    "schema_version": 1,
    "cookies": []
  },
  "local_storage": {
    "included": false,
    "entries": []
  },
  "profile_dir": {
    "included": false,
    "archive": null
  },
  "metadata": {
    "source_profile_id": "profile-id",
    "fingerprint_seed_included": true,
    "sensitive_included": false
  }
}
```

## 默认允许包含

默认 bundle 只允许包含低风险、可审计、可测试的内容：

- profile config 白名单字段：
  - `name`
  - `fingerprint_seed`
  - `proxy` 的脱敏形式
  - `timezone`
  - `locale`
  - `platform`
  - `user_agent`
  - `screen_width`
  - `screen_height`
  - `gpu_vendor`
  - `gpu_renderer`
  - `hardware_concurrency`
  - `humanize`
  - `human_preset`
  - `headless`
  - `geoip`
  - `clipboard_sync`
  - `auto_launch`
  - `color_scheme`
  - `launch_args`
  - `notes`
  - `tags`
- cookie summary 低敏统计。
- manifest metadata：
  - `format`
  - `schema_version`
  - `exported_at`
  - `app_name`
  - `app_version`
  - `source_profile_id`
  - `source_profile_name`
  - 各类 include flag。
- 低敏统计：
  - cookie 数。
  - local storage origin 数。
  - profile dir 文件数量和总字节数。
  - 排除文件数量。

## 默认禁止包含

bundle 默认不能包含以下内容：

- `user_data_dir` 绝对路径。
- Firefox profile dir 原始目录。
- cookie 明文。
- local storage 明文。
- IndexedDB、Cache Storage、Service Worker cache、session restore、history、downloads、form history、cert/key DB 等浏览器内部数据。
- runtime session、viewer token、viewer token hash、VNC URL、VNC ticket、automation task、lease owner。
- Project Mileage 钱包、订单、支付、扣费、权限、续期、远程工作台 session 或审计事实。
- `.env`、数据库 dump、secret、token、proxy password。
- 原始浏览器历史、表单自动填充、站点权限、设备绑定标识、下载记录。

## 显式敏感导出

后续如实现敏感 bundle 导出，必须单独显式确认，不得复用普通 export 默认行为。

建议将敏感选项拆开：

- `include_sensitive_proxy: true`
- `include_cookies: true`
- `include_local_storage: true`
- `include_profile_dir_archive: true`

每个选项都要：

- 使用 JSON boolean，不接受字符串或数字宽松转换。
- 只面向可信本地管理 API。
- 成功写低敏 audit。
- 响应或 audit 不回显 cookie/local storage/profile dir 文件名细节、URL query、fragment、token 或 secret。
- 文档明确导出文件不得提交到 git。

## 停止态 profile dir 风险

停止态 profile dir 不是简单 JSON 数据源，不能在当前阶段直接读写：

- Firefox cookie 存储通常在 SQLite 文件中，直接写入容易破坏一致性。
- local storage、IndexedDB、cache、service worker 数据结构复杂，直接打包可能泄露账号 token、站点缓存或业务数据。
- session restore/history/form history 可能包含完整 URL、query、fragment 和用户输入。
- lock/session restore 文件需要排除，否则导入后可能影响启动。
- 不同 Firefox/invisible_playwright 版本的数据格式可能变化。

因此停止态 profile dir 能力必须先做只读评估和允许/拒绝清单，不能直接实现“整目录 zip 导出/导入”。

如果未来实现完整 profile dir bundle：

- 导出完整 profile dir 必须要求 profile 已停止；running profile 只能导出 config 或 running context cookie。
- 导入完整 profile dir 不能覆盖既有 `user_data_dir`，必须创建新 profile、新 UUID 和新目录，避免跨 profile 污染。
- 导入前必须拒绝路径穿越、绝对路径、symlink、设备文件和隐藏高风险文件。

## 后续最小切片

### 切片 1：bundle manifest 格式层

- 新增后端格式 helper，例如 `backend/profile_bundle.py`。
- 只构造 manifest，不读取 profile dir，不包含 cookie/local storage 明文。
- 复用 `ProfileConfigExport` 字段。
- 测试覆盖：
  - `format/schema_version` 固定。
  - 默认 proxy 脱敏。
  - 默认不包含 `user_data_dir`、cookie、local storage、runtime、viewer、automation、Project Mileage 字段。

### 切片 2：bundle config export API

- 新增可信本地管理 API，例如 `POST /api/profiles/{profile_id}/bundle/export`.
- 默认只返回 manifest 和 config，不返回文件 archive。
- 显式敏感 proxy 仍沿用单独 boolean。
- 成功可写低敏 audit，但 audit 不包含 bundle 内容。

### 切片 3：bundle config import API

- 从 manifest 导入 profile config。
- 复用当前 profile config import 白名单。
- 忽略调用方附带的 runtime/viewer/automation/Project Mileage 字段。
- 不导入 cookie/local storage/profile dir。

### 切片 4：running profile cookie bundle

- 只复用 running browser context 的 Cookie JSON v1。
- 导出仍必须显式确认。
- 导入仍只允许运行中 profile。
- 不读写停止态 Firefox profile dir。

### 切片 5：local storage 只读评估

- 先评估 Playwright context/page 是否可在 running profile 里低风险导出当前页面 origin 的 local storage。
- 不做跨 origin 扫描。
- 不写 audit 明文。
- 不实现 stopped profile dir 读取。

### 切片 6：profile dir archive 评估

- 只做文档和只读文件清单评估。
- 必须先定义 allowlist/denylist。
- 必须排除 lock、session restore、history、downloads、cache、service worker、cert/key DB、SQLite WAL/SHM 等高风险文件。
- 未完成评估前，不实现 archive API。
- 评估文档：`docs/ai-docs/v1/profile-dir-archive-evaluation.md`。
- 评估完成后仍不直接代表 archive API 可以实现；实现前必须再按测试先行补导出/导入失败测试。

## Project Mileage 边界

- Project Mileage App 不能直接调用 CloakBrowser bundle/cookie/runtime API。
- Payload 仍是账号、订单、钱包、权限、续期、viewer token 和审计事实源。
- 若未来远程账号工作台需要 profile bundle 相关能力，必须先提交跨仓 Proposal，由主 agent/Jeff 确认 Payload 安全 DTO 和权限边界。
- 本文件不要求修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。

## 建议验证命令

后续实现每个切片时至少运行：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_api.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
git diff --check
```

如果只修改后端格式层，可先运行对应新增测试和：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py backend/tests/test_api.py -q
git diff --check
```

后续新增 bundle helper 时建议补充：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py -q
```
