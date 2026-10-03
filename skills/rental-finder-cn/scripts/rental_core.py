"""Offline planning, evidence-aware filtering and reporting. No network or credentials."""
import argparse
import html
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, quote

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'references/catalog.json').read_text(encoding='utf-8'))
TEXT_FIELDS = {'city', 'district', 'rental_type', 'orientation', 'community', 'available_from', 'lease_type'}
BOOL_FIELDS = {'private_bathroom', 'elevator', 'balcony', 'air_conditioner', 'washing_machine',
               'refrigerator', 'kitchen', 'pets_allowed', 'gas', 'residential_utilities'}
NUM_FIELDS = {'rent_monthly', 'mandatory_recurring_monthly', 'variable_monthly', 'deposit',
              'upfront_rent', 'one_time_fees', 'area_sqm', 'bedrooms', 'floor', 'commute_minutes',
              'metro_walk_minutes', 'lease_months'}
FIELDS = TEXT_FIELDS | BOOL_FIELDS | NUM_FIELDS
LABELS = {'city':'城市','district':'区域','rental_type':'租赁方式','orientation':'朝向',
          'private_bathroom':'独卫','elevator':'电梯','pets_allowed':'可养宠物','balcony':'阳台',
          'rent_monthly':'月租','mandatory_recurring_monthly':'其他固定月费',
          'variable_monthly':'月度用量费用','commute_minutes':'通勤分钟','area_sqm':'面积'}
STATUS = {'meets_documented':'页面记载符合', 'needs_verification':'待核实', 'excluded':'不符合'}

def number(v):
    return type(v) in (int, float) and math.isfinite(v) and v >= 0

def safe_url(url):
    if not isinstance(url, str) or re.search(r'[\s\x00-\x1f<>]', url):
        raise ValueError('URL 必须是不含空白的 http(s) 链接')
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        raise ValueError('URL 必须是无凭据的 http(s) 链接')
    return url

def canonical_url(url):
    p = urlsplit(safe_url(url))
    # Preserve query identity (e.g. room=2); only discard known marketing parameters.
    q = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True)
         if not k.lower().startswith('utm_') and k.lower() not in ('gclid','fbclid')]
    return urlunsplit((p.scheme, p.netloc.lower(), p.path or '/', urlencode(q), p.fragment))

def timestamp(value):
    if not isinstance(value, str): raise ValueError('observed_at 必须为含时区的 ISO 时间')
    try: d = datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: raise ValueError('observed_at 不是有效 ISO 时间') from None
    if d.tzinfo is None: raise ValueError('时间必须包含时区，例如 +08:00')
    return d

def check_value(field, value):
    if value is None: return
    if field in NUM_FIELDS and not number(value): raise ValueError(f'{field} 必须为非负有限数字')
    if field in BOOL_FIELDS and type(value) is not bool: raise ValueError(f'{field} 必须为 true/false')
    if field in TEXT_FIELDS and (not isinstance(value,str) or not value.strip()):
        raise ValueError(f'{field} 必须为非空字符串')

def validate_requirements(r):
    if not isinstance(r,dict): raise ValueError('需求必须为 JSON 对象')
    allowed = {'city','budget','hard','preferences','keywords','providers','max_age_days','notes'}
    if set(r)-allowed: raise ValueError('未知需求字段: '+', '.join(sorted(set(r)-allowed)))
    if not isinstance(r.get('city'), str) or not r['city'].strip(): raise ValueError('city 必填')
    b = r.get('budget')
    if not isinstance(b,dict) or set(b) != {'max','basis'} or not number(b['max']):
        raise ValueError('budget 必须包含非负 max 和 basis')
    if b['basis'] not in ('rent','fixed_total','total_monthly'): raise ValueError('未知 budget.basis')
    for group in ('hard','preferences'):
        rules = r.get(group,{})
        if not isinstance(rules,dict): raise ValueError(f'{group} 必须为对象')
        for f,rule in rules.items():
            if f not in FIELDS or f == 'city': raise ValueError(f'未知或重复条件字段: {f}')
            if not isinstance(rule,dict) or set(rule) != {'op','value'}: raise ValueError(f'{f} 条件需 op/value')
            op,v = rule['op'],rule['value']
            if op not in ('eq','in','lte','gte'): raise ValueError(f'{f} 不支持操作符')
            if op in ('lte','gte') and f not in NUM_FIELDS: raise ValueError('大小比较仅支持数字')
            vals = v if op == 'in' else [v]
            if not isinstance(vals,list) or not vals or any(x is None for x in vals): raise ValueError('条件值不能为空')
            for x in vals: check_value(f,x)
    for key in ('keywords','providers'):
        if key in r and (not isinstance(r[key],list) or any(not isinstance(x,str) or not x.strip() for x in r[key])):
            raise ValueError(f'{key} 必须为非空字符串的数组')
    if 'providers' in r and (not r['providers'] or set(r['providers']) - {p['id'] for p in CATALOG['providers']}):
        raise ValueError('providers 为空或含未知来源')
    if not number(r.get('max_age_days',7)): raise ValueError('max_age_days 必须是非负数字')
    return r

def plan(requirements):
    r = validate_requirements(requirements)
    city = r['city'].strip()
    entry = next((x for x in CATALOG['cities'] if x['name'] == city.removesuffix('市')),None)
    selected = r.get('providers',[p['id'] for p in CATALOG['providers'] if p['default']])
    terms = [city, '租房'] + r.get('keywords',[])
    for f in ('district','rental_type'):
        rule = r.get('hard',{}).get(f)
        if rule and rule['op'] == 'eq': terms.append(str(rule['value']))
    queries=[]
    for p in CATALOG['providers']:
        if p['id'] in selected:
            for kind,words in [('targeted',terms),('broad',[city,'租房'])]:
                queries.append({'provider':p['id'],'group':p['group'],'kind':kind,
                                'query':f"site:{p['domain']} " + ' '.join(words)})
    return {'city':city,'coverage': 'jzh_priority' if entry and entry['priority'] else 'jzh_discovery' if entry else 'nationwide_discovery',
            'queries':queries,'budget':r['budget'],'instruction':'用宿主搜索工具实际执行 targeted；结果不足再 broad。查询不等于已检索。'}

def validate_listing(x):
    if not isinstance(x,dict): raise ValueError('每条房源必须是对象')
    for key in ('id','title','source'):
        if not isinstance(x.get(key),str) or not x[key].strip(): raise ValueError(f'房源缺少 {key}')
    safe_url(x.get('url'))
    timestamp(x.get('observed_at'))
    if x.get('evidence_level') not in ('detail','snippet','user_provided'): raise ValueError('未知 evidence_level')
    facts = x.get('facts')
    if not isinstance(facts,dict) or set(facts)-FIELDS: raise ValueError('facts 缺失或包含未知字段')
    for f,v in facts.items():
        if not isinstance(v,dict) or set(v)-{'value','evidence'} or 'value' not in v:
            raise ValueError(f'{f} 事实应包含 value/evidence')
        check_value(f,v['value'])
        if 'evidence' in v and not isinstance(v['evidence'],str): raise ValueError('evidence 必须为原文字符串')

def value(x, field):
    f = x['facts'].get(field,{})
    return f.get('value') if f.get('evidence','').strip() else None

def matches(v,rule):
    if v is None: return None
    return {'eq':lambda: v == rule['value'], 'in':lambda: v in rule['value'],
            'lte':lambda: v <= rule['value'], 'gte':lambda: v >= rule['value']}[rule['op']]()

def evaluate_one(r,x,now):
    validate_listing(x)
    failed,unknown,failed_keys = [],[],[]
    age = (now-timestamp(x['observed_at'])).total_seconds()/86400
    if age < -5/1440: unknown.append('读取时间在未来')
    elif age > r.get('max_age_days',7): unknown.append('读取记录过期，需重新打开')
    if x['evidence_level'] != 'detail': unknown.append('尚无本次可读取详情页证据')
    rules = {'city':{'op':'eq','value':r['city']}, **r.get('hard',{})}
    for f,rule in rules.items():
        matched = matches(value(x,f),rule)
        if matched is False:
            failed.append(f'{LABELS.get(f,f)}不符: {value(x,f)}')
            failed_keys.append(f)
        elif matched is None: unknown.append(f'{LABELS.get(f,f)}缺少证据')
    cost_fields = ['rent_monthly']
    if r['budget']['basis'] != 'rent': cost_fields.append('mandatory_recurring_monthly')
    if r['budget']['basis'] == 'total_monthly': cost_fields.append('variable_monthly')
    costs = [value(x,f) for f in cost_fields]
    known = round(sum(c for c in costs if c is not None),2)
    missing = [f for f,c in zip(cost_fields,costs) if c is None]
    if known > r['budget']['max']:
        failed.append(f'已知月费至少 {known:g} 元，超过预算')
        failed_keys.append('budget')
    elif missing: unknown.append('预算口径缺少: '+', '.join(LABELS.get(f,f) for f in missing))
    prefs = [f for f,rule in r.get('preferences',{}).items() if matches(value(x,f),rule) is True]
    status = 'excluded' if failed else 'needs_verification' if unknown else 'meets_documented'
    return {'id':x['id'],'title':x['title'],'url':x['url'],'source':x['source'],
            'observed_at':x['observed_at'],'status':status,'failed':failed,'failed_keys':failed_keys,'unknown':unknown,
            'cost':{'basis':r['budget']['basis'],'known_min':known,'complete':not missing,'missing':missing},
            'preference_matches':len(prefs),'matched_preferences':prefs,'observations':[x]}

def evaluate(requirements,listings,now=None):
    r = validate_requirements(requirements)
    if not isinstance(listings,list): raise ValueError('房源输入必须为数组')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('now 必须带时区')
    grouped={}; ids=set()
    for x in listings:
        item=evaluate_one(r,x,now)
        if x['id'] in ids: raise ValueError('房源 id 必须唯一')
        ids.add(x['id']); grouped.setdefault(canonical_url(x['url']),[]).append(item)
    results=[]
    for items in grouped.values():
        # Keep the most recently read detail as representative; preserve every observation.
        items.sort(key=lambda z:(z['observations'][0]['evidence_level']=='detail',timestamp(z['observed_at'])),reverse=True)
        item=items[0]
        observations=[i['observations'][0] for i in items]
        conflicts=[]
        for f in FIELDS:
            vals={value(x,f) for x in observations if value(x,f) is not None}
            if len(vals)>1: conflicts.append(f)
        item['observations']=observations
        if conflicts:
            common_failures = set.intersection(*(set(i['failed_keys']) for i in items))
            item['status']='excluded' if common_failures else 'needs_verification'
            item['unknown'].append('同链接记录冲突: '+', '.join(sorted(conflicts)))
        results.append(item)
    order={'meets_documented':0,'needs_verification':1,'excluded':2}
    results.sort(key=lambda z:(order[z['status']],-z['preference_matches'],len(z['unknown']),z['id']))
    return {'generated_at':now.isoformat(),'requirements':r,'input_count':len(listings),
            'unique_count':len(results),'results':results,
            'notice':'页面记载符合不代表房源仍可租；缺费不按零，未自动联系任何人。'}

def escape(s):
    s=html.escape(str(s)).replace('\n',' ').replace('\r',' ')
    return re.sub(r'([\\`*{}_\[\]()|#!])',r'\\\1',s)

def report(data):
    lines=['# 租房候选对比', '', f"生成时间：{data['generated_at']}", '',
           f"预算：{data['requirements']['budget']['max']} 元/月；口径：{data['requirements']['budget']['basis']}。", '',
           f"输入 {data['input_count']} 条，按相同链接合并后 {data['unique_count']} 条。跨站疑似重复需人工核实。", '',data['notice'],'']
    if not data['results']: lines.append('暂无候选；请查看搜索执行记录，不能把未检索当作无房源。')
    for i,x in enumerate(data['results'],1):
        url=quote(safe_url(x['url']),safe=':/?&=%#@+;,~!$*-._')
        lines += [f"## {i}. {escape(x['title'])} · {STATUS[x['status']]}", '',
                  f"来源：[{escape(x['source'])}]({url})；读取：{x['observed_at']}", '',
                  f"预算口径内已知费用：{'合计' if x['cost']['complete'] else '至少'} {x['cost']['known_min']:g} 元/月。偏好命中 {x['preference_matches']} 项。", '']
        for reason in x['failed']+x['unknown']: lines.append('- '+escape(reason))
        lines += ['', '| 页面字段 | 值 | 证据摘录 |','| --- | --- | --- |']
        for f,v in x['observations'][0]['facts'].items():
            lines.append(f"| {escape(LABELS.get(f,f))} | {escape(v['value'])} | {escape(v.get('evidence','待核实'))} |")
        if len(x['observations'])>1: lines += ['',f"保留 {len(x['observations'])} 次原始记录；详情见 JSON。"]
        lines += ['']
    return '\n'.join(lines)+'\n'

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('plan'); p.add_argument('requirements')
    e=sub.add_parser('evaluate'); e.add_argument('requirements'); e.add_argument('listings'); e.add_argument('--now',help='仅用于重放测试的 ISO 时间')
    t=sub.add_parser('report'); t.add_argument('results')
    for p in (p,e,t): p.add_argument('--output',help='新输出文件；拒绝覆盖')
    args=parser.parse_args()
    try:
        if args.command=='plan': out=plan(read_json(args.requirements))
        elif args.command=='evaluate': out=evaluate(read_json(args.requirements),read_json(args.listings),timestamp(args.now) if args.now else None)
        else: out=report(read_json(args.results))
        text=out if isinstance(out,str) else json.dumps(out,ensure_ascii=False,indent=2)+'\n'
        if args.output:
            with Path(args.output).open('x',encoding='utf-8') as f: f.write(text)
        else: print(text,end='')
    except (ValueError, OSError, KeyError, TypeError) as exc: parser.exit(2,f'输入错误: {exc}\n')

if __name__=='__main__': main()
