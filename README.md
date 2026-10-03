# 租房搜寻 rental-finder-cn

一句话描述地点、预算、设施和朝向，让 Codex / WorkBuddy 跨站寻找、核对和对比出租住房。**江浙沪优先，全国可发现；所有推荐都带来源，未知信息明确标注。**

v0.1.0 · MIT · 中文优先 · Python 辅助程序无第三方依赖

> 这是调用宿主联网工具的 Agent Skill。脚本负责查询规划、筛选、去重和报告，不是独立联网爬虫。实际找房需要宿主有搜索/浏览能力。WorkBuddy 包已按官方规范生成，尚未完成客户端实机导入验证。

## 获取源码与安装包

- [GitHub 源码仓库](https://github.com/yhzll99/rental-hunter-skill)
- [v0.1.0 下载页](https://github.com/yhzll99/rental-hunter-skill/releases/tag/v0.1.0)：Codex / WorkBuddy 安装包和 SHA256 校验清单。

仓库名为 `rental-hunter-skill`，安装后的技能名为 `rental-finder-cn`。

```sh
git clone https://github.com/yhzll99/rental-hunter-skill.git
cd rental-hunter-skill
```

## 使用示例

> 帮我找杭州滨江的整租，固定月费总计3500以内，必须朝南、有独卫，最好有电梯。跨几个平台比较，缺信息请标出来。

也可以说：上海张江附近、南京鼓楼、苏州园区、宁波、无锡，或者全国其他城市。城市不明确时会先确认。预算、通勤和宠物的具体含义需要明确；技能不会自动放宽“必须”条件。

输出分为「页面记载符合」「待核实」「不符合」，包含原始链接、费用口径、朝向、设施、读取时间、比较理由和各站访问情况。页面记载符合不等于保证当前在租。

## 安装

### Codex

在仓库目录运行，安装到要使用它的项目的 `.agents/skills`：

```sh
python3 tools/install.py --skills-dir /你的项目路径/.agents/skills
```

也可把 `skills/rental-finder-cn` 完整复制到宿主支持的技能目录；本机旧版本使用 `~/.codex/skills` 时可指定该路径。安装器不覆盖同名技能。重新加载技能或开启新会话后，用 `$rental-finder-cn` 或直接描述租房需求。详见 [OpenAI 技能文档](https://learn.chatgpt.com/docs/build-skills)。

提供的 Codex ZIP 以 SKILL.md 为根，手工解压时应放入名为 `rental-finder-cn` 的技能文件夹，不要把所有文件散放到 skills 根目录。

### WorkBuddy

使用 `rental-finder-cn-workbuddy-0.1.0.zip`，在「技能 → 添加技能 → 上传技能」导入。包根目录包含 SKILL.md，含 description_zh、description_en、version 和 author 等开放平台字段。导入后的权限、联网工具和 Python 环境由客户端决定。

依据：[WorkBuddy 技能安装](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) · [开放平台包格式](https://open.workbuddy.cn/en/docs/skill)。客户端未实测，不能宣称认证兼容；遇到导入错误请提交脱敏错误和客户端版本。

## 不安装也能试运行

要求 Python 3.10+。以下只是离线合成示例，**不会真的找到这些房源**：

```sh
python3 skills/rental-finder-cn/scripts/rental_core.py plan examples/requirements.json
python3 skills/rental-finder-cn/scripts/rental_core.py evaluate examples/requirements.json examples/listings.synthetic.json --now 2026-10-03T10:00:00Z --output results.json
python3 skills/rental-finder-cn/scripts/rental_core.py report results.json --output report.md
```

实时任务应由 AI 执行搜索、打开详情并填入真实候选 JSON；不要传 `--now`。输出文件存在时会拒绝覆盖。字段详见 [数据协议](skills/rental-finder-cn/references/data-contract.md)。

## 首版能力与边界

- 江浙沪25城目录，上海/杭州/南京/苏州/宁波/无锡为优先验证城市；全国其他城市走城市名发现模式。
- 默认贝壳、自如、58，按需补充链家、安居客、我爱我家、豆瓣、小红书。来源策略不是专用爬虫适配器；实际访问结果逐次报告。
- 条件、预算、设施、朝向支持确定性比较；缺失和过期不会判成符合。
- 相同链接去跟踪参数合并，冲突保留；跨站疑似重复由 AI 核对，不能靠同小区同面积自动合并。
- 复杂日期、宠物种类、带时段通勤需要 AI 核验；不保证地图路线，不自动联系房东或支付。
- 网站可能限制登录、抓取或索引。遵守平台规则和当前访问权限；不会绕过验证码，也不保证找到所有网站的全部房源。

## 开发、打包和开源

```sh
python3 -m unittest discover -s tests -v
python3 tools/package.py --output dist
```

同一源码生成两个 ZIP 和 SHA256 清单；已有同名包会拒绝覆盖。运行环境和脚本输出不需要密钥。CI 配置覆盖 macOS、Windows、Linux 与 Python 3.10/3.13，只有真实运行过才能宣称对应平台通过。

阅读 [实施计划与全国路线](docs/PLAN.md)、[验证记录](docs/VALIDATION.md)、[贡献指南](CONTRIBUTING.md) 和 [发布清单](docs/RELEASE.md)。源码默认不携带真实租客数据或房东联系方式，MIT 只授权本项目代码和文档，不授予第三方房源数据权利。
