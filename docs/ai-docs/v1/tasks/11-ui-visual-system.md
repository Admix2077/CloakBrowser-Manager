# 11 UI 视觉系统与体验升级

## 目标

把 UI 从朴素配置面板升级为成熟、专业、高密度的指纹浏览器运营台。

## 设计方向

- 专业安全运营台。
- 深色低噪声。
- 高密度但清晰。
- 健康状态使用 emerald/cyan。
- 警告使用 amber。
- 错误使用 red。
- 使用 lucide 图标。
- 不做营销 hero。
- 不做夸张 cyberpunk。
- 不用大面积渐变装饰。

## 任务清单

- [ ] 统一 CSS token。
- [ ] 重写按钮状态：
  - default。
  - hover。
  - active。
  - disabled。
  - loading。
- [ ] 重写 input/select/textarea 样式。
- [ ] 新增 badge 系统：
  - health。
  - runtime。
  - proxy。
  - country。
  - tag。
- [ ] 新增 table 样式。
- [ ] 新增 empty state 样式。
- [ ] 新增 error banner。
- [ ] 新增 toast 或 inline feedback。
- [ ] 用项目内 ConfirmDialog 替代原生 `confirm`。
- [ ] ProfileForm 改为分组页签：
  - Identity。
  - Network。
  - Device。
  - Behavior。
  - Advanced。
- [ ] Viewer 顶部 EnvironmentStrip 视觉升级。
- [ ] 375px、768px、1024px、1440px 响应式检查。
- [ ] 文案避免“保证安全”“保证不封号”等不可验证承诺。

## 验证

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

浏览器检查：

- [ ] Profile table 无溢出。
- [ ] 表单长字段不撑破容器。
- [ ] Viewer 工具条不遮挡 VNC。
- [ ] 批量操作栏不挡住主操作。
- [ ] 深色对比度足够。
