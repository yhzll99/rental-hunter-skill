# 验证记录

验证日期：2026-10-03。这是首版能力边界记录，不是房源推荐报告。

## 本地逻辑与分发

最终本地测试：27项通过（macOS，Python 3.12.14；另在系统 Python 3.9 上也运行通过，但项目支持基线仍为3.10+）。官方 skill-creator 的 quick_validate 返回 Skill is valid。

独立源码审阅发现数值3200与3200.0因字符串比较误判为冲突；已补失败回归并改为按数值相等判断。未发现其他新的高/中优先级问题。

- 单元测试覆盖费用缺失/超额、朝向精确匹配、软硬条件、摘要/过期/未来时间、证据缺失、城市不符、同链接冲突、查询参数保留、输入错误、全国发现、25城目录、报告转义、安装覆盖保护和双包结构。
- 测试先运行到模块缺失失败，再实现；独立试用发现同链接偏好冲突导致超预算排除失效，补回归测试复现后修复。冲突记录存在所有观察都支持的同一硬条件失败时，保留排除状态；其他冲突待核实。
- 独立离线代理按 Skill 完成 plan / evaluate / report，四条合成记录为1符合、2待核实、1排除。代理未修改源码。
- 无技能基线在相同领域的简短案例中已经能正确识别缺费和硬条件，并未观察到模型基础判断失败。此次 Skill 的增量是可复现流程、共享字段、来源执行记录和确定性辅助程序；不能据此声称它提高了真实找房成功率。
- 自动 Markdown 是中间候选对比；最终答复还需 AI 加上搜索执行记录、推荐理由和具体核实问题，SKILL.md 已明确规定。

## 在线抽测（宿主 web 搜索/读取）

下列链接来自实际搜索或导航，未保存联系方式或完整网页。读取成功只代表工具返回内容，可能来自索引缓存；不代表浏览器直连或当前库存已确认。

| 城市/来源 | 实际访问页面 | 观察 | 结论 |
| --- | --- | --- | --- |
| 上海/安居客 | https://sh.zu.anjuke.com/ | 返回城市租房列表 | 入口和列表可发现，未逐条确认 |
| 杭州/贝壳 | https://hz.zu.ke.com/zufang | 返回租房列表和详情链接 | 可发现列表 |
| 杭州/贝壳公寓 | https://hz.zu.ke.com/apartment/58500.html | 点击列表后重定向至登录 | 仅线索，不能提取成已核验详情 |
| 杭州/贝壳详情 | https://hz.zu.ke.com/zufang/HZ1844243717200805888.html | 读取超时 | 访问受限，不代表房源失效 |
| 苏州/58 | https://su.zf.58.com/ | 搜索返回租房列表字段 | 搜索可发现，未完成详情核验 |
| 南京/安居客 | https://nj.zu.anjuke.com/ | 搜索返回列表，后续打开报错 | 仅搜索结果可用 |
| 宁波/贝壳 | https://nb.zu.ke.com/wzdt/ | 返回城区与租房导航 | 城市入口验证，非房源验证 |
| 无锡/贝壳 | https://wx.zu.ke.com/truehouse/content | 返回平台租房服务规则 | 仅城市站发现，未验证房源列表 |
| 自如 | https://www.ziroom.com/ | 读取报错，定向检索未取得可用详情 | 未验证详情访问；运行时需其他来源补位 |

没有完成六城全流程成功验收，没有获取三家平台详情均可读取的证据。不把“城市已配置”写成“该城全部平台已接入”。

## 宿主规范

- [OpenAI Build skills](https://learn.chatgpt.com/docs/build-skills)：读取了 SKILL.md 格式、.agents/skills 发现路径与 openai.yaml 说明。
- [WorkBuddy 技能安装](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)：支持导入本地技能包。
- [WorkBuddy Open Platform Skill](https://open.workbuddy.cn/en/docs/skill)：检查了 description_zh / description_en / version / author 等要求；WorkBuddy ZIP 单独注入这些元数据。

WorkBuddy 客户端实机导入、技能市场审核、Windows/Linux CI、真实租房转化率仍未验证。包结构检查不能代替客户端验收。初版本地验收未进行消息发送、预约、付费或登录绕过。后续 GitHub 开源发布记录见 [RELEASE.md](RELEASE.md)，跨平台运行状态见仓库 Actions。
