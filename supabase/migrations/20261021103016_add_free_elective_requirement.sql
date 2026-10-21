-- Migration: 20261021103016_add_free_elective_requirement.sql
-- Purpose: Schema foundation for generic university-approved free electives and
--          canonical correction of requirement group accounting across all 9 Zarqa University
--          bachelor curricula containing a 3-credit Free Elective requirement (reconciling 129 -> 132 credits).
-- Principle: AI EXPLAINS — DETERMINISTIC RULES DECIDE. NO INVENTED COURSES. FAIL CLOSED.

begin;

-- 1. Schema: Extend requirement_groups to support free_elective requirement type
alter table public.requirement_groups
  drop constraint if exists requirement_groups_requirement_type_check;

alter table public.requirement_groups
  add constraint requirement_groups_requirement_type_check
  check (requirement_type in ('required', 'elective', 'free_elective'));

-- 2. Schema: Add selection policy and status columns for open/generic requirements
alter table public.requirement_groups
  add column if not exists selection_policy text not null default 'plan_membership'
  check (selection_policy in ('plan_membership', 'university_approved')),
  add column if not exists selection_policy_status text not null default 'available'
  check (selection_policy_status in ('available', 'policy_required'));

-- 3. Data correction: Reconcile 9 study plans canonical total from 129.00 to 132.00 credits
update public.study_plans
set total_credit_hours = 132.00,
    updated_at = now()
where id in (
  '070818ab-9577-5457-afd9-865a50241b9d', -- ZU:SCI:MATH:P12
  '6a3a9646-2822-56da-b486-a001f0aa927a', -- ZU:SCI:PHYS:P12
  '4aed9e40-89eb-5bf9-9eea-129dbad7a936', -- ZU:ARTS:ENGLISH:P12
  '91eec87e-6eec-5bb4-9f4c-a24cad790747', -- ZU:ARTS:HISTORY:P12
  'a6622d55-d8b8-5a8c-8c6b-70e83391c100', -- ZU:ARTS:TRANS:P12
  'ce695e6c-b58c-545f-9dd9-a58c659b685e', -- ZU:BUS:ECON:P12
  '6b5756b1-e8f1-5274-9711-4189a5eff158', -- ZU:BUS:BBA:P12
  '94e47824-8352-5280-a8d9-796e329c845e', -- ZU:BUS:ACC:P12
  '2a78bbbb-0dc0-5c46-8630-7a46e4179830'  -- ZU:NURS:NURS:P12
);

-- 4. Data correction: Add the governed Free Elective requirement group (3.00 credits) to all 9 plans if the plan exists in this database
-- These are requirement nodes without fixed course membership; selection fails closed until university policy is supplied.
insert into public.requirement_groups (
  id,
  study_plan_id,
  group_code,
  name_ar,
  name_en,
  scope,
  requirement_type,
  selection_policy,
  selection_policy_status,
  required_credit_hours,
  display_order,
  active
)
select
  v.id,
  v.study_plan_id,
  v.group_code,
  v.name_ar,
  v.name_en,
  v.scope,
  v.requirement_type,
  v.selection_policy,
  v.selection_policy_status,
  v.required_credit_hours,
  v.display_order,
  v.active
from (
  values
    ('56e1cf0a-829b-574f-8761-e364a1070633'::uuid, '070818ab-9577-5457-afd9-865a50241b9d'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('cf2d6863-0d43-5b51-a8f1-a37714761bcf'::uuid, '6a3a9646-2822-56da-b486-a001f0aa927a'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('a0f3277e-0f01-5aa2-9b45-77fec87343c4'::uuid, '4aed9e40-89eb-5bf9-9eea-129dbad7a936'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('b832a811-d446-58c2-8e1b-f871a12f2b96'::uuid, '91eec87e-6eec-5bb4-9f4c-a24cad790747'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('921ea88b-a86f-5b01-b4a5-6b0f83e36f1c'::uuid, 'a6622d55-d8b8-5a8c-8c6b-70e83391c100'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('9e855f92-5261-5a13-a355-dfe9c511254d'::uuid, 'ce695e6c-b58c-545f-9dd9-a58c659b685e'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('79d988f7-4238-528e-9daa-2f428cba4f2f'::uuid, '6b5756b1-e8f1-5274-9711-4189a5eff158'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('498a5d0a-b721-5bba-82fe-b4fc4b5d8d22'::uuid, '94e47824-8352-5280-a8d9-796e329c845e'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true),
    ('0f147053-35fe-5c3c-9bdf-5c51a65331c7'::uuid, '2a78bbbb-0dc0-5c46-8630-7a46e4179830'::uuid, 'FREE_ELECTIVE', 'متطلب حر', 'Free Elective', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7, true)
) as v(id, study_plan_id, group_code, name_ar, name_en, scope, requirement_type, selection_policy, selection_policy_status, required_credit_hours, display_order, active)
join public.study_plans sp on sp.id = v.study_plan_id
on conflict (study_plan_id, group_code) do update set
  name_ar = excluded.name_ar,
  name_en = excluded.name_en,
  requirement_type = excluded.requirement_type,
  selection_policy = excluded.selection_policy,
  selection_policy_status = excluded.selection_policy_status,
  required_credit_hours = excluded.required_credit_hours,
  updated_at = now();

commit;
