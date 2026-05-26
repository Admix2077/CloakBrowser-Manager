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

- [ ] 支持 proxy provider preset。
- [ ] 支持按国家/标签选择 proxy。
- [ ] 支持随机分配策略。

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
  - 字段覆盖 platform、screen、GPU、hardware concurrency、color scheme、humanize、human preset、launch args、geoip。
- [x] `backend/main.py`
  - 新增 `/api/profile-templates` CRUD：
    - `GET /api/profile-templates`
    - `POST /api/profile-templates`
    - `GET /api/profile-templates/{template_id}`
    - `PUT /api/profile-templates/{template_id}`
    - `DELETE /api/profile-templates/{template_id}`
- [x] `backend/tests/test_templates.py`
  - 覆盖表创建、DB CRUD、API CRUD、not found、模板更新不静默改写已有 profile。

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
