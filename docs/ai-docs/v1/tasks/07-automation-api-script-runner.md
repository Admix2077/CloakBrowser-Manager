# 07 Automation API 与脚本运行器

## 目标

扩展现有 Automation REST API，并在其上实现可记录、可重试、可批量运行的 Script Runner。

## 当前基础

已有：

- `/api/profiles/{id}/automation`
- pages list。
- goto。
- evaluate。
- screenshot。
- clipboard get/set。

## 任务清单

- [ ] 补齐 Automation API 文档。
- [ ] 新增 page create。
- [ ] 新增 page close。
- [ ] 新增 wait for selector。
- [ ] 新增 click。
- [ ] 新增 fill。
- [ ] 新增 keyboard input。
- [ ] 新增 scroll。
- [ ] 新增 console logs。
- [ ] 新增 network summary。
- [ ] 新增 task 表：
  - id。
  - profile_id。
  - status。
  - steps。
  - result。
  - error。
  - created_at。
  - started_at。
  - finished_at。
- [ ] 新增 `POST /api/tasks`。
- [ ] 新增 `GET /api/tasks`。
- [ ] 新增 `GET /api/tasks/{id}`。
- [ ] 新增 `POST /api/tasks/{id}/cancel`。
- [ ] 支持第一版 step：
  - open_url。
  - wait。
  - click。
  - fill。
  - scroll。
  - evaluate。
  - screenshot。
- [ ] 支持并发限制。
- [ ] 支持失败重试。
- [ ] 前端新增 Automation 页面。
- [ ] 前端新增 task log viewer。

## 典型脚本

账号 warm-up：

```json
[
  {"type": "open_url", "url": "https://example.com"},
  {"type": "wait", "ms": 3000},
  {"type": "scroll", "direction": "down", "amount": 600},
  {"type": "screenshot", "full_page": false}
]
```

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_automation.py backend/tests/test_api.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [ ] 不依赖 Chromium CDP。
- [ ] 脚本失败能看到失败 step 和错误。
- [ ] 运行中 profile 才能执行脚本。
- [ ] 脚本不能绕过权限直接读取敏感配置。
