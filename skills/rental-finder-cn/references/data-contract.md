# 数据协议 v1

脚本仅确定性处理已提取的事实，AI 负责提取及核验证据。使用 Python 3.10+ 标准库，无外部依赖。脚本位置相对本技能目录：`scripts/rental_core.py`。

## 需求 JSON

```json
{
  "city": "杭州",
  "budget": {"max": 3500, "basis": "fixed_total"},
  "hard": {
    "district": {"op": "eq", "value": "滨江"},
    "rental_type": {"op": "eq", "value": "整租"},
    "orientation": {"op": "eq", "value": "南"},
    "private_bathroom": {"op": "eq", "value": true}
  },
  "preferences": {"elevator": {"op": "eq", "value": true}},
  "max_age_days": 7
}
```

city、budget 必填，其余可省略。city 使用确认后的标准名称，如杭州；需求和事实都用相同名称。`keywords` 为额外搜索词字符串数组；`providers` 为 catalog 中的来源 id 数组；`notes` 保存无法自动比较的限制，并由 AI 手工检查。任何硬条件没有被脚本表达时，即使脚本返回符合，最终仍需人工核验该条件。

- `rent`：只比较月租。
- `fixed_total`：月租 + mandatory_recurring_monthly（全部其他固定月费合计）。
- `total_monthly`：再加 variable_monthly（水电燃气等用量费用，只有明确包干才可据此确认总额；估算须在报告中标明且最终仍待核实）。

金额单位人民币元/月；年固定费除以12，租期内一次性费另列，未写不能填0。押金、预付租金、一次性中介费分别用 deposit / upfront_rent / one_time_fees。首付款可由 AI 将三项及实际首期固定费相加，缺项就显示下限和未包含项目。

硬条件和偏好格式为字段名 → `{op,value}`。op：eq 精确相等；in 接受列表中的任意一个值；lte/gte 仅数值。偏好目前等权，按命中项数排序，没有假精度百分比分。地区多个可接受用 in，朝向“南北”和“南”不同。

## 房源数组 JSON

每条必填 id（本次唯一）、title、url、source、observed_at（带时区）、evidence_level、facts。url 是实际来源页面，仅接受 http/https。evidence_level：detail / snippet / user_provided；后两类不能自动进入页面记载符合。

```json
[{
  "id": "demo-1",
  "title": "模拟房源，非真实推荐",
  "url": "https://example.com/rental/1",
  "source": "模拟平台",
  "observed_at": "2026-10-03T18:00:00+08:00",
  "evidence_level": "detail",
  "facts": {
    "city": {"value": "杭州", "evidence": "模拟文本：杭州"},
    "rent_monthly": {"value": 3200, "evidence": "模拟文本：租金3200元/月"}
  }
}]
```

每个事实含 `value` 和 `evidence`（同一页面支持该值的短原文）；缺证据即未知。事实不能用模型常识补全。不同来源证据分成不同 observation，不混入当前链接。相同链接不同观察使用不同 id；冲突不自动覆盖。原始 JSON 保留全部事实，Markdown 显示代表记录和冲突提示。

| 类型 | 支持字段 |
| --- | --- |
| 字符串 | city, district, rental_type, orientation, community, available_from, lease_type |
| 布尔 | private_bathroom, elevator, balcony, air_conditioner, washing_machine, refrigerator, kitchen, pets_allowed, gas, residential_utilities |
| 非负数字 | rent_monthly, mandatory_recurring_monthly, variable_monthly, deposit, upfront_rent, one_time_fees, area_sqm, bedrooms, floor, commute_minutes, metro_walk_minutes, lease_months |

未知字段拒绝，避免拼错条件被忽略。楼层负数/地下室用 notes 保留并手工筛选。pets_allowed=true 必须与用户宠物类型相符：仅“允许小型犬”不能推为允许猫。入住日期先保留 ISO 日期，首版仅支持精确/列表匹配，早晚日期和复杂租期由 AI 核验。通勤数字必须对应用户的交通方式、目的地和时段，详细证据写在 evidence。

## 命令

```sh
python3 <技能目录>/scripts/rental_core.py plan requirements.json --output search-plan.json
python3 <技能目录>/scripts/rental_core.py evaluate requirements.json listings.json --output results.json
python3 <技能目录>/scripts/rental_core.py report results.json --output report.md
```

输出存在时拒绝覆盖，改用新文件名。`evaluate --now` 只用于历史/合成测试；实时搜房不使用。CLI 返回码 0 成功、2 输入错误。

结果状态：meets_documented 页面记载符合；needs_verification 缺证据/过期/冲突；excluded 硬条件明确不符。known_min 是预算口径的已知费用下限；complete 只说明该口径字段齐全，不保证房源真实性。脚本不会核验文本真假、实时库存、照片真实性或跨站是否同一套房。
