import json, os, uuid, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(DIR))
DATA_DIR = os.path.join(REPO_ROOT, "data", "curricula")
with open(os.path.join(DATA_DIR, 'canonical_curriculum.json'), encoding='utf-8') as f: data = json.load(f)
UNI = data['university']['id']; NS = uuid.UUID(UNI)
def uid(kind, key): return str(uuid.uuid5(NS, f'{kind}:{key}'))
def q(s): return "null" if s is None else "'" + str(s).replace("'", "''") + "'"
plans = data['plans']
faculty_ids={'IT':'10000000-0000-0000-0000-000000000002'}
for p in plans:
    faculty_ids.setdefault(p['faculty_code'],uid('faculty',p['faculty_code']))
major_ids={p['plan_key']:uid('major',p['faculty_code']+':'+p['major_code']) for p in plans}
plan_ids={p['plan_key']:uid('plan',p['plan_key']) for p in plans}
source_ids={p['plan_key']:uid('source',p['plan_key']) for p in plans}
lines=[]
A=lines.append
A('-- Generated from user-supplied study-plan tables. No external corrections applied.')
A('-- IMPORTANT: all new plans share plan_number=12; identity must use major + plan number, never plan number alone.')
A('-- Multi-code prerequisites are intentionally NOT modeled as executable dependencies until AND/OR semantics are verified.')
A('begin;\n')
A("update public.faculties set code = coalesce(code, 'IT') where id = '10000000-0000-0000-0000-000000000002';")
A("update public.majors set code = coalesce(code, 'AI') where id = '10000000-0000-0000-0000-000000000003';\n")
# faculties
for fc in sorted({p['faculty_code'] for p in plans if p['faculty_code']!='IT'}):
    p=next(x for x in plans if x['faculty_code']==fc)
    A(f"insert into public.faculties (id,university_id,code,name_ar,active) values ({q(faculty_ids[fc])},{q(UNI)},{q(fc)},{q(p['faculty_ar'])},true) on conflict (id) do nothing;")
A('')
# majors, sources, plans, groups
for p in plans:
    pk=p['plan_key']; mid=major_ids[pk]; pid=plan_ids[pk]; sid=source_ids[pk]; fid=faculty_ids[p['faculty_code']]
    A(f"insert into public.majors (id,faculty_id,code,name_ar,active) values ({q(mid)},{q(fid)},{q(p['major_code'])},{q(p['major_ar'])},true) on conflict (id) do nothing;")
    title=f"User-supplied {p['major_ar']} study plan {p['plan_number']}"
    note='Supplied in ChatGPT conversation on 2026-10-16; not independently source-verified. Course/prerequisite text preserved as supplied.'
    A(f"insert into public.academic_sources (id,university_id,source_type,title,plan_number,source_status,notes) values ({q(sid)},{q(UNI)},'manual_verification',{q(title)},{q(p['plan_number'])},'unknown',{q(note)}) on conflict (id) do nothing;")
    A(f"insert into public.study_plans (id,major_id,plan_number,total_credit_hours,status,source_id,notes) values ({q(pid)},{q(mid)},{q(p['plan_number'])},{p['computed_total_required_credits']},'unknown',{q(sid)},{q('Total credits computed from supplied requirement-group headers.')}) on conflict (id) do nothing;")
    for g in p['groups']:
        gid=uid('group',pk+':'+g['group_code'])
        A(f"insert into public.requirement_groups (id,study_plan_id,group_code,name_ar,scope,requirement_type,selection_policy,selection_policy_status,required_credit_hours,display_order,active) values ({q(gid)},{q(pid)},{q(g['group_code'])},{q(g['name_ar'])},{q(g['scope'])},{q(g['requirement_type'])},{q(g['selection_policy'])},{q(g['selection_policy_status'])},{g['required_credit_hours']},{g['display_order']},true) on conflict (study_plan_id,group_code) do update set name_ar=excluded.name_ar,requirement_type=excluded.requirement_type,selection_policy=excluded.selection_policy,selection_policy_status=excluded.selection_policy_status,required_credit_hours=excluded.required_credit_hours;")
    A('')
# courses via temp table
known={}
for p in plans:
  for g in p['groups']:
    for c in g['courses']: known.setdefault(c['course_code'],c['name_ar'])
refs=data['referenced_only_prerequisite_course_codes']
A('create temporary table _multi_plan_courses (course_code text primary key, name_ar text, catalog_status text not null) on commit drop;')
A('insert into _multi_plan_courses values')
vals=[]
for code,name in sorted(known.items()): vals.append(f"  ({q(code)},{q(name)},'known')")
for code in refs:
    if code not in known: vals.append(f"  ({q(code)},null,'referenced_only')")
A(',\n'.join(vals)+';')
A(f"""insert into public.courses (university_id,course_code,name_ar,catalog_status,active)
select {q(UNI)},course_code,name_ar,catalog_status,true
from _multi_plan_courses
on conflict (university_id,course_code) do update
set name_ar = case
      when public.courses.catalog_status in ('referenced_only','unknown')
       and excluded.name_ar is not null then excluded.name_ar
      else public.courses.name_ar
    end,
    catalog_status = case
      when excluded.catalog_status='known' and public.courses.catalog_status <> 'known' then 'known'
      else public.courses.catalog_status
    end,
    active = true;
""")
# plan courses temp
A('create temporary table _multi_plan_course_seed (plan_id uuid, source_id uuid, group_code text, course_code text, credit_hours numeric(6,2), learning_type text, delivery_mode text, raw_prerequisite_text text, prerequisite_logic_status text, display_order integer, verification_status text) on commit drop;')
A('insert into _multi_plan_course_seed values')
vals=[]
for p in plans:
    pid=plan_ids[p['plan_key']]; sid=source_ids[p['plan_key']]
    for g in p['groups']:
        for c in g['courses']:
            raw=c.get('raw_prerequisite_text')
            deps=[] if not raw else [x.strip() for x in raw.split(',') if x.strip()]
            logic='not_applicable' if not raw else ('verified' if len(deps)==1 and deps[0] != '0000000' else 'unresolved')
            vals.append(f"  ({q(pid)}::uuid,{q(sid)}::uuid,{q(g['group_code'])},{q(c['course_code'])},{c['credit_hours']},{q(c['learning_type'])},{q(c['delivery_mode'])},{q(raw)},{q(logic)},{c.get('display_order',0) or 0},'needs_review')")
# display order is absent in nested c; recalc per plan
# rewrite with actual sequential display order
vals=[]
for p in plans:
    pid=plan_ids[p['plan_key']]; sid=source_ids[p['plan_key']]; order=0
    for g in p['groups']:
        for c in g['courses']:
            order+=1; raw=c.get('raw_prerequisite_text'); deps=[] if not raw else [x.strip() for x in raw.split(',') if x.strip()]
            logic='not_applicable' if not raw else ('verified' if len(deps)==1 and deps[0] != '0000000' else 'unresolved')
            vals.append(f"  ({q(pid)}::uuid,{q(sid)}::uuid,{q(g['group_code'])},{q(c['course_code'])},{c['credit_hours']},{q(c['learning_type'])},{q(c['delivery_mode'])},{q(raw)},{q(logic)},{order},'needs_review')")
A(',\n'.join(vals)+';')
A(f"""insert into public.study_plan_courses (study_plan_id,course_id,requirement_group_id,credit_hours,learning_type,delivery_mode,raw_prerequisite_text,prerequisite_logic_status,verification_status,source_id,display_order,active)
select s.plan_id,c.id,g.id,s.credit_hours,s.learning_type,s.delivery_mode,s.raw_prerequisite_text,s.prerequisite_logic_status,s.verification_status,s.source_id,s.display_order,true
from _multi_plan_course_seed s
join public.courses c on c.university_id={q(UNI)} and c.course_code=s.course_code
join public.requirement_groups g on g.study_plan_id=s.plan_id and g.group_code=s.group_code
on conflict (study_plan_id,course_id) do nothing;\n""")
# single prereq mappings
A('create temporary table _multi_plan_single_prereq (plan_id uuid, target_course_code text, prerequisite_course_code text) on commit drop;')
A('insert into _multi_plan_single_prereq values')
vals=[]
for p in plans:
    pid=plan_ids[p['plan_key']]
    for g in p['groups']:
        for c in g['courses']:
            raw=c.get('raw_prerequisite_text'); deps=[] if not raw else [x.strip() for x in raw.split(',') if x.strip()]
            if len(deps)==1 and deps[0]!='0000000': vals.append(f"  ({q(pid)}::uuid,{q(c['course_code'])},{q(deps[0])})")
A(',\n'.join(vals)+';')
A(f"""insert into public.course_dependency_groups (study_plan_course_id,dependency_type,group_number,verification_status)
select spc.id,'prerequisite',1,'verified'
from _multi_plan_single_prereq s
join public.courses tc on tc.university_id={q(UNI)} and tc.course_code=s.target_course_code
join public.study_plan_courses spc on spc.study_plan_id=s.plan_id and spc.course_id=tc.id
on conflict (study_plan_course_id,dependency_type,group_number) do nothing;""")
A(f"""insert into public.course_dependency_options (dependency_group_id,dependency_course_id,verification_status)
select dg.id,pc.id,case when pc.catalog_status='referenced_only' then 'referenced_only' else 'verified' end
from _multi_plan_single_prereq s
join public.courses tc on tc.university_id={q(UNI)} and tc.course_code=s.target_course_code
join public.study_plan_courses spc on spc.study_plan_id=s.plan_id and spc.course_id=tc.id
join public.course_dependency_groups dg on dg.study_plan_course_id=spc.id and dg.dependency_type='prerequisite' and dg.group_number=1
join public.courses pc on pc.university_id={q(UNI)} and pc.course_code=s.prerequisite_course_code
on conflict (dependency_group_id,dependency_course_id) do nothing;\n""")
A('commit;')
A('\n-- Generated plan IDs for application wiring / tests:')
for p in plans: A(f"-- {p['plan_key']} = {plan_ids[p['plan_key']]} ({p['major_ar']})")
with open(os.path.join(DATA_DIR, 'morshidi_multi_plan_seed.sql'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
plan_ids_obj = {'existing_ai': '10000000-0000-0000-0000-000000000005', 'new_plans': {p['plan_key']: plan_ids[p['plan_key']] for p in plans}}
with open(os.path.join(DATA_DIR, 'morshidi_plan_ids.json'), 'w', encoding='utf-8') as f:
    json.dump(plan_ids_obj, f, ensure_ascii=False, indent=2)
print('sql lines', len(lines), 'bytes', os.path.getsize(os.path.join(DATA_DIR, 'morshidi_multi_plan_seed.sql')))
