# LLBot v8.3.2-NA 可行性调查

日期：2026-11-13。对应计划：005。决策：**C，后续实现与发行 BLOCKED**。

公开调查与最小离线验证已执行。现有资料不足以部署完整鉴权/签名链路，也没有验证可独立运行的本地替代实现。没有制作 Token 分发器、修改客户端鉴权、创建 NA tag 或发布 NA 包。原 v8.3.2 镜像发行保持原状。

这不是“证明服务端不存在”。结论限于以下已读取的公开仓库、历史文档、发行物和本次隔离测试。CLI 实际显示版本已定位为 2.1.4，但其构建与公开源码 commit 的精确对应仍未闭合；因此阶段 1 的全部验收条件不能标为通过。

## 固定基线与执行证据

- 应用：[v8.3.2 commit dc2b2b90092ef0f571b5546878288b83fff1e436](https://github.com/mlpoki/LuckyLilliaBot/tree/dc2b2b90092ef0f571b5546878288b83fff1e436)，annotated tag 对象 `7dec94b7a0fb2ed5fa49677841afe5074a46b3cf`。
- 调查分支从 fork 当前 `main` 的 `86b78f96` 建立，以保留已有镜像维护；应用调查和适配测试均另取上述固定基线，不以 main 应用源码代替 v8.3.2。
- [首轮 Windows Actions](https://github.com/mlpoki/LuckyLilliaBot/actions/runs/43387531431)：包内清单、版本资源、7 项 TS 适配检查和 22 项镜像回归通过。
- [第二轮 Windows Actions](https://github.com/mlpoki/LuckyLilliaBot/actions/runs/43387935782)：增加组件逐文件比对、固定 Desktop 源码的 6 项预检检查；7 + 6 + 22 项检查全部通过。测试提交 `57fb5b8f7b64ed03a43bb77095f63f454731847e`。
- [第二轮完整 artifact](https://github.com/mlpoki/LuckyLilliaBot/actions/runs/43387935782/artifacts/14019646376) 保留静态二进制及文本副本，保留期 30 天；长期可复核的小型记录在本目录 [evidence](evidence/)。工作流可重新下载固定摘要的包。

| 固定 fork 资产 | 大小 bytes | 本次实际 SHA-256 |
|---|---:|---|
| LLBot-CLI-win-x64.zip | 95713510 | `3b29f2bdaafbbb1e0e494e42d81da7566aeb16114e9eb42a5d168c59dbcadcb7` |
| LLBot-Desktop-win-x64.zip | 65767668 | `38fde3cc61d76fc9bfcfabcc7b0b362a5c938016d8b57a1665d4173492d3981f` |

以上与计划历史摘要及本次 GitHub asset digest 一致。入口、运行时、全部成员的大小/摘要见 [inventory.json](evidence/inventory.json)。

## 组件身份：观察与未知分开

| 组件 | 实际包内观察 | 源码对应与限制 |
|---|---|---|
| CLI 入口 LuckyLillia.exe | PE version `2.1.4`；SHA `48e3988cf625410be8f4ef89beed680123b71630158982ce40a04c16da1c9b25` | 候选 [CLI v2.1.4 / e3520c91f1e6541daa2ba8a842ad0ecb10d33024](https://github.com/LuckyLilliaDev/LuckyLillia.CLI/tree/e3520c91f1e6541daa2ba8a842ad0ecb10d33024)。该 Release 当前独立 EXE 的 SHA 为 `8a86d5cf1cb39493c22f148245e1ceaeea0f25fcaa9602a083d4deda405077bb`，**不匹配**。只能确证显示版本，不能确证同一源码构建；原因未知。 |
| Desktop 入口 LuckyLillia.exe | PE product version `3.1.2+a718675d6916fcf013e5929ddffe464fbd750c03`；SHA `9b9826a62da1c16e6d6f5ed31df00cfeeb7913175d704c8cbaf1a27d6bf85419` | 与 [Desktop v3.1.2](https://github.com/LuckyLilliaDev/LuckyLillia.Desktop/releases/tag/v3.1.2) ZIP 内 `lucky-lillia-desktop.exe` 逐字节一致，对应 [a718675d6916fcf013e5929ddffe464fbd750c03](https://github.com/LuckyLilliaDev/LuckyLillia.Desktop/tree/a718675d6916fcf013e5929ddffe464fbd750c03)。 |
| 两包 bin/llbot | package version `8.3.2`；两包 llbot.js 同 SHA `83707ca9764d5fba040db52cdfaf5ec91735e40bbb0857c41dd44dcb5c73e81c` | 固定源码 tag 为调查基线；未重新构建主程序，未声称源码可重现同一 JS 字节。根源码 package.json 的 `8.0.0` 不能当发行版本。 |
| 两包 sign-proxy.win-x64.node | 同 SHA `e42cba1619b716055bf77c765c4d86fd35398d071c564cebf158c01d2988cc03` | 与 v8.3.2 树中的 `.node` 逐字节一致。loader JSON 标记 `0.1.0-20261007184501`，这是缓存/同步版本，**原生实现源码 commit 未知**。 |
| CLI bin/pmhq/pmhq.exe 与 pmhq.dll | exe SHA `945edd552a31f7e6e9b21620a8f50729965956d062df5fe12fb7de4276d510e7`；dll SHA `ebeae2141cf6b95551a6bf47ad656dfc522dd5691361cc899b6c208c70d1f800` | 两者均与 [PMHQ v9.0.4](https://github.com/linyuchen/PMHQ/releases/tag/v9.0.4) 逐字节一致，与 v9.0.6 不同。公开 tag `7551952bf6779e89c27d9c1155894ecf58b4d8c7` 只是发布壳，核心源码 commit 未知。不能按 CLI 重传日期猜成 v9.0.6。 |
| CLI Node / ffmpeg / ffprobe | 三个 EXE 已随包；各自摘要在 inventory。Node SHA `d14ba95cdce1ef7dc9ad3ac74949ca5db38b27378ee30f30a23cf26f9e875a11` | 未执行这些运行时，未读取它们的版本资源，其构建版本/commit 仍未知。它们不是缺失签名服务的替代。 |
| Desktop PMHQ 与运行时 | ZIP **没有** PMHQ、node.exe、ffmpeg.exe 或 ffprobe.exe | 匹配源码提供首次下载/补齐机制；未启动 Desktop，因此没有补下载，也没有把当前 latest 当成已随包组件。 |

逐文件匹配记录：[component-matches.json](evidence/component-matches.json)。版本资源解码：[pe-versions.json](evidence/pe-versions.json)。

REA 对两入口只做 PE 资源静态解析：均为 PE32+ / machine `0x8664`。证据分别为 `ev_767dd83abc46f69906ae4be12409d34b542de06b4970779460c972df77a5b8a3` 和 `ev_8ab58fd1792930747b3f24bbbea3d24b0e6e3d449140b065f17e29e66ea33f99`，完整记录见 [CLI](evidence/rea-cli.json)、[Desktop](evidence/rea-desktop.json)。REA 不执行入口、不观察窗口，不把图标/版本字符串当运行行为证据。

## 鉴权和能力依赖矩阵

| 层 | 读取/传递 token | 校验与必要能力 | 可公开重建情况 |
|---|---|---|---|
| CLI 候选 v2.1.4 | `src/util.rs:146` 读 `bin/llbot/data/auth_token.txt`；`src/main.rs:132` 空值退出，默认 PMHQ，headless 也检查；`:243` 给 PMHQ `--auth-token` | 本地检查只证明有非空值；后续服务端仍须认可 | 启动器源码公开；本包构建来源未精确闭合，不能直接贴补丁冒充已验证修复 |
| Desktop 已匹配 v3.1.2 | `HomeViewModel.cs:1337` / `:1539` 两模式调用 `EnsureAuthTokenAsync`；`:1759` 读取、预检、弹窗、写入 token | `AuthTokenValidator.cs` GET `/api/sign/info` + Bearer，2xx valid，401/403 invalid，其余/网络错误 inconclusive；网络不确定的弹窗允许用户二次确认继续，后端鉴权并未消失 | C#/Avalonia 源码公开且版本已匹配；只重建 UI 无法补全后端 |
| Desktop → PMHQ / LLBot | `ProcessManager.cs:348` 向 PMHQ 传 token；`:559` 给 LLBot `--pmhq-port` | PMHQ 另行与 manager 交互；WebUI 不提示不等于 PMHQ 没有鉴权 | PMHQ 需下载，核心未取得 |
| LLBot direct authTokenWatcher | 从文件读 token，回退 AUTH_TOKEN；无 token 不登录；调用 `validateAuthToken` 后才回调登录 | invalid 停止；网络不确定重试，避免直接触发 native 退出 | TS 公开，不能以恒真替换真实能力 |
| LLBot sign.ts → native | setupSign 的 init 包含 authToken、GUID、uin、cdn；签名经 signRequest；动态更新 token 用 setAuthToken | 需要真实 `sign/token/extra`；还需 preflight、sign token、envelope/设备和会话协议。仅实现 validate 不够 | loader/interface 公开，业务原生实现仅 `.node` |
| PMHQ → manager | [配置文档](https://github.com/linyuchen/PMHQ/blob/7551952bf6779e89c27d9c1155894ecf58b4d8c7/doc/config.md) 的 auth_token 为必填 manager-server 凭证 | 缺失会拒绝；另外 `pmhq_api_token` 是本地 HTTP/WS Bearer token，不能混淆 | 核心客户端、manager 签名链源码未取得 |
| manager → sign-service | public interface 只暴露部分端点线索 | 完整 token 签发/验证/到期/撤销、签名后端、QUA 路由、设备/会话支持均必需 | 未找到公开完整部署材料/可用独立实现，不能自造 JWT 或假成功回包替代 |

固定源码链接：[CLI main](https://github.com/LuckyLilliaDev/LuckyLillia.CLI/blob/e3520c91f1e6541daa2ba8a842ad0ecb10d33024/src/main.rs)、[Desktop token 调用](https://github.com/LuckyLilliaDev/LuckyLillia.Desktop/blob/a718675d6916fcf013e5929ddffe464fbd750c03/ViewModels/HomeViewModel.cs#L1759)、[Desktop validator](https://github.com/LuckyLilliaDev/LuckyLillia.Desktop/blob/a718675d6916fcf013e5929ddffe464fbd750c03/Services/AuthTokenValidator.cs)、[Desktop ProcessManager](https://github.com/LuckyLilliaDev/LuckyLillia.Desktop/blob/a718675d6916fcf013e5929ddffe464fbd750c03/Services/ProcessManager.cs)、[authTokenWatcher](https://github.com/mlpoki/LuckyLilliaBot/blob/dc2b2b90092ef0f571b5546878288b83fff1e436/src/main/qqProtocol/direct-lib/authTokenWatcher.ts)、[sign.ts](https://github.com/mlpoki/LuckyLilliaBot/blob/dc2b2b90092ef0f571b5546878288b83fff1e436/src/main/qqProtocol/direct-lib/sign.ts)、[native interface](https://github.com/mlpoki/LuckyLilliaBot/blob/dc2b2b90092ef0f571b5546878288b83fff1e436/src/main/qqProtocol/direct-lib/sign-proxy/index.ts)。

`sign.ts` 将 502 解释为 sign-service 不可用，503 解释为无匹配 QUA 后端。`acquireViaManager` 注释列出 `/api/sign/token/{build-request,decrypt-response}`。Linux/macOS 的部分 ESK/SA 逻辑在 native 本地，不代表签名全链路本地化；Windows/watch 路径仍可经 manager。Windows x64 发行架构也不等于选择了 `--protocol windows`。

WebUI [auth-token 路由](https://github.com/mlpoki/LuckyLilliaBot/blob/dc2b2b90092ef0f571b5546878288b83fff1e436/src/webui/BE/routes/authToken.ts) 的 applicable 判断只针对主程序 direct/PMHQ 模式，录入只写文件，并受 WebUI 密码中间件保护。

## 地址、配置与更新边界

| 类型 | 已确认的代码或文档地址 | 判断 |
|---|---|---|
| 生产 manager API | `api-auth.luckylillia.com`、`llbot-api-auth.wumiao.wang` | 禁止连接的生产鉴权/签名链；本次未向其发送测试请求 |
| token 网页 | `auth.luckylillia.com`、`llbot.wumiao.wang` | 用户获取 token 的前端；本次未访问用户会话或注册/登录 |
| 开发 manager | loader 注释的 `http://localhost:8090` | 编译期 dev native，非 production native 的普通 URL 配置；发行包没有 dev `.node` |
| Desktop 预检覆盖 | `LILLIA_AUTH_BASE_URL`，旧注释举 localhost:8080 | **仅覆盖 Desktop 预检**，不等于能配置 PMHQ/native 的后端。本次以 loopback 覆盖并测试 |
| 下载/更新 | GitHub Releases、registry.npmjs.org 及代码中的 npm 镜像 | 获取组件，非签名后端；只读公开 GitHub 下载已执行，应用更新器未执行 |
| QQ 登录/设备协议 | 包内 native 有 QQ 相关 URL 字面量；完整用途未逆向确认 | 字符串不能证明实际请求或完整协议；本次未连接 QQ 或执行 native |

来源：[固定 environment.ts](https://github.com/mlpoki/LuckyLilliaBot/blob/dc2b2b90092ef0f571b5546878288b83fff1e436/src/common/utils/environment.ts)、上表 Desktop validator、loader 注释。inventory 中 ASCII URL 是**候选字面量**，可能连续拼接、遗漏 UTF-16/编码字符串，不能当完整端点清单或网络抓包。

自动更新也会阻止“只改启动器”成为完整成品：[CLI updater](https://github.com/LuckyLilliaDev/LuckyLillia.CLI/blob/e3520c91f1e6541daa2ba8a842ad0ecb10d33024/src/updater.rs) 从 `llbot-cli-win-x64`、`pmhq-dist-win-x64`、`llonebot-dist` 获取 latest，启动时补齐缺失组件；[Desktop DownloadService](https://github.com/LuckyLilliaDev/LuckyLillia.Desktop/blob/a718675d6916fcf013e5929ddffe464fbd750c03/Services/DownloadService.cs) 从 npm 补组件/更新 Desktop。自建路线若获批准，需固定自有适配版本，当前未修改这些行为。

## 公开后端与历史搜索结果

1. [PMHQ 当前固定树](https://github.com/linyuchen/PMHQ/tree/7551952bf6779e89c27d9c1155894ecf58b4d8c7) 为已归档公开发布壳，完整递归树只有文档、Docker、workflow 等，没有核心 Rust crate。其 [build-release.yml](https://github.com/linyuchen/PMHQ/blob/7551952bf6779e89c27d9c1155894ecf58b4d8c7/.github/workflows/build-release.yml) 从 `linyuchen/PMHQ.Rust` 取预编译附件；该仓库本次公开读取返回 404，只能称未公开可读。
2. 历史 [f42b12968484d3930c2df5a67a4d72b7b662d998 workflow](https://github.com/linyuchen/PMHQ/blob/f42b12968484d3930c2df5a67a4d72b7b662d998/.github/workflows/build-release.yml) 明标 `Checkout private repo`，目标 `linyuchen/LuckyLilliaHook`。历史 V8 [44e5e8255277ef874ff34306e22aa0f5869d5456](https://github.com/linyuchen/PMHQ/tree/44e5e8255277ef874ff34306e22aa0f5869d5456) 同样未提供核心，并已要求 manager token。
3. v8.3.2 [sign-proxy 子树](https://github.com/mlpoki/LuckyLilliaBot/tree/dc2b2b90092ef0f571b5546878288b83fff1e436/src/main/qqProtocol/direct-lib/sign-proxy) 只有 loader、版本 JSON、7 个平台 native 二进制，没有 SignProxy / SecureSDK / ManagerServer 源码。
4. 历史 [dev-mode.md / 40563b573c89104ed2e7bcdba8e655ae347d3bb9](https://github.com/LuckyLilliaDev/LuckyLilliaBot/blob/40563b573c89104ed2e7bcdba8e655ae347d3bb9/docs/dev-mode.md) 描述在独立 SignProxy 仓库执行 `build:dev-bot`、启动 ManagerServer 的 `crates/manager-server`，由本地 manager 生成 token；生产 native 使用 TLS pinning，dev 编译期锁 localhost:8090 并关闭 pinning。此文档不在固定 v8.3.2 树中，只作历史线索；文档描述了设计，未提供缺失实现。
5. 枚举 LuckyLilliaDev 组织公开仓库 15 个、linyuchen 公开仓库 14 个；未见完整 ManagerServer/SignProxy/SecureSDK/sign-service 仓库。GitHub repository 搜索 `PMHQ manager-server`、`LuckyLillia.SignProxy`、`PMHQ.Rust`、`LuckyLillia ManagerServer`、`manager-server luckylillia`、`user:LuckyLilliaDev sign` 未找到部署实现。空搜索不证明不存在，主要结论依据完整树和发行 workflow。
6. 核对 PMHQ main 历史、分支和 tags，以及最近 10 个公开 Releases（v8.0.7 至 v9.0.6）；附件只有客户端三平台 ZIP，未见后端。此范围不等于全部 GitHub 或全部历史。
7. [Yogurt-PMHQ README / aa5584a7ba605eedfeef3fcb054d3a8281412592](https://github.com/LuckyLilliaDev/yogurt-pmhq/blob/aa5584a7ba605eedfeef3fcb054d3a8281412592/README.md) 所称不需签名服务以已运行的 PMHQ 为前提，不能消除 PMHQ 自身 manager 鉴权。没有把其他产品静默替换为 LLBot。

Desktop 当前 main `a74e791` 是后来的整体重写，虽项目仍写 3.1.2，却删除旧 token 弹窗；本次已匹配旧 tag，未使用该 main 替代旧包。

## 离线验证的实际覆盖

| 检查 | 实际结果 | 不能证明的事项 |
|---|---|---|
| 固定两包下载、SHA、静态成员清单与组件匹配 | 第二轮通过，来源差异没有被忽略 | CLI 源码精确构建对应、所有运行时版本 |
| 固定 v8.3.2 `sign.ts`，strip TS 后在 VM 中用 SyntheticModule 替代全部原生/应用依赖 | 7 项通过：空 token、缺 native export、传参/trim/CDN、valid、invalid、retry、异常等；4 次 HTTP fixture 请求全部 127.0.0.1，详见 [adapter-tests.json](evidence/adapter-tests.json) | fixture native bridge 不是 native HTTP 协议的复现；不验证 TLS pinning、签名、发 token、到期/撤销或服务端 |
| 精确匹配 Desktop commit 的未修改 `AuthTokenValidator.cs`，独立 .NET 10 控制台测试壳 | 6 项通过：空值零请求、2xx、401、403、503、loopback 不可达；4 个 GET /api/sign/info 均为 127.0.0.1，Bearer 为固定假数据 fixture，详见 [desktop-tests.json](evidence/desktop-tests.json) | 不验证 GUI、PMHQ、native、真实账号或生产 token；未实现自有鉴权服务器 |
| 既有镜像脚本回归 | Windows runner 22/22，通过；源镜像脚本及 publish.yml 无改动 | 未重新发布/覆盖原资产 |

调查工作流只有 contents:read，不触发原镜像发布入口，没有发布步骤。包内入口、QQ、native `.node`、PMHQ、更新器、包内 Node 均未运行。执行代码只有调查脚本、固定公开 TS adapter 和独立编译的 Desktop validator 测试壳。所有鉴权测试目标均为硬编码 loopback；Desktop 预检 URL 在测试进程内显式设为 loopback，TS 原生导入完全替换。公开资料读取/依赖工具获取属于正常 GitHub/工具安装网络。

这些是代码结构、执行步骤和 loopback 请求日志证据，**不是全机网络抓包或防火墙阻断验收**。没有宣称完成阶段 4 的“原域名不可达仍能登录”验收；本次没有发送生产鉴权/签名请求，没有读取用户凭据、使用已有账号或联系 token 网页会话。

## 路线决策与恢复条件

| 路线 | 结论 | 缺口 |
|---|---|---|
| A 完全本地运行 | 未证可行 | 未取得/验证独立签名与会话实现；部分设备逻辑本地化不能证明全链路本地化 |
| B 完整自建服务 | 未通过 | 缺可部署 manager、签名后端、native/PMHQ 可重建实现及完整客户端接入能力；仅 Desktop 预检可改 URL 不够 |
| C 关键材料不足 | **当前采用，停止阶段 3–5** | 不删除检查、不伪造 token/签名、不发布 v8.3.2-NA |

恢复原计划至少需要：合法可用且完整的服务端/底层签名实现和部署说明；可重建/可配置的 native 与 PMHQ 接入；CLI 本包构建来源闭合；随后先验证完整自有链路，才讨论常驻部署目标和成本。当前没有依据评估完整后端资源需求，因此没有虚报服务器价格，也没有将 Actions 充当常驻服务。

若改用另一协议实现、仅支持特定模式或升级 Desktop，属于产品路线变化，需要明确选择后另行实施。本报告不作该替换。真实 GUI、QQ 登录与消息收发、进程生命周期、更新后行为、服务端签发/到期/撤销等验收全部仍未完成。
