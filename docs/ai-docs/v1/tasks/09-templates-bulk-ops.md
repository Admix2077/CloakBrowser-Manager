# 09 模板、批量创建与批量运营

## 目标

实现成熟多账号运营需要的模板和批量能力，减少逐个创建 profile 的重复操作。

## 任务清单

### Profile Template

- [x] 新增 profile_templates 表。
- [x] 支持保存模板：
  - platform。
  - screen。
  - GPU。
  - hardware concurrency。
  - color scheme。
  - humanize。
  - launch args。
  - geoip。
- [x] 创建 profile 时可选择模板。
- [x] 模板变更不自动修改已有 profile，避免意外批量污染。

### Proxy Template

- [x] 支持 proxy provider preset。
  - [x] 后端事实源 CRUD API。
  - [x] 前端接入/选择（Proxy CSV import preset 默认值）。
  - [x] 后端与国家/标签选择、随机分配策略联动。
  - [x] 前端完整管理入口。
- [x] 支持按国家/标签选择 proxy。
  - [x] 后端候选过滤 API。
  - [x] 前端运营入口。
- [x] 支持随机分配策略。
  - [x] 后端 random assignment API。
  - [x] 前端运营入口。

### 批量创建

- [x] 支持 CSV 粘贴导入 profile（后端 API；前端提交导入按钮另起闭环）。
- [x] 支持字段（CSV preview/import 后端契约）：
  - name。
  - proxy。
  - tags。
  - notes。
  - template。
  - platform。
  - locale。
  - timezone。
- [x] 导入前预览（后端 API；前端导入 UI 另起闭环）。
- [x] 无效行标红（Profile CSV preview 前端弹窗）。
- [x] 部分导入成功，失败行保留原因（后端 API）。

### 批量运营

- [ ] 批量启动。
- [ ] 批量停止。
- [ ] 批量 health check。
- [ ] 批量刷新 GeoIP。
- [ ] 批量设置 tag。
- [ ] 批量设置 proxy。
- [x] 批量导出 profile config（后端 API + 前端下载入口）。
- [ ] 批量删除必须二次确认。

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [x] 批量导入不会因为一行失败而全部失败（后端 API）。
- [ ] 批量启动有并发限制。
- [ ] 批量删除需要确认。
- [x] 模板不会静默改写已有 profile。

## 2026-05-26 Profile Template 后端基础 CRUD 小闭环

背景：

- 当前 09 模块先从低风险、可测试的 Profile Template 事实源切入。
- 本轮只实现后端 `profile_templates` 表和 CRUD API，不做前端模板选择，不改变 profile 创建流程，不触碰 Project Mileage。

已完成：

- [x] `backend/database.py`
  - 新增 `profile_templates` 表。
  - 新增 `create_profile_template` / `list_profile_templates` / `get_profile_template` / `update_profile_template` / `delete_profile_template`。
  - `launch_args` 采用与 profile 一致的 JSON roundtrip。
- [x] `backend/models.py`
  - 新增 `ProfileTemplateCreate` / `ProfileTemplateUpdate` / `ProfileTemplateResponse`。
  - 10 审计安全阶段已补 `ProfileTemplateDeleteRequest`；删除 template 必须传 JSON boolean `confirm_delete: true`。
  - 字段覆盖 platform、screen、GPU、hardware concurrency、color scheme、humanize、human preset、launch args、geoip。
- [x] `backend/main.py`
  - 新增 `/api/profile-templates` CRUD：
    - `GET /api/profile-templates`
    - `POST /api/profile-templates`
    - `GET /api/profile-templates/{template_id}`
    - `PUT /api/profile-templates/{template_id}`
    - `DELETE /api/profile-templates/{template_id}`
  - 10 审计安全阶段已补删除确认：缺失、`false` 或字符串 `"true"` 返回固定 422，未确认不删除 template。
- [x] `backend/tests/test_templates.py`
  - 覆盖表创建、DB CRUD、API CRUD、not found、模板更新不静默改写已有 profile。
  - 10 审计安全阶段已补 API 删除确认测试。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 5 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 237 passed
```

未覆盖范围：

- 前端模板列表/保存入口。
- 创建 profile 时选择模板并应用字段。
- CSV 批量导入、批量启动/停止/GeoIP/tag/proxy/export/delete。

## 2026-05-26 Profile 创建应用模板后端契约小闭环

背景：

- 在 `profile_templates` 后端事实源基础上，继续推进 `创建 profile 时可选择模板`。
- 本轮只做后端契约：`POST /api/profiles` 可接收 `template_id` 并复制模板字段。
- 前端创建页模板下拉和保存模板入口另起小闭环，因此顶部 `创建 profile 时可选择模板` 暂不勾选。

已完成：

- [x] `backend/models.py`
  - `ProfileCreate` 新增可选 `template_id`。
- [x] `backend/main.py`
  - 创建 profile 时如果传入 `template_id`，先读取模板。
  - 复制 platform、screen、GPU、hardware concurrency、color scheme、humanize、human preset、launch args、geoip。
  - 用户显式传入的 profile 字段覆盖模板字段。
  - 缺失模板返回 `404 Profile template not found`，不会静默创建默认 profile。
- [x] `backend/tests/test_templates.py`
  - 覆盖从模板创建 profile。
  - 覆盖显式字段覆盖模板字段。
  - 覆盖 missing template 返回 404。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 红灯：2 failed, 6 passed
# 失败点：template_id 被忽略，missing template 仍创建成功

. .venv/bin/activate && python -m pytest backend/tests/test_templates.py -q
# 8 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 240 passed
```

未覆盖范围：

- 前端创建 profile 时选择模板。
- 前端 API 类型暴露 `template_id`。
- 保存当前 profile 为模板。

## 2026-05-26 Profile 创建页模板选择小闭环

背景：

- 在后端 `template_id` 契约完成后，补齐 Profile 创建页的模板选择入口。
- 本轮只处理创建 Profile 表单，不做编辑页模板切换，不做保存当前 profile 为模板，不做 CSV 批量导入。

已完成：

- [x] `frontend/src/lib/api.ts`
  - 新增 `ProfileTemplate` / `ProfileTemplateCreateData` / `ProfileTemplateUpdateData`。
  - `ProfileCreateData` 新增可选 `template_id`。
  - 新增 profile template CRUD API client。
- [x] `frontend/src/App.tsx`
  - 启动后读取 `/api/profile-templates`。
  - 创建 Profile 时把模板列表传给 `ProfileForm`。
- [x] `frontend/src/components/ProfileForm.tsx`
  - 创建模式下显示 `Profile template` 下拉。
  - 选择模板后把 platform、screen、GPU、hardware concurrency、color scheme、humanize、human preset、launch args、geoip 应用到表单。
  - 编辑模式不显示模板选择，避免误把模板变更套到既有 profile。
- [x] `frontend/src/App.test.tsx`
  - 覆盖创建页选择模板后提交 `template_id` 和模板字段。

验证：

```bash
cd frontend && npm test -- --run src/App.test.tsx -t "applies a profile template"
# 红灯：1 failed
# 失败点：创建页没有 Profile template 下拉

cd frontend && npm test -- --run src/App.test.tsx -t "applies a profile template"
# 1 passed, 23 skipped

cd frontend && npm test -- --run
# 13 passed, 167 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`，让服务加载新的后端和 `frontend/dist`。
- 通过 API 创建 QA 模板 `Mac warmup`。
- 桌面 `1440x960`：
  - 创建页可见 `Profile template` 下拉。
  - 选择 `Mac warmup` 后，Device 页显示 `1440 × 900`、hardware concurrency `8`、GPU `Apple / Apple M2`。
  - Behavior 页显示 humanize checked、color scheme `light`。
  - Advanced 页显示 `--private-window`。
  - 点击 Create 后，`/api/profiles` 返回 `Template QA Profile`，字段为 `macos / 1440x900 / Apple M2 / humanize=true / --private-window / geoip=false`。
  - `scrollWidth=1440`、`clientWidth=1440`。
- 移动 `390x844`：
  - 创建页模板下拉可见，页面未横向撑破。
- Playwright MCP console：0 errors、0 warnings。
- 截图：
  - `/tmp/cloakbrowser-template-form-screens/desktop-template-select.png`
  - `/tmp/cloakbrowser-template-form-screens/desktop-template-applied.png`
  - `/tmp/cloakbrowser-template-form-screens/mobile-template-select.png`

未覆盖范围：

- 前端保存当前 profile 为模板。
- 模板列表管理页面。
- CSV 批量创建中的 `template` 字段。

## 2026-05-26 Profile CSV 导入预览后端 API 小闭环

背景：

- 在 Profile Template 事实源和创建页模板选择完成后，继续推进批量创建的低风险前置能力。
- 本轮只做 `POST /api/profiles/import/preview`，用于 CSV 粘贴导入前的后端解析、模板应用和行级校验。
- 本轮不写入 `profiles`，不做前端导入 UI，不做真正批量创建，不启动浏览器。

已完成：

- [x] `backend/tests/test_bulk.py`
  - 先写红灯测试：CSV preview endpoint 不存在，返回 `405`。
  - 覆盖模板按名称/id 解析、显式 CSV 字段覆盖模板字段、proxy 响应脱敏、tags 解析、预览不写库。
  - 覆盖混合成功/失败：一行失败不会阻断其他有效行。
  - 覆盖空 CSV 和无可用 header 返回 `422`。
- [x] `backend/models.py`
  - 新增 `ProfileImportPreviewRequest` / `ProfileImportPreviewProfile` / `ProfileImportPreviewRow` / `ProfileImportPreviewResponse`。
- [x] `backend/profile_import.py`
  - 新增 CSV 解析与 preview 纯逻辑。
  - 支持字段：`name`、`proxy`、`tags`、`notes`、`template`、`platform`、`locale`、`timezone`。
  - 额外兼容模板相关字段：`screen_width`、`screen_height`、`gpu_vendor`、`gpu_renderer`、`hardware_concurrency`、`color_scheme`、`humanize`、`human_preset`、`launch_args`、`geoip`。
  - 抽出 `apply_profile_template_fields`，复用到普通 profile 创建，避免模板覆盖规则分叉。
- [x] `backend/main.py`
  - 新增 `POST /api/profiles/import/preview`。
  - 普通 `POST /api/profiles` 改为复用模板应用 helper，行为保持与既有测试一致。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 红灯：3 failed, 1 passed
# 失败点：/api/profiles/import/preview 尚不存在，返回 405

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 4 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
# 12 passed
```

未覆盖范围：

- 前端 CSV 粘贴导入 UI。
- 无效行前端标红。
- 真正批量创建 profile 与部分成功写入。
- 批量启动/停止/health check/GeoIP/tag/proxy/export/delete。

## 2026-05-26 Profile Config 批量导出后端 API 小闭环

背景：

- 在 CSV 批量导入闭环后，继续推进低风险、只读的批量运营能力。
- 本轮只做后端 `POST /api/profiles/export`，用于导出可重建 profile 的 config JSON；不写服务端文件，不做前端下载入口，不启动浏览器。

已完成：

- [x] `backend/tests/test_bulk.py`
  - 先写红灯测试：`/api/profiles/export` 尚不存在，返回 `405`。
  - 覆盖多 profile 按输入顺序返回部分成功/失败。
  - 覆盖 missing profile 不阻断其他导出项。
  - 覆盖成功 config 包含可重建字段：name、fingerprint_seed、proxy、platform、screen、GPU、hardware concurrency、humanize、human preset、color scheme、launch args、notes、tags。
  - 覆盖成功 config 不包含运行态/本机路径字段：`status`、`automation_url`、`vnc_ws_port`、`user_data_dir`。
  - 覆盖空 `profile_ids` 返回 `422`。
- [x] `backend/models.py`
  - 新增 `ProfileExportRequest` / `ProfileConfigExport` / `ProfileExportResult` / `ProfileExportResponse`。
  - `ProfileConfigExport` 使用专用模型，不复用 `ProfileResponse`，避免导出运行态字段。
- [x] `backend/main.py`
  - 新增 `POST /api/profiles/export`。
  - 返回 `schema_version=1`、`total/exported/failed/results`。
  - 成功项返回 config；失败项只返回 `Profile not found`。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 红灯：2 failed, 6 passed
# 失败点：/api/profiles/export 尚不存在，返回 405

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 8 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
# 16 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 248 passed
```

未覆盖范围：

- 前端 `Export config` 下载入口已在后续小闭环补齐，见下一节。
- 批量启动/停止/health check/GeoIP/tag/proxy/delete。

## 2026-05-26 Profile Config 批量导出前端下载入口小闭环

背景：

- 后端 `POST /api/profiles/export` 已完成，本轮补齐 Profile 运营台批量栏里的只读下载入口。
- 只启用低风险 `Export config`；不解锁批量启动/停止/tag/delete 等高风险操作。
- 导出 JSON 只通过浏览器下载，不把完整 config 渲染到 DOM。

已完成：

- [x] `frontend/src/lib/api.ts`
  - 新增 `ProfileConfigExport` / `ProfileExportResult` / `ProfileExportResponse` 类型。
  - 新增 `api.exportProfiles(profileIds)`，请求体为 `{ profile_ids: [...] }`。
- [x] `frontend/src/hooks/useProfiles.ts`
  - 新增 `exportProfileConfigs(ids)`。
  - 对选中 id 去重，不修改 `profiles` state。
- [x] `frontend/src/components/BulkActionBar.tsx`
  - 在批量栏新增 `Export config` 按钮。
  - 导出中显示 `Exporting...`，并纳入 toolbar `aria-busy`。
  - 保持 Launch/Stop/Tag/Delete disabled。
- [x] `frontend/src/components/ProfileTable.tsx`
  - 从当前受控 selection 传递完整选中 profile ids，不依赖虚拟窗口 DOM。
- [x] `frontend/src/App.tsx`
  - 点击后调用导出 API，生成本地 JSON 下载文件 `cloakbrowser-profile-configs-*.json`。
  - 成功/部分失败使用现有 bulk feedback 展示摘要。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx
# 红灯：6 failed，缺少 api/hook/button/App 下载链路

cd frontend && npm test -- --run src/lib/api.test.ts src/hooks/useProfiles.test.ts src/components/ProfileTable.test.tsx src/App.test.tsx
# 4 passed, 114 passed

cd frontend && npm test -- --run
# 13 passed, 175 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`，当前进程 `1681096`。
- 桌面 `1440x960`：
  - 选中 `Alpha Warmup` 和 `Beta Running Candidate` 后，批量栏显示 `2 selected`。
  - `Check health` 保持可用，`Export config` 可用。
  - `Launch selected` / `Stop selected` / `Tag selected` / `Delete selected` 均保持 disabled。
  - 点击 `Export config` 触发 `POST /api/profiles/export`，请求体包含 2 个选中 profile id，响应 `exported=2/failed=0`。
  - 浏览器下载 `cloakbrowser-profile-configs-2026-05-26T13-15-52-514Z.json`。
  - bulk feedback 显示 `Exported 2 profile configs.`。
- 移动 `390x844`：
  - 批量栏、card selection、profile cards 保持可用。
  - `body.scrollWidth=390`、`documentElement.scrollWidth=390`，未横向撑破页面。
  - 表格/卡片语义和 Actions 入口未被导出按钮破坏。
- Playwright MCP console：导出交互后 0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-export-desktop.png`
  - `/home/jeff/code/cloakbrowser-export-mobile.png`

未覆盖范围：

- 批量启动/停止/health check/GeoIP/tag/proxy/delete。
  - 其中 bulk health check UI 已存在，但本轮未重新定义模块 09 checkbox 口径。

## 2026-05-26 Profile CSV 导入预览前端 UI 小闭环

背景：

- 在后端 `POST /api/profiles/import/preview` 完成后，补齐 Profile 运营台里的 CSV preview 入口。
- 本轮只做前端预览：粘贴 CSV、调用 preview API、展示 ready/blocked 行和错误原因。
- 本轮不做真正 profile 批量创建，不把 preview rows 合并进真实 profile table，不改虚拟滚动、bulk health check、Actions 列或移动端横向滚动语义。

已完成：

- [x] `frontend/src/lib/api.ts`
  - 新增 `ProfileImportPreviewProfile` / `ProfileImportPreviewRow` / `ProfileImportPreviewResponse` 类型。
  - 新增 `api.previewProfileImport(csvText)`。
- [x] `frontend/src/components/ProfileCsvPreviewDialog.tsx`
  - 新增 `Import profile CSV preview` 弹窗。
  - 支持粘贴 CSV、点击 `Preview CSV` 调用后端 preview API。
  - 展示 `total / ready / blocked` 计数和最多 60 行 preview。
  - 有效行显示 profile 摘要、platform、locale/timezone、proxy、tags。
  - 无效行以 amber 状态高亮并展示后端返回的行级 errors。
  - Preview 成功后将 textarea 中的 URL 凭证脱敏，避免截图和 UI 证据泄漏 proxy 密码。
- [x] `frontend/src/App.tsx`
  - Profile 顶栏新增 `Import CSV` 按钮，与 `New Profile` 并列。
  - 入口不放入 `ProfileTable`、`BulkActionBar` 或 row Actions，避免和 selection/bulk 状态耦合。
- [x] `frontend/src/lib/api.test.ts`
  - 覆盖 API client 调用 `/api/profiles/import/preview`。
- [x] `frontend/src/App.test.tsx`
  - 先写红灯测试：`Import CSV` 按钮不存在。
  - 覆盖打开弹窗、提交 preview、展示 ready/blocked 行、显示模板应用后的字段和错误原因。
  - 覆盖不调用 `create`，确认本轮只是 preview。
  - 覆盖 dialog 文本与 title 不泄漏 `user:hiddenpass` / `user:`。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "previewProfileImport"
# 红灯：1 failed
# 失败点：api.previewProfileImport is not a function

cd frontend && npm test -- --run src/lib/api.test.ts -t "previewProfileImport"
# 1 passed, 21 skipped

cd frontend && npm test -- --run src/App.test.tsx -t "previews profile CSV import"
# 红灯：1 failed
# 失败点：Profiles 顶栏没有 Import CSV 按钮

cd frontend && npm test -- --run src/App.test.tsx -t "previews profile CSV import"
# 中间红灯：textarea 展示原始 proxy 凭证

cd frontend && npm test -- --run src/App.test.tsx -t "previews profile CSV import"
# 1 passed, 24 skipped

cd frontend && npm test -- --run
# 13 passed, 169 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`，让服务加载新的后端和 `frontend/dist`。
- 通过 API 创建 QA 模板 `CSV QA Mac`。
- 桌面 `1440x960`：
  - Profile 顶栏可见 `Import CSV`，与 `New Profile` 并列。
  - 点击后打开 `Import profile CSV preview` 弹窗。
  - 粘贴 2 行 CSV 后点击 `Preview CSV`，返回 `2 total / 1 ready / 1 blocked`。
  - 有效行展示 `CSV QA Import`、`macos`、`ja-JP`、`Asia/Tokyo`、`asia/warmup`。
  - 无效行展示 `name is required`、`Template not found`、`platform must be one of...`，且没有出现真实导入按钮。
  - 页面正文不包含 `hiddenpass` 或 `user:`。
- 移动 `390x844`：
  - 弹窗可见，表格区域内部横向滚动。
  - `document.body.scrollWidth=390`、`document.body.clientWidth=390`，body 未被横向撑破。
- Playwright MCP console：当前交互后 0 errors、0 warnings。
- 截图：
  - `/tmp/cloakbrowser-profile-csv-preview-screens/desktop.png`
  - `/tmp/cloakbrowser-profile-csv-preview-screens/mobile.png`

未覆盖范围：

- 前端真正批量创建 profile 提交入口。
- 前端展示部分成功写入后的失败行保留原因。

## 2026-05-26 Profile CSV 批量创建后端 API 小闭环

背景：

- 在 CSV preview parser/validator 稳定后，继续推进真正批量创建的后端最小闭环。
- 本轮只做 `POST /api/profiles/import` 后端 API，不做前端提交导入按钮，不启动浏览器，不触碰 Project Mileage。

已完成：

- [x] `backend/tests/test_bulk.py`
  - 先写红灯测试：`/api/profiles/import` 尚不存在，返回 `405`。
  - 覆盖有效行写入 profile，无效行保留 `line_number/source/errors/profile:null`。
  - 覆盖一行失败不会阻断其他行创建。
  - 覆盖模板字段复制与 CSV 显式字段覆盖模板字段。
  - 覆盖 tags 写入后 `GET /api/profiles` 可读回。
  - 覆盖 headerless CSV 返回 `422` 且不写库。
- [x] `backend/profile_import.py`
  - 抽出 `parse_profile_csv_import`，preview 和 import 共用同一套 CSV parser/validator。
  - 新增 `profile_create_data_for_import`，创建前移除 `template_id`，避免传入 DB 层。
  - Preview 响应继续脱敏，import 内部保留 raw normalized create data，避免丢失 proxy 凭证。
- [x] `backend/models.py`
  - 新增 `ProfileImportResult` / `ProfileImportResponse`。
- [x] `backend/main.py`
  - 新增 `POST /api/profiles/import`。
  - 成功行调用 `db.create_profile`，不调用 `browser_mgr.launch`。
  - 成功行返回真实 `ProfileResponse`，失败行保留错误；只要 header 可解析，部分失败仍返回 `200`。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 红灯：2 failed, 4 passed
# 失败点：/api/profiles/import 尚不存在，返回 405

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py -q
# 6 passed

. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
# 14 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 246 passed
```

未覆盖范围：

- 前端 `Import valid rows` / `Create valid profiles` 提交入口。
- 导入后的前端刷新、成功/失败反馈和重复提交保护。
- 批量启动/停止/health check/GeoIP/tag/proxy/export/delete。

## 2026-05-26 Profile CSV 批量创建前端提交小闭环

背景：

- 后端 `POST /api/profiles/import` 完成后，继续把 Profile CSV preview 弹窗升级为可提交有效行的导入入口。
- 本轮只把现有弹窗接入后端 batch import API，不改 ProfileTable、BulkActionBar 或 runtime。

已完成：

- [x] `frontend/src/lib/api.ts`
  - 新增 `ProfileImportResult` / `ProfileImportResponse`。
  - 新增 `api.importProfiles(csvText)`，调用 `/api/profiles/import`。
- [x] `frontend/src/components/ProfileCsvPreviewDialog.tsx`
  - Preview 后若存在有效行，显示 `Create valid profiles`。
  - 点击后调用 `api.importProfiles`，进入 creating 状态并防重复提交。
  - 成功后展示 `Imported N profile(s), M failed`。
  - 导入结果优先显示后端 `results`，失败行继续保留 errors。
  - 保留最近一次成功 preview 的原始 CSV 用于提交，UI 中 textarea 仍显示脱敏 CSV，避免 proxy 凭证丢失或泄漏。
- [x] `frontend/src/App.tsx`
  - 传入 `onImported={refresh}`，导入后刷新 profile list。
- [x] `frontend/src/lib/api.test.ts`
  - 覆盖 `api.importProfiles` 调用 `/api/profiles/import`。
- [x] `frontend/src/App.test.tsx`
  - 覆盖 preview 后点击 `Create valid profiles`。
  - 断言调用 batch import API，不调用单条 `create`。
  - 断言导入后调用 `refresh`，成功/失败汇总可见，失败原因保留且不泄漏 credentials。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "importProfiles"
# 红灯：1 failed
# 失败点：api.importProfiles is not a function

cd frontend && npm test -- --run src/lib/api.test.ts -t "importProfiles"
# 1 passed, 22 skipped

cd frontend && npm test -- --run src/App.test.tsx -t "imports valid profile CSV"
# 1 passed, 25 skipped

cd frontend && npm test -- --run
# 13 passed, 171 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`，让服务加载最新后端和 `frontend/dist`。
- 通过 API 创建 QA 模板 `CSV Import UI Mac`。
- 桌面 `1440x960`：
  - 打开 `Import profile CSV preview` 弹窗。
  - 粘贴 2 行 CSV 后点击 `Preview CSV`，显示 `2 total / 1 ready / 1 blocked`。
  - 点击 `Create valid profiles` 后显示 `Imported 1 profile(s), 1 failed`。
  - 左侧列表和主统计从 `5 profiles` 刷新为 `6 profiles`，并出现 `UI Batch Import`。
  - 失败行继续显示 `name is required`、`Template not found`、`platform must be one of...`。
  - 页面正文不包含 `hiddenpass` 或 `user:`。
- 移动 `390x844`：
  - 弹窗可见，导入结果提示保留。
  - `body.scrollWidth=390`、`body.clientWidth=390`，body 未被横向撑破。
- Playwright MCP console：当前交互后 0 errors、0 warnings。
- 截图：
  - `/tmp/cloakbrowser-profile-csv-import-screens/desktop.png`
  - `/tmp/cloakbrowser-profile-csv-import-screens/mobile.png`

未覆盖范围：

- 批量启动/停止/health check/GeoIP/tag/proxy/export/delete。

## 2026-05-26 Proxy Provider Preset 后端事实源 CRUD 小闭环

背景：

- Module 09 继续从低风险、可测试的 Proxy Template 前置能力切入。
- 本轮只实现 proxy provider preset 的后端事实源和 CRUD API，不做前端选择器，不做按国家/标签选择 proxy，不做随机分配策略。
- Preset 只保存 provider 元数据、国家和标签，不保存 proxy 凭证、provider API key、billing/account 信息。

已完成：

- [x] `backend/database.py`
  - 新增 `proxy_provider_presets` 表。
  - 新增 `create_proxy_provider_preset` / `list_proxy_provider_presets` / `get_proxy_provider_preset` / `update_proxy_provider_preset` / `delete_proxy_provider_preset`。
  - 删除 preset 不级联删除已有 proxy assets。
- [x] `backend/models.py`
  - 新增 `ProxyProviderPresetCreate` / `ProxyProviderPresetUpdate` / `ProxyProviderPresetResponse`。
  - 10 审计安全阶段已补 `ProxyProviderPresetDeleteRequest`；删除 preset 必须传 JSON boolean `confirm_delete: true`。
  - 字段限制为 `name`、`provider`、`country_code`、`tags`、`notes` 和时间戳。
- [x] `backend/main.py`
  - 新增 `/api/proxy-provider-presets` CRUD：
    - `GET /api/proxy-provider-presets`
    - `POST /api/proxy-provider-presets`
    - `GET /api/proxy-provider-presets/{preset_id}`
    - `PUT /api/proxy-provider-presets/{preset_id}`
    - `DELETE /api/proxy-provider-presets/{preset_id}`
  - 10 审计安全阶段已补删除确认：缺失、`false` 或字符串 `"true"` 返回固定 422，未确认不删除 preset。
- [x] `backend/tests/test_proxy_provider_presets.py`
  - 覆盖表创建、DB CRUD、API CRUD、not found、空名称拒绝。
  - 10 审计安全阶段已补 API 删除确认测试。
  - 覆盖删除 preset 不影响 proxy assets。
  - 覆盖传入 `api_key` / `password` / `billing_account` 等凭证或账务字段不会进入响应和列表。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py -q
# 7 passed

. .venv/bin/activate && python -m pytest backend/tests/test_proxy_provider_presets.py backend/tests/test_proxies.py -q
# 22 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 255 passed
```

未覆盖范围：

- 前端 preset 创建/管理入口仍未覆盖；Proxy CSV import 选择入口已在后续小闭环补齐。
- CSV import dialog 消费 provider preset 已在后续小闭环补齐。
- 按国家/标签选择 proxy 和随机分配策略的后端 API 已在后续小闭环补齐；前端运营入口仍未覆盖。
- Proxy check/assign/GeoIP 行为，本轮没有修改。

## 2026-05-26 Proxy Provider Preset 前端消费小闭环

背景：

- 后端 `proxy_provider_presets` 事实源已完成，本轮把 preset 接入 Proxy Manager 的 proxy CSV import。
- 本轮只做“选择 provider preset 作为导入默认值”，不做 preset CRUD 管理页，不做随机分配策略，不修改 Profile CSV import 合约。
- 行内 CSV 显式字段优先，preset 只补空字段；tags 使用 preset tags + row tags 去重合并。

已完成：

- [x] `frontend/src/lib/api.ts`
  - 新增 `ProxyProviderPreset` / `ProxyProviderPresetCreateData` / `ProxyProviderPresetUpdateData`。
  - 新增 `listProxyProviderPresets` / `createProxyProviderPreset` / `updateProxyProviderPreset` / `deleteProxyProviderPreset` API client。
- [x] `frontend/src/components/ProxyManagerPage.tsx`
  - Proxy Manager 加载 provider presets。
  - `Import proxy CSV` 弹窗新增 `Provider preset` 下拉。
  - CSV preview/import 使用 preset 默认 `provider`、`country_code`、`notes`、`tags`。
  - textarea 显示脱敏 URL，内部保留刚粘贴的 raw CSV 用于创建 proxy asset。
- [x] `frontend/src/lib/api.test.ts`
  - 覆盖 provider preset API client 路由、method 和 request body。
- [x] `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖选择 preset 后 CSV 行自动继承 provider/country/notes/tags。
  - 覆盖 row tags 与 preset tags 合并。
  - 覆盖 UI 不渲染 `hiddenpass`。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "ProxyProviderPreset|listProxyProviderPresets|createProxyProviderPreset|updateProxyProviderPreset|deleteProxyProviderPreset"
# 4 passed, 24 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx -t "applies proxy provider preset defaults"
# 1 passed, 18 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 19 passed

cd frontend && npm test -- --run src/lib/api.test.ts
# 28 passed

cd frontend && npm test -- --run
# 13 passed, 180 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 重启本地 QA 服务 `http://127.0.0.1:8095/`，让服务加载最新后端和 `frontend/dist`。
- 通过 API 创建 QA preset `QA Japan Mobile`。
- 桌面/移动交互：
  - 进入 `Proxy Manager`。
  - 打开 `Import CSV`。
  - `Provider preset` 下拉可选择 `QA Japan Mobile`。
  - 粘贴 `name,url,tags` CSV 后，textarea 显示脱敏 endpoint，不显示 `user:hiddenpass`。
  - Preview 行显示 `ProxyJP`、`mobile, bulk`、`Ready`。
  - 点击 `Import valid rows` 后，新增 `QA Preset Import` proxy asset，列表中显示 `JP`、`ProxyJP`、`Tokyo QA defaults`、`mobile/bulk`。
  - `document.body.innerText` 不包含 `hiddenpass` 或 `user:`。
  - 移动端 `body.scrollWidth=390`、`clientWidth=390`，未横向撑破。
- Playwright MCP console：0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-proxy-preset-desktop.png`
  - `/home/jeff/code/cloakbrowser-proxy-preset-mobile.png`

未覆盖范围：

- Provider preset 前端 CRUD 管理页。
- 与国家/标签选择 proxy、随机分配策略的后端联动已在后续小闭环补齐；前端运营入口仍未覆盖。
- Proxy check/assign/GeoIP 行为，本轮没有修改。

## 2026-05-26 Proxy 国家/标签候选过滤与随机分配后端 API 小闭环

背景：

- 在 proxy provider preset 后端事实源和前端消费之后，继续推进 Proxy Template 的核心运营策略。
- 本轮只做后端契约：按 provider preset / country / tags 筛选候选 proxy，并随机分配给多个 profiles。
- 不做前端入口，不修改既有单 proxy assign API，不触碰 browser runtime、CDP、VNC 或高风险批量启动/删除。

已完成：

- [x] `backend/models.py`
  - 新增 `ProxyRandomAssignRequest` / `ProxyRandomAssignResult` / `ProxyRandomAssignResponse`。
  - 请求支持 `profile_ids`、`provider_preset_id`、`provider`、`country_code`、`tags`。
  - 响应包含 `strategy=random`、筛选条件、`candidate_count`、部分成功结果和脱敏 proxy。
- [x] `backend/main.py`
  - 新增 `POST /api/proxies/assign/random`。
  - `provider_preset_id` 可注入 preset 的 `provider/country_code/tags`。
  - `country_code` trim + uppercase 后匹配。
  - tags 使用 preset tags + request tags 去重合并，当前语义为全部 tag 同时匹配。
  - 每个有效 profile 从候选 proxy 中 `random.choice` 一个并写入 raw proxy URL。
  - missing profile 返回行级失败，不阻断其他 profile。
  - 候选为空返回 `400 No proxy assets match selection`，不改 profile。
- [x] `backend/tests/test_proxies.py`
  - 覆盖 provider preset + country + tag 候选过滤。
  - 覆盖 random assignment 对多个 profile 的部分成功。
  - 覆盖响应不泄漏 proxy credentials，但数据库写入 raw proxy URL。
  - 覆盖候选为空返回 400 且不改 profile。

验证：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q -k "random_proxy_assignment"
# 2 passed, 15 deselected

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py -q
# 17 passed

. .venv/bin/activate && python -m pytest backend/tests/test_proxies.py backend/tests/test_proxy_provider_presets.py -q
# 24 passed

. .venv/bin/activate && python -m pytest backend/tests -q
# 257 passed
```

未覆盖范围：

- 前端按国家/标签/随机分配的运营入口。
- tag match `any` 策略；当前后端为 all-match。
- 随机分配并发限制和审计。
- 批量启动/停止/GeoIP/tag/proxy/delete。

## 2026-05-26 Proxy 随机分配前端运营入口小闭环

背景：

- 继续 Module 09 Proxy Template 和批量运营能力。
- 后端已经具备 `POST /api/proxies/assign/random`，本轮补齐 Proxy Manager 前端入口。
- 本轮不做 provider preset CRUD 管理页，不修改 runtime，不接 Project Mileage。

已完成：

- [x] `frontend/src/lib/api.ts`
  - 新增 `ProxyRandomAssignRequestData` / `ProxyRandomAssignResponse` / `ProxyRandomAssignResult`。
  - 新增 `api.assignRandomProxyToProfiles`，POST `/api/proxies/assign/random`。
- [x] `frontend/src/components/ProxyManagerPage.tsx`
  - Proxy Manager toolbar 新增 `Random assign`。
  - 按当前 Country / Provider / Tag filter 形成后端 selection，内部 sentinel 不会提交给后端。
  - 新增独立 `Random proxy assignment` 弹窗，选择 profiles 后随机分配匹配 proxy。
  - 搜索框只用于筛选 profile，不影响 proxy candidate selection，避免与后端契约不一致。
  - 成功后显示结果、关闭弹窗、清理选择，并调用 `onProfilesAssigned` 刷新 profile 数据。
  - 错误信息继续通过 `redactUrlCredentials` 脱敏。
- [x] `frontend/src/lib/api.test.ts`
  - 覆盖 random assignment API endpoint 与 body shape。
- [x] `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖按 Country / Provider / Tag filter 随机分配给选中 profiles。
  - 覆盖成功提示、profile refresh、弹窗关闭、凭证不渲染。

验证：

```bash
cd frontend && npm test -- --run src/lib/api.test.ts -t "assignRandomProxyToProfiles"
# 1 passed, 28 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx -t "randomly assigns"
# 1 passed, 19 skipped

cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx
# 20 passed

cd frontend && npm test -- --run src/lib/api.test.ts
# 29 passed

cd frontend && npm test -- --run
# 13 passed, 182 passed

cd frontend && npm run build
# built successfully
```

浏览器 UI/UE 验证：

- 本地 QA 服务：`http://127.0.0.1:8095/`，进程 `1749057`。
- 桌面 `1440x960`：
  - Proxy Manager 选择 `JP` / `ProxyJP` / `mobile`。
  - 点击 `Random assign` 打开 `Random proxy assignment`。
  - 弹窗显示 `1 candidate proxy`，选择 2 个 profiles 后提交。
  - 真实调用 `POST /api/proxies/assign/random`，请求体为 `country_code=JP`、`provider=ProxyJP`、`tags=["mobile"]` 和 2 个 profile ids。
  - 响应 `200 OK`，显示 `Random assigned proxy to 2 profile(s), 0 failed`。
- 移动 `390x844`：
  - `Random assign` 在工具栏内换行可见。
  - `body.scrollWidth=390`、`documentElement.scrollWidth=390`，页面本体不横向撑破。
- Playwright MCP console：0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-random-assign-desktop.png`
  - `/home/jeff/code/cloakbrowser-random-assign-mobile.png`

未覆盖范围：

- Provider preset 前端 CRUD 管理页。
- tag match `any` 策略；当前后端为 all-match。
- 随机分配并发限制和审计。
- Profile operations 主表里的批量 proxy 设置入口。
- 批量启动/停止/GeoIP/tag/delete。

## 2026-05-26 Proxy Provider Preset 前端完整管理入口小闭环

背景：

- Module 09 的 `proxy provider preset` 已具备后端事实源、CSV import 前端消费和随机分配后端策略联动。
- 本轮补齐 Proxy Manager 内的完整管理入口，方便运营者维护 provider/country/tags/notes 默认值。
- 不修改后端、不接 Project Mileage、不把 provider API key/password/billing/account 等字段做进 CloakBrowser UI。

已完成：

- [x] `frontend/src/components/ProxyManagerPage.tsx`
  - Toolbar 新增 `Manage presets`。
  - 新增 `Manage provider presets` 弹窗，支持创建、编辑、删除 provider preset。
  - 表单只暴露 `name`、`provider`、`country_code`、`tags`、`notes`。
  - 创建/编辑后同步 `providerPresets`，CSV import 的 `Provider preset` 下拉即时更新。
  - 删除当前 preset 后从管理列表和 import 下拉移除，并清理当前 import 选中值。
  - 保存和删除错误继续通过 `redactUrlCredentials` 脱敏。
  - 移动端弹窗 body 改为内部滚动，避免窄屏裁切底部操作按钮；页面本体仍不横向撑破。
- [x] `frontend/src/components/ProxyManagerPage.test.tsx`
  - 覆盖 provider preset create。
  - 覆盖 provider preset update/delete。
  - 覆盖管理弹窗不出现 `api key/password/billing/account` 等敏感 provider 字段文案。
- [x] `docs/ai-docs/v1/tasks/09-templates-bulk-ops.md`
  - 勾选 `支持 proxy provider preset`。
  - 勾选 `前端完整管理入口`。

验证：

```bash
cd frontend && npm test -- --run src/components/ProxyManagerPage.test.tsx -t "proxy provider presets"
# 1 test file passed, 2 tests passed | 20 skipped

cd frontend && npm test -- --run
# 13 test files passed, 184 tests passed

cd frontend && npm run build
# built successfully

git diff --check
# passed
```

浏览器 UI/UE 验证：

- 本地 QA 服务：`http://127.0.0.1:8095/`，运行时 `invisible-playwright`。
- 桌面 `1440x960`：
  - 进入 `Proxy Manager`。
  - 打开 `Manage presets`。
  - 创建 `QA UI Preset Temp`，页面显示 `Saved provider preset QA UI Preset Temp`。
  - 打开 `Import CSV`，`Provider preset` 下拉出现新 preset。
  - 选择新 preset 并粘贴仅含 `name,url` 的 CSV，preview 自动补入 `ProxyQA`、`US`、`ui, temp`。
  - 编辑为 `QA UI Preset Updated`，页面显示 `Saved provider preset QA UI Preset Updated`。
  - 删除临时 preset，页面显示 `Deleted provider preset QA UI Preset Updated`。
  - 再打开 `Import CSV`，临时 preset 已从下拉移除，只保留既有 `QA Japan Mobile`。
- 移动 `390x844`：
  - `Manage provider presets` 弹窗在窄屏下使用内部滚动。
  - `document.body.scrollWidth=390`、`viewportWidth=390`，页面本体未横向撑破。
- Playwright MCP console：0 errors、0 warnings。
- 截图：
  - `/home/jeff/code/cloakbrowser-provider-presets-desktop.png`
  - `/home/jeff/code/cloakbrowser-provider-presets-mobile.png`

未覆盖范围：

- Provider preset 删除确认/撤销；当前任务只要求完整管理入口，批量删除二次确认仍留在批量运营任务中。
- Provider preset API 错误分支的 UI 自动化测试。
- Profile operations 主表里的批量 proxy 设置入口。
- 批量启动/停止/health check/GeoIP/tag/proxy/delete。
