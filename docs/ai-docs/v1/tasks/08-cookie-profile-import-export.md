# 08 Cookie、Profile 导入导出

## 目标

提供成熟指纹浏览器常见的 cookie 和 profile 迁移能力，同时控制敏感数据暴露风险。

## 任务清单

- [ ] 定义 cookie JSON import 格式。
- [ ] 定义 cookie JSON export 格式。
- [ ] 支持 Netscape cookie import。
- [ ] 支持 Netscape cookie export。
- [ ] 仅运行中 profile 允许通过 browser context 导入 cookie。
- [ ] 停止状态 profile 可通过 profile dir 方式导入 cookie 时必须先评估 Firefox 存储格式，不强行实现。
- [ ] 导出 cookie 必须写 audit。
- [ ] 导出 cookie 必须有显式确认。
- [ ] 前端新增 Cookie 管理入口。
- [ ] 支持 profile config export：
  - 不包含 cookie。
  - 不包含 proxy password，除非用户选择包含敏感字段。
- [ ] 支持 profile config import。
- [ ] 后续支持完整 profile bundle：
  - profile dir。
  - cookies。
  - local storage。
  - fingerprint config。
  - metadata。

## 安全规则

- cookie value 不进入日志。
- cookie 导出文件不自动提交。
- proxy password 默认遮蔽。
- profile bundle 导出必须带风险提示。

## 验证

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py -q
cd frontend && npm test -- --run
cd frontend && npm run build
```

## 验收标准

- [ ] JSON cookie 导入后页面可读到 cookie。
- [ ] JSON cookie 导出不破坏字段。
- [ ] Netscape 格式基础兼容。
- [ ] 导出动作写 audit 且不记录 cookie 明文。
