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

- [ ] 支持 CSV 粘贴导入 profile。
- [ ] 支持字段：
  - name。
  - proxy。
  - tags。
  - notes。
  - template。
  - platform。
  - locale。
  - timezone。
- [x] 导入前预览（后端 API；前端导入 UI 另起闭环）。
- [ ] 无效行标红。
- [ ] 部分导入成功，失败行保留原因。

### 批量运营

- [ ] 批量启动。
- [ ] 批量停止。
- [ ] 批量 health check。
- [ ] 批量刷新 GeoIP。
- [ ] 批量设置 tag。
- [ ] 批量设置 proxy。
- [ ] 批量导出 profile config。
- [ ] 批量删除必须二次确认。

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_bulk.py backend/tests/test_templates.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [ ] 批量导入不会因为一行失败而全部失败。
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
