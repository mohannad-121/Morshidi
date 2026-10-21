import json, csv, os, sys
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DIR = os.path.dirname(os.path.abspath(__file__))
if DIR not in sys.path:
    sys.path.insert(0, DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(DIR))
out = os.path.join(REPO_ROOT, "data", "curricula")
os.makedirs(out, exist_ok=True)
plans_dir = os.path.join(out, "plans")
os.makedirs(plans_dir, exist_ok=True)

from it_science import plans as p1
from arts_business import plans as p2
from media_law_nursing import plans as p3
plans = p1 + p2 + p3

# add canonical internal identity, preserve user-supplied Arabic data
for p in plans:
    p['plan_key']=f"ZU:{p['faculty_code']}:{p['major_code']}:P{p['plan_number']}"
    p['computed_total_required_credits']=sum(g[4] for g in p['groups'])
    groups=[]
    for i,g in enumerate(p['groups'],1):
        code,name,scope,typ,hours,courses,*policy=g
        groups.append({
            'group_code':code,'name_ar':name,'scope':scope,'requirement_type':typ,
            'required_credit_hours':hours,'display_order':i,'courses':courses,
            'selection_policy':policy[0] if policy else 'plan_membership',
            'selection_policy_status':policy[1] if len(policy) > 1 else 'available',
        })
    p['groups']=groups

# global catalog candidates + conflicts
catalog={}
conflicts=[]
plan_courses=[]
prereq_refs=set()
for p in plans:
    order=0
    for g in p['groups']:
        for course in g['courses']:
            order += 1
            code=course['course_code']
            base={'course_code':code,'name_ar':course['name_ar']}
            if code not in catalog:
                catalog[code]=base
            elif catalog[code]['name_ar'] != course['name_ar']:
                conflicts.append({'course_code':code,'field':'name_ar','values':[catalog[code]['name_ar'],course['name_ar']], 'plan_key':p['plan_key']})
            raw=course.get('raw_prerequisite_text')
            deps=[] if not raw else [x.strip() for x in raw.split(',') if x.strip()]
            for d in deps:
                if d != '0000000': prereq_refs.add(d)
            if not raw:
                logic='not_applicable'; review=False; reason=None
            elif raw == '0000000' or '0000000' in deps:
                logic='unresolved'; review=True; reason='SOURCE_SENTINEL_0000000_REQUIRES_SEMANTIC_VERIFICATION'
            elif len(deps)==1:
                logic='verified'; review=False; reason=None
            else:
                logic='unresolved'; review=True; reason='MULTI_CODE_SOURCE_DOES_NOT_STATE_AND_OR_SEMANTICS'
            plan_courses.append({
                'plan_key':p['plan_key'],'faculty_ar':p['faculty_ar'],'major_ar':p['major_ar'],'plan_number':p['plan_number'],
                'group_code':g['group_code'],'group_name_ar':g['name_ar'],'requirement_type':g['requirement_type'],'scope':g['scope'],
                'display_order':order, **course,'prerequisite_codes':deps,'prerequisite_logic_status':logic,
                'review_required':review,'review_reason':reason
            })

referenced_only=sorted(prereq_refs-set(catalog))
required_group_validation=[]
for p in plans:
    for g in p['groups']:
        listed=sum(float(c['credit_hours']) for c in g['courses'])
        if g['requirement_type']=='required':
            ok=listed==float(g['required_credit_hours'])
        elif g['requirement_type']=='free_elective' and g['selection_policy_status']=='policy_required':
            ok=listed==0
        else:
            ok=listed>=float(g['required_credit_hours'])
        required_group_validation.append({'plan_key':p['plan_key'],'group_code':g['group_code'],'requirement_type':g['requirement_type'],'required_credit_hours':g['required_credit_hours'],'listed_option_credit_sum':listed,'valid_by_basic_sum_rule':ok})

registry={
 'schema_version':'MORSHIDI_MULTI_PLAN_SOURCE_V1',
 'university':{'id':'10000000-0000-0000-0000-000000000001','name_ar':'جامعة الزرقاء','name_en':'Zarqa University'},
 'identity_rule':'plan identity = university + faculty/major + plan_number; plan_number alone is NOT unique',
 'source_note':'New plan data transcribed from user-supplied tables in this conversation. No outside corrections applied.',
 'existing_plan_not_reseeded':{'plan_key':'ZU:IT:AI:P12','faculty_ar':'كلية تكنولوجيا المعلومات','major_ar':'الذكاء الاصطناعي','major_code':'AI','plan_number':'12','morshidi_existing_plan_id':'10000000-0000-0000-0000-000000000005','computed_total_required_credits':132},
 'plans':plans,
 'referenced_only_prerequisite_course_codes':referenced_only,
 'name_conflicts':conflicts,
 'validation':required_group_validation
}
with open(os.path.join(out, 'canonical_curriculum.json'), 'w', encoding='utf-8') as f:
    json.dump(registry, f, ensure_ascii=False, indent=2)

for p in plans:
    fname = p['plan_key'].replace(':', '_') + '.json'
    with open(os.path.join(plans_dir, fname), 'w', encoding='utf-8') as pf:
        json.dump(p, pf, ensure_ascii=False, indent=2)

# CSVs
fields = ['plan_key', 'faculty_ar', 'major_ar', 'plan_number', 'group_code', 'group_name_ar', 'requirement_type', 'scope', 'display_order', 'course_code', 'name_ar', 'credit_hours', 'raw_prerequisite_text', 'prerequisite_logic_status', 'review_required', 'review_reason', 'learning_type', 'delivery_mode']
with open(os.path.join(out, 'plan_courses.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in plan_courses:
        w.writerow({k: r.get(k) for k in fields})
with open(os.path.join(out, 'courses.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['course_code', 'name_ar', 'catalog_status'])
    w.writeheader()
    for code, row in sorted(catalog.items()):
        w.writerow({'course_code': code, 'name_ar': row['name_ar'], 'catalog_status': 'known'})
    for code in referenced_only:
        w.writerow({'course_code': code, 'name_ar': '', 'catalog_status': 'referenced_only'})
with open(os.path.join(out, 'plans.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['plan_key', 'faculty_code', 'faculty_ar', 'major_code', 'major_ar', 'plan_number', 'computed_total_required_credits'])
    w.writeheader()
    w.writerow({'plan_key': 'ZU:IT:AI:P12', 'faculty_code': 'IT', 'faculty_ar': 'كلية تكنولوجيا المعلومات', 'major_code': 'AI', 'major_ar': 'الذكاء الاصطناعي', 'plan_number': '12', 'computed_total_required_credits': 132})
    for p in plans:
        w.writerow({k: p[k] for k in w.fieldnames})
with open(os.path.join(out, 'data_quality_issues.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        fields2=['issue_type','plan_key','course_code','details']
        w=csv.DictWriter(f,fieldnames=fields2); w.writeheader()
        for r in plan_courses:
            if r['review_required']:
                w.writerow({'issue_type':'PREREQUISITE_SEMANTICS_UNRESOLVED','plan_key':r['plan_key'],'course_code':r['course_code'],'details':f"{r['raw_prerequisite_text']} | {r['review_reason']}"})
        for code in referenced_only:
            w.writerow({'issue_type':'REFERENCED_ONLY_COURSE','plan_key':'','course_code':code,'details':'Prerequisite code referenced by supplied plan but not listed as a course in any newly supplied plan.'})
        for v in required_group_validation:
            if not v['valid_by_basic_sum_rule']:
                w.writerow({'issue_type':'GROUP_CREDIT_SUM_MISMATCH','plan_key':v['plan_key'],'course_code':'','details':f"{v['group_code']}: required={v['required_credit_hours']} listed_sum={v['listed_option_credit_sum']}"})
        for x in conflicts:
            w.writerow({'issue_type':'COURSE_NAME_CONFLICT','plan_key':x['plan_key'],'course_code':x['course_code'],'details':' | '.join(x['values'])})

print('plans',len(plans)+1,'new_plans',len(plans),'plan_course_rows',len(plan_courses),'unique_new_courses',len(catalog),'referenced_only',len(referenced_only),'conflicts',len(conflicts))
print('totals',[(p['major_ar'],p['computed_total_required_credits']) for p in plans])
print('invalid_groups',[v for v in required_group_validation if not v['valid_by_basic_sum_rule']])
