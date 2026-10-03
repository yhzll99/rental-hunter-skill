# v0.1.0 开源发布

源码仓库：[yhzll99/rental-hunter-skill](https://github.com/yhzll99/rental-hunter-skill)。技能名为 `rental-finder-cn`，采用 MIT 许可证。

[下载 v0.1.0](https://github.com/yhzll99/rental-hunter-skill/releases/tag/v0.1.0)，附件包括 Codex ZIP、WorkBuddy ZIP 和 `SHA256SUMS.json`；GitHub 同时提供对应版本的源码 ZIP / tar.gz。

## 本版验证

- 发布前重新运行 27 项测试，全部通过；双包 ZIP 完整性及内容结构检查通过。
- macOS、Windows、Linux 和 Python 3.10 / 3.13 的结果以 [GitHub Actions](https://github.com/yhzll99/rental-hunter-skill/actions) 为准。
- WorkBuddy 尚未完成客户端实机导入验证；包格式校验不代表认证兼容。
- 详细能力与在线抽测边界见 [VALIDATION.md](VALIDATION.md)。

## 使用边界

由宿主联网工具驱动，不是独立爬虫，也不是全站 API 集成。网站登录和读取限制可能影响结果；页面记载符合不保证当前仍可租。不自动联系房东或支付。

MIT 仅覆盖本项目代码和文档，不授予第三方房源数据权利。本次只发布 GitHub，不包含技能市场上架或社区推广。

## 后续发布流程

运行测试、技能格式校验与双包生成；审查真实找房记录、密钥及联系方式排除情况；核对已验证范围后创建版本标签和 Release，并附包文件及校验清单。
