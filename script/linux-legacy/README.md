# LLBot 7.12.15 Linux CLI 完整配套包

包含相同架构的 QQ 3.2.23-44343、Node、PMHQ 7.3.2、FFmpeg 和 FFprobe。组件下载来源、版本与哈希保存在 COMPONENTS.json。

修正了首次连接 PMHQ 时账号信息尚未返回便读取 online 字段的异常，此时继续等待并重试。修改后的主程序哈希记录在 COMPONENTS.json。

在 Ubuntu 24.04 解压后，首次运行 `./install-dependencies.sh` 安装系统图形库和 Xvfb，并配置随包 QQ 的 sandbox 权限。安装需要 sudo。无显示器时运行 `xvfb-run -a ./start.sh`，有桌面时运行 `./start.sh`。

启动脚本按当前目录指定随包 QQ。退出其他 QQ 和 LLBot 后使用，避免进程和端口冲突。更新组件会改变这套旧版配合关系，请保留当前版本配置。QQ 自身的热更新也可能改变兼容性。

GitHub Actions 在对应架构进行无账号启动验证，结果保存在同一 artifact 的 evidence 目录。登录、收发和长期运行仍需使用者验证。包内仅包含程序文件，首次运行时 QQ 可能恢复电脑已有的登录状态。

此包面向 Ubuntu 24.04。其他 Linux 发行版需要安装对应的系统依赖。随包保留原组件的版权文件和媒体工具说明。
