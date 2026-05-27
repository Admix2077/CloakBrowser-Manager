# Profile Dir Archive 只读评估

## 目标

为后续 profile bundle 是否支持 Firefox profile dir archive 建立安全边界。本评估只定义风险、允许清单、拒绝清单、审计和测试要求，不代表已经实现 archive 导出或导入 API。

profile dir 是浏览器的完整本地状态目录，可能包含登录态、站点缓存、历史记录、下载记录、证书/key DB、session restore、设备绑定标识和业务 token。它不能像普通 JSON config 一样默认导出，也不能整目录 zip 后直接导入到既有 profile。

## 当前事实

- `backend/database.py:create_profile()` 当前把 `user_data_dir` 固定生成为 `/data/profiles/{profile_id}`。
- `backend/browser_manager.py:_build_invisible_kwargs()` 会把 `profile["user_data_dir"]` 作为 invisible_playwright 的 `profile_dir`。
- `backend/browser_manager.py:_clean_firefox_startup_state()` 只在启动前清理 Firefox lock 和 session restore 文件，不清理站点数据。
- `backend/main.py:delete_profile()` 删除 profile 时会删除对应 `user_data_dir` 目录。
- `backend/profile_bundle.py` 当前只保留 `profile_dir.included=false`、`file_count=0`、`total_bytes=0`、`excluded_file_count=0` 和 `archive=null` 的占位结构。
- 当前 `POST /api/profiles/{profile_id}/bundle/export` 不读取磁盘 profile dir，不生成 archive。
- 当前 `POST /api/profiles/bundle/import` 只读取 `bundle.profile.config`，忽略 `profile_dir.archive`。

## 当前结论

当前阶段不实现 profile dir archive export/import API。

原因：

- 整目录 archive 很容易包含 cookie、local storage、IndexedDB、Cache Storage、history、session restore、download metadata、cert/key DB 和站点权限。
- Firefox SQLite、WAL、SHM、lock、session restore 等文件在 running profile 下可能不一致。
- 导入 archive 到既有目录会造成跨 profile 污染、权限绕过和难以审计的账号状态覆盖。
- 文件名、路径和 archive metadata 本身也可能携带 URL、账号名、token 或业务标识。

## 未来导出边界

如后续实现 archive export，必须满足以下条件：

- 只允许 stopped profile；running profile 必须返回固定错误，不尝试复制正在使用的 profile dir。
- 必须使用独立请求字段：
  - `include_profile_dir_archive: true`
  - `confirm_profile_dir_archive_export: true`
- 两个字段必须是 JSON boolean，不接受字符串或数字宽松转换。
- 未确认时不读取 profile dir、不统计文件、不写 audit。
- 只面向可信本地管理 API，不给 Project Mileage App 直连。
- archive 文件不得自动写入仓库、不得自动提交、不得落在公开静态目录。
- 响应中可以返回低敏统计和下载句柄，但不能回显绝对路径、文件名明细、URL query、fragment、token 或 secret。

## 未来导入边界

如后续实现 archive import，必须满足以下条件：

- 只能创建新 profile、新 UUID 和新 `user_data_dir`。
- 不能覆盖既有 profile，不能把 archive 解压到调用方指定目录。
- 不能信任 archive 内部路径或 metadata。
- 必须先校验完整 archive 清单，通过后才允许解包。
- 必须拒绝路径穿越、绝对路径、空路径、重复路径、symlink、hardlink、设备文件、socket、FIFO、特殊权限位和超大文件。
- 必须设置文件数量、单文件大小、总字节数和目录深度上限。
- 导入失败必须清理临时目录和新建半成品目录。
- 导入响应只返回新 profile 的低敏字段，不回显 archive 文件名明细或原始错误。

## 建议允许清单

未来如果要做最小 profile dir archive，建议先从严格 allowlist 开始，而不是 denylist 补洞。

初始 allowlist 只建议考虑：

- Firefox profile 必需的非敏感配置文件，且要逐项验证字段内容。
- 与指纹浏览器环境稳定性直接相关、不会携带站点账号状态的偏好配置。
- 经测试确认不包含 URL、token、账号状态、证书、cookie、local storage、history 或下载信息的文件。

当前阶段不列出可直接放行的具体文件名。原因是需要先用真实 Firefox/invisible_playwright profile 样本做只读清单审计，但本轮不读取真实 profile dir，也不接触用户数据。

## 必须拒绝清单

未来实现时至少必须拒绝：

- `cookies.sqlite`、`cookies.sqlite-wal`、`cookies.sqlite-shm`。
- `webappsstore.sqlite`、`webappsstore.sqlite-wal`、`webappsstore.sqlite-shm`。
- `places.sqlite`、`favicons.sqlite`、`formhistory.sqlite`、`permissions.sqlite`、`content-prefs.sqlite` 及其 WAL/SHM。
- `storage/`、`indexedDB/`、`cache2/`、`startupCache/`、`shader-cache/`、`serviceworker.txt`、`serviceworkers/`。
- `sessionstore.jsonlz4`、`sessionCheckpoints.json`、`recovery.jsonlz4`、`previous.jsonlz4`、`upgrade.jsonlz4-*`。
- `downloads.json`、下载临时文件、页面保存文件。
- `cert9.db`、`key4.db`、`pkcs11.txt`、证书、私钥和安全模块文件。
- `.parentlock`、`parent.lock`、`lock`、`SingletonLock`、`*.lock`。
- `.env`、数据库 dump、日志、崩溃报告、core dump、secret、token、临时备份文件。
- 任何隐藏高风险目录、绝对路径条目、包含 `..` 的路径条目和非普通文件。

## Audit 边界

未来成功导出 profile dir archive 时，建议写低敏 audit：

- `event_type=profile_bundle.profile_dir_archive_exported`。
- `actor_type=local_admin`。
- `profile_id` 为目标 profile。
- metadata 只包含：
  - `format`。
  - `schema_version`。
  - `file_count`。
  - `total_bytes`。
  - `excluded_file_count`。
  - `archive_manifest_hash`。

metadata 禁止包含：

- archive 文件名明细。
- 原始 profile dir 路径。
- URL、query、fragment。
- cookie、local storage、IndexedDB key/value。
- token、secret、proxy password、Authorization。
- Project Mileage 订单、钱包、权限、扣费、续期或审计事实。

## Project Mileage 边界

- Project Mileage App 不能直接调用 CloakBrowser bundle、cookie、local storage、profile dir archive 或 runtime API。
- Payload 仍是账号、订单、钱包、权限、续期、viewer token 和审计事实源。
- 如果远程账号工作台未来需要 profile dir archive 迁移能力，必须先提交跨仓 Proposal，由主 agent/Jeff 确认 Payload 安全 DTO、权限、审计、用户风险提示和运营可见边界。
- 本评估不要求修改 `/home/jeff/code/project-mileage-v3-app` 或 `/home/jeff/code/project-mileage-v3-payload`。

## 建议测试清单

未来实现前必须先补失败测试：

- `include_profile_dir_archive=true` 且未确认时返回固定 422，不读取 profile dir，不写 audit。
- 字符串或数字 boolean 不被宽松转换。
- running profile 返回固定错误，不复制目录。
- stopped profile 不存在目录时返回固定错误，不回显绝对路径。
- archive manifest 默认不包含文件名明细、绝对路径、URL query、fragment 或 token。
- allowlist 之外的文件都会计入 excluded，不进入 archive。
- symlink、hardlink、设备文件、socket、FIFO、绝对路径、路径穿越和重复路径被拒绝。
- 超过文件数、目录深度、单文件大小或总字节数上限时失败并清理临时目录。
- import 总是创建新 profile、新 UUID 和新目录，不覆盖既有 `user_data_dir`。
- import 忽略或拒绝 archive 中的 Project Mileage 钱包、订单、权限、审计、viewer token、runtime session 和 automation 字段。
- audit metadata 只包含低敏统计和 hash，不包含文件名、路径、URL、token 或 secret。

建议命令：

```bash
. .venv/bin/activate && python -m pytest backend/tests/test_profile_bundle.py backend/tests/test_api.py -q
. .venv/bin/activate && python -m pytest backend/tests/test_cookies.py -q
git diff --check
```

## 本轮验收口径

本轮只要求文档落地：

- 明确当前不实现 profile dir archive API。
- 明确未来 export/import 的最小安全边界。
- 明确 allowlist 优先、denylist 必备、导入隔离、audit 和测试清单。
- 明确不修改 Project Mileage app/payload。
