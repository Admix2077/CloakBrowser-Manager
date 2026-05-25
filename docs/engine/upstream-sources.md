# 上游源码来源记录

本项目从 `CloakBrowser-Manager` 派生为 `cloakbrowser-invisible-manager`，目标是在保留 Manager 管理面板和 noVNC 网页操控能力的前提下，将后端浏览器启动器从 CloakBrowser Chromium 替换为 `invisible_playwright` patched Firefox。

## 主项目基座

- 仓库：`https://github.com/CloakHQ/CloakBrowser-Manager.git`
- 当前工作目录：`/home/jeff/code/cloakbrowser-invisible-manager`
- 基线 commit：`f65b4b32022e0c4110c1972e9b471e4758b98ac4`
- 当前分支：`feature/invisible-playwright-engine`

## 旧内核参考

- 仓库：`https://github.com/CloakHQ/CloakBrowser.git`
- 本地只读参考目录：`_research/upstream/CloakBrowser`
- 参考 commit：`7fc577e5c6dd9e5674965d8f7119bb434d648deb`
- 用途：对照旧 Chromium/CloakBrowser 参数、Docker 依赖和 `cloakserve` 行为，不作为本项目运行依赖。

## 新内核运行依赖

- 仓库：`https://github.com/feder-cr/invisible_playwright.git`
- 本地只读参考目录：`_research/upstream/invisible_playwright`
- 参考 commit：`3d8ba0b82c51854aa5fe1fe35240553294be02f8`
- 运行依赖策略：后端依赖锁定到上述 commit，不直接修改 invisible_playwright 内核源码。

## 本地参考目录提交策略

`_research/upstream/` 只用于本机调研和源码对照，已加入 `.gitignore`，避免把第三方仓库整包提交进产品仓库。需要复现调研环境时重新执行：

```bash
mkdir -p _research/upstream
git clone --depth 1 https://github.com/CloakHQ/CloakBrowser.git _research/upstream/CloakBrowser
git clone --depth 1 https://github.com/feder-cr/invisible_playwright.git _research/upstream/invisible_playwright
```
