# LLBot 7.12.15 macOS arm64 配套包

包含配套 QQ、PMHQ、Node，并补齐 arm64 FFmpeg/FFprobe。Desktop 程序集版本为 2.8.0，已同步修正原应用清单中的旧版本标记。来源、版本、哈希与构建提交记录在 COMPONENTS.json。

完整解压后双击 Start.command。启动脚本会按解压位置设置 QQ、Node 和组件路径。Desktop 打开后点击启动。CLI 与 Desktop 择一运行，启动前退出其他 QQ 和 LLBot。

首次获取账号信息时若 PMHQ 尚未返回对象，主程序会继续等待重试。更新组件会改变当前验证组合。

Desktop 完整包采用本地 ad-hoc 签名。GitHub Actions 在原生 macOS arm64 上检查版本和启动接口，结果位于同一次运行的 evidence artifact。真实 QQ 账号登录、消息收发与长期运行仍需后续验收。
