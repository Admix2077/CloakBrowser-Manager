# 09 模板、批量创建与批量运营

## 目标

实现成熟多账号运营需要的模板和批量能力，减少逐个创建 profile 的重复操作。

## 任务清单

### Profile Template

- [ ] 新增 profile_templates 表。
- [ ] 支持保存模板：
  - platform。
  - screen。
  - GPU。
  - hardware concurrency。
  - color scheme。
  - humanize。
  - launch args。
  - geoip。
- [ ] 创建 profile 时可选择模板。
- [ ] 模板变更不自动修改已有 profile，避免意外批量污染。

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
- [ ] 模板不会静默改写已有 profile。
