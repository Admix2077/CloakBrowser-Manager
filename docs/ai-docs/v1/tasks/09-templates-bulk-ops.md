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
- [ ] 创建 profile 时可选择模板。
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
- [ ] 导入前预览。
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
