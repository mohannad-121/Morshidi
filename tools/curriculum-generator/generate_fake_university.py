import json, os, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(DIR))
DATA_DIR = os.path.join(REPO_ROOT, "data", "curricula")
with open(os.path.join(DATA_DIR, 'canonical_curriculum.json'), encoding='utf-8') as f: d = json.load(f)
plans = d['plans']
def q(s): return 'null' if s is None else "'" + str(s).replace("'", "''") + "'"
# JSON registry in a university-friendly shape
registry = {'schemaVersion': 'FAKE_UNIVERSITY_MULTI_CURRICULUM_V1', 'university': 'جامعة الزرقاء', 'existingAiPlanKey': 'ZU:IT:AI:P12', 'plans': []}
for p in plans:
  rp={'planKey':p['plan_key'],'facultyCode':p['faculty_code'],'faculty':p['faculty_ar'],'majorCode':p['major_code'],'major':p['major_ar'],'planNumber':p['plan_number'],'totalRequiredCredits':p['computed_total_required_credits'],'requirementGroups':[]}
  for g in p['groups']:
    rg={'code':g['group_code'],'name':g['name_ar'],'scope':g['scope'],'type':g['requirement_type'],'requiredCredits':g['required_credit_hours'],'selectionPolicy':g['selection_policy'],'selectionPolicyStatus':g['selection_policy_status'],'courses':[]}
    for c in g['courses']:
      raw=c.get('raw_prerequisite_text'); deps=[] if not raw else [x.strip() for x in raw.split(',') if x.strip()]
      rg['courses'].append({'code':c['course_code'],'name':c['name_ar'],'credits':c['credit_hours'],'prerequisites':deps,'rawPrerequisiteText':raw,'prerequisiteLogicStatus':'not_applicable' if not raw else ('verified' if len(deps)==1 and deps[0] != '0000000' else 'unresolved'),'reviewRequired':bool(raw and (len(deps)!=1 or deps[0]=='0000000')),'learningType':c['learning_type'],'deliveryMode':c['delivery_mode']})
    rp['requirementGroups'].append(rg)
  registry['plans'].append(rp)
with open(os.path.join(DATA_DIR, 'fake_university_curriculum_registry.json'), 'w', encoding='utf-8') as f:
    json.dump(registry, f, ensure_ascii=False, indent=2)
# SQL migration for dedicated plan-aware curriculum tables
L=[];A=L.append
A('-- Fake University multi-major/multi-plan curriculum foundation.')
A('-- Adds plan-aware curriculum tables. It does NOT replace the current runtime path by itself; server code must switch to plan_key-aware reads before adding global course rows.')
A('begin;')
A('''create table if not exists public.curriculum_faculties (
  faculty_code text primary key,
  name_ar text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);''')
A('''create table if not exists public.curriculum_majors (
  major_code text primary key,
  faculty_code text not null references public.curriculum_faculties(faculty_code) on delete restrict,
  name_ar text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);''')
A('''create table if not exists public.curriculum_plans (
  plan_key text primary key,
  major_code text not null references public.curriculum_majors(major_code) on delete restrict,
  plan_number text not null,
  total_required_credits numeric(6,2) not null check (total_required_credits >= 0),
  active boolean not null default true,
  source_status text not null default 'user_supplied_unverified',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(major_code,plan_number)
);''')
A('''create table if not exists public.curriculum_requirement_groups (
  plan_key text not null references public.curriculum_plans(plan_key) on delete cascade,
  group_code text not null,
  name_ar text not null,
  scope text not null,
  requirement_type text not null check (requirement_type in ('required','elective','free_elective')),
  selection_policy text not null default 'plan_membership' check (selection_policy in ('plan_membership','university_approved')),
  selection_policy_status text not null default 'available' check (selection_policy_status in ('available','policy_required')),
  required_credit_hours numeric(6,2) not null check (required_credit_hours >= 0),
  display_order integer not null,
  primary key(plan_key,group_code)
);''')
A('''create table if not exists public.curriculum_plan_courses (
  plan_key text not null references public.curriculum_plans(plan_key) on delete cascade,
  course_code text not null,
  name_ar text not null,
  credit_hours numeric(6,2) not null check (credit_hours >= 0),
  group_code text not null,
  learning_type text,
  delivery_mode text,
  raw_prerequisite_text text,
  prerequisite_codes jsonb not null default '[]'::jsonb,
  prerequisite_logic_status text not null check (prerequisite_logic_status in ('not_applicable','verified','unresolved')),
  review_required boolean not null default false,
  review_reason text,
  display_order integer not null,
  primary key(plan_key,course_code),
  foreign key(plan_key,group_code) references public.curriculum_requirement_groups(plan_key,group_code) on delete restrict,
  check (jsonb_typeof(prerequisite_codes)='array')
);''')
A('create index if not exists idx_curriculum_plan_courses_code on public.curriculum_plan_courses(course_code);')
A('alter table public.curriculum_faculties enable row level security;')
A('alter table public.curriculum_majors enable row level security;')
A('alter table public.curriculum_plans enable row level security;')
A('alter table public.curriculum_requirement_groups enable row level security;')
A('alter table public.curriculum_plan_courses enable row level security;')
A('revoke all on public.curriculum_faculties, public.curriculum_majors, public.curriculum_plans, public.curriculum_requirement_groups, public.curriculum_plan_courses from anon, authenticated;')
# faculties includes existing IT
faculty_map={'IT':'كلية تكنولوجيا المعلومات'}
for p in plans: faculty_map[p['faculty_code']]=p['faculty_ar']
for code,name in faculty_map.items(): A(f"insert into public.curriculum_faculties(faculty_code,name_ar,active) values ({q(code)},{q(name)},true) on conflict(faculty_code) do update set name_ar=excluded.name_ar,active=true;")
# AI major and new majors
A("insert into public.curriculum_majors(major_code,faculty_code,name_ar,active) values ('AI','IT','الذكاء الاصطناعي',true) on conflict(major_code) do update set faculty_code=excluded.faculty_code,name_ar=excluded.name_ar,active=true;")
for p in plans: A(f"insert into public.curriculum_majors(major_code,faculty_code,name_ar,active) values ({q(p['major_code'])},{q(p['faculty_code'])},{q(p['major_ar'])},true) on conflict(major_code) do update set faculty_code=excluded.faculty_code,name_ar=excluded.name_ar,active=true;")
# AI plan + groups and copy current 68 courses from existing public.courses
A("insert into public.curriculum_plans(plan_key,major_code,plan_number,total_required_credits,active,source_status) values ('ZU:IT:AI:P12','AI','12',132,true,'existing_seed') on conflict(plan_key) do update set total_required_credits=excluded.total_required_credits,active=true;")
ai_groups=[('UNIVERSITY_REQUIRED','متطلبات الجامعة الإجبارية','university','required',18,1),('UNIVERSITY_ELECTIVE','متطلبات الجامعة الاختيارية','university','elective',9,2),('FACULTY_REQUIRED','متطلبات الكلية الإجبارية','faculty','required',21,3),('SUPPORTING_REQUIRED','المتطلبات المساندة','supporting','required',12,4),('MAJOR_REQUIRED','متطلبات التخصص الإجبارية','major','required',63,5),('MAJOR_ELECTIVE','متطلبات التخصص الاختيارية','major','elective',9,6)]
for x in ai_groups:
  A(f"insert into public.curriculum_requirement_groups(plan_key,group_code,name_ar,scope,requirement_type,required_credit_hours,display_order) values ('ZU:IT:AI:P12',{q(x[0])},{q(x[1])},{q(x[2])},{q(x[3])},{x[4]},{x[5]}) on conflict(plan_key,group_code) do update set name_ar=excluded.name_ar,required_credit_hours=excluded.required_credit_hours;")
# map Arabic group names to codes and insert AI current course data
A('''insert into public.curriculum_plan_courses(plan_key,course_code,name_ar,credit_hours,group_code,learning_type,delivery_mode,raw_prerequisite_text,prerequisite_codes,prerequisite_logic_status,review_required,review_reason,display_order)
select 'ZU:IT:AI:P12', c.course_code,
       coalesce(c.data_json->>'name', c.course_code),
       coalesce((c.data_json->>'credits')::numeric,0),
       case c.data_json->>'group'
         when 'متطلبات الجامعة الإجبارية' then 'UNIVERSITY_REQUIRED'
         when 'متطلبات الجامعة الاختيارية' then 'UNIVERSITY_ELECTIVE'
         when 'متطلبات الكلية الإجبارية' then 'FACULTY_REQUIRED'
         when 'المتطلبات المساندة' then 'SUPPORTING_REQUIRED'
         when 'متطلبات التخصص الإجبارية' then 'MAJOR_REQUIRED'
         when 'متطلبات التخصص الاختيارية' then 'MAJOR_ELECTIVE'
         else 'MAJOR_ELECTIVE'
       end,
       c.data_json->>'learning_type', null,
       nullif(array_to_string(array(select jsonb_array_elements_text(coalesce(c.data_json->'prerequisites','[]'::jsonb))),','),''),
       coalesce(c.data_json->'prerequisites','[]'::jsonb),
       case jsonb_array_length(coalesce(c.data_json->'prerequisites','[]'::jsonb)) when 0 then 'not_applicable' when 1 then 'verified' else 'unresolved' end,
       jsonb_array_length(coalesce(c.data_json->'prerequisites','[]'::jsonb)) > 1,
       case when jsonb_array_length(coalesce(c.data_json->'prerequisites','[]'::jsonb)) > 1 then 'MULTI_CODE_SOURCE_REQUIRES_AND_OR_VERIFICATION' end,
       row_number() over(order by c.course_code)
from public.courses c
on conflict(plan_key,course_code) do nothing;''')
# new plans + groups + courses
for p in plans:
  A(f"insert into public.curriculum_plans(plan_key,major_code,plan_number,total_required_credits,active,source_status) values ({q(p['plan_key'])},{q(p['major_code'])},{q(p['plan_number'])},{p['computed_total_required_credits']},true,'user_supplied_unverified') on conflict(plan_key) do update set total_required_credits=excluded.total_required_credits,active=true;")
  for g in p['groups']:
    A(f"insert into public.curriculum_requirement_groups(plan_key,group_code,name_ar,scope,requirement_type,selection_policy,selection_policy_status,required_credit_hours,display_order) values ({q(p['plan_key'])},{q(g['group_code'])},{q(g['name_ar'])},{q(g['scope'])},{q(g['requirement_type'])},{q(g['selection_policy'])},{q(g['selection_policy_status'])},{g['required_credit_hours']},{g['display_order']}) on conflict(plan_key,group_code) do update set name_ar=excluded.name_ar,requirement_type=excluded.requirement_type,selection_policy=excluded.selection_policy,selection_policy_status=excluded.selection_policy_status,required_credit_hours=excluded.required_credit_hours;")
  order=0
  for g in p['groups']:
    for c in g['courses']:
      order+=1; raw=c.get('raw_prerequisite_text'); deps=[] if not raw else [x.strip() for x in raw.split(',') if x.strip()]
      logic='not_applicable' if not raw else ('verified' if len(deps)==1 and deps[0]!='0000000' else 'unresolved')
      review=bool(raw and logic=='unresolved'); reason=None
      if review: reason='SOURCE_SENTINEL_0000000_REQUIRES_SEMANTIC_VERIFICATION' if '0000000' in deps else 'MULTI_CODE_SOURCE_REQUIRES_AND_OR_VERIFICATION'
      deps_json=json.dumps(deps,ensure_ascii=False)
      A(f"insert into public.curriculum_plan_courses(plan_key,course_code,name_ar,credit_hours,group_code,learning_type,delivery_mode,raw_prerequisite_text,prerequisite_codes,prerequisite_logic_status,review_required,review_reason,display_order) values ({q(p['plan_key'])},{q(c['course_code'])},{q(c['name_ar'])},{c['credit_hours']},{q(g['group_code'])},{q(c['learning_type'])},{q(c['delivery_mode'])},{q(raw)},{q(deps_json)}::jsonb,{q(logic)},{str(review).lower()},{q(reason)},{order}) on conflict(plan_key,course_code) do nothing;")
# Backfill current AI demo students with unambiguous plan identity, keeping legacy fields
A("update public.students set record_json = jsonb_set(jsonb_set(jsonb_set(coalesce(record_json,'{}'::jsonb),'{plan_key}','\"ZU:IT:AI:P12\"'::jsonb,true),'{faculty_code}','\"IT\"'::jsonb,true),'{major_code}','\"AI\"'::jsonb,true) where profile_json->>'major'='الذكاء الاصطناعي' and (profile_json->>'studyPlan'='خطة 12' or record_json->>'plan_id'='12');")
A('commit;')
with open(os.path.join(DATA_DIR, 'fake_university_multi_plan_migration.sql'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L) + '\n')
print('registry plans', len(registry['plans']) + 1, 'migration bytes', os.path.getsize(os.path.join(DATA_DIR, 'fake_university_multi_plan_migration.sql')))
