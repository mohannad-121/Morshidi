-- Fake University Production Migration: Reconcile 9 Study Plans and Add Free Elective Requirement
-- Target Project: fjywltwzyfmwexumlnbz (Fake University Production)
-- Purpose: Reconcile 9 Zarqa University study plans from 129.00 to 132.00 credits by adding
--          the governed 3-credit Free Elective requirement group.
-- Principle: AI EXPLAINS — DETERMINISTIC RULES DECIDE. NO INVENTED COURSES. FAIL CLOSED.

begin;

-- 1. Ensure requirement_type check constraint includes 'free_elective'
alter table public.curriculum_requirement_groups
  drop constraint if exists curriculum_requirement_groups_requirement_type_check;

alter table public.curriculum_requirement_groups
  add constraint curriculum_requirement_groups_requirement_type_check
  check (requirement_type in ('required', 'elective', 'free_elective'));

-- 2. Ensure selection policy and selection policy status columns exist
alter table public.curriculum_requirement_groups
  add column if not exists selection_policy text not null default 'plan_membership'
  check (selection_policy in ('plan_membership', 'university_approved')),
  add column if not exists selection_policy_status text not null default 'available'
  check (selection_policy_status in ('available', 'policy_required'));

-- 3. Update total_required_credits from 129.00 to 132.00 for the 9 affected study plans
update public.curriculum_plans
set total_required_credits = 132.00,
    updated_at = now()
where plan_key in (
  'ZU:SCI:MATH:P12',
  'ZU:SCI:PHYS:P12',
  'ZU:ARTS:ENGLISH:P12',
  'ZU:ARTS:HISTORY:P12',
  'ZU:ARTS:TRANS:P12',
  'ZU:BUS:ECON:P12',
  'ZU:BUS:BBA:P12',
  'ZU:BUS:ACC:P12',
  'ZU:NURS:NURS:P12'
);

-- 4. Insert the 3-credit Free Elective requirement group for each of the 9 plans
insert into public.curriculum_requirement_groups (
  plan_key,
  group_code,
  name_ar,
  scope,
  requirement_type,
  selection_policy,
  selection_policy_status,
  required_credit_hours,
  display_order
)
select
  v.plan_key,
  v.group_code,
  v.name_ar,
  v.scope,
  v.requirement_type,
  v.selection_policy,
  v.selection_policy_status,
  v.required_credit_hours,
  v.display_order
from (
  values
    ('ZU:SCI:MATH:P12',    'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:SCI:PHYS:P12',    'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:ARTS:ENGLISH:P12', 'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:ARTS:HISTORY:P12', 'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:ARTS:TRANS:P12',   'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:BUS:ECON:P12',    'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:BUS:BBA:P12',     'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:BUS:ACC:P12',     'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7),
    ('ZU:NURS:NURS:P12',   'FREE_ELECTIVE', 'متطلب حر', 'other', 'free_elective', 'university_approved', 'policy_required', 3.00, 7)
) as v(plan_key, group_code, name_ar, scope, requirement_type, selection_policy, selection_policy_status, required_credit_hours, display_order)
join public.curriculum_plans cp on cp.plan_key = v.plan_key
on conflict (plan_key, group_code) do update set
  name_ar = excluded.name_ar,
  requirement_type = excluded.requirement_type,
  selection_policy = excluded.selection_policy,
  selection_policy_status = excluded.selection_policy_status,
  required_credit_hours = excluded.required_credit_hours;

commit;
