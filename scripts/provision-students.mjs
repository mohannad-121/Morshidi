/** Owner-operated provisioning. Run dry first; --apply creates missing accounts only.
 * University data is obtained over HTTP, never from a sibling repository.
 * Credentials are written exclusively to an ignored local file, never stdout.
 */
import { randomBytes } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export function attemptsFor(profile, courseIds) {
  const sequence = new Map();
  const rows = [];
  function append(code, values) {
    const courseId = courseIds.get(code);
    if (!courseId) throw new Error(`Course is not mapped in the selected plan: ${code}`);
    const next = (sequence.get(code) || 0) + 1;
    sequence.set(code, next);
    rows.push({ course_id: courseId, attempt_sequence: next, record_source: 'university_integration',
      term_label: null, reported_grade_text: null, raw_numeric_grade: null, raw_letter_grade: null,
      performance_provenance: 'STUDENT_RECORD', performance_verification_state: 'UNVERIFIED', ...values });
  }
  for (const term of profile.semesterHistory) {
    for (const course of term.courses) {
      const outcome = { 'ناجح': 'PASSED', 'راسب': 'FAILED', 'منسحب': 'WITHDRAWN' }[course.status];
      if (!outcome) throw new Error('Unknown university attempt status');
      append(course.courseCode, { outcome, term_label: term.semesterName,
        reported_grade_text: course.letterGrade || String(course.grade), raw_numeric_grade: course.grade,
        raw_letter_grade: course.letterGrade || null, attempt_credit_hours: course.credits,
        performance_source_reference: `uni:${profile.universityId}:${term.semesterId}` });
    }
  }
  const current = new Set();
  for (const section of profile.currentRegisteredSections) {
    if (current.has(section.courseCode)) continue;
    current.add(section.courseCode);
    append(section.courseCode, { outcome: 'IN_PROGRESS', attempt_credit_hours: section.credits,
      performance_source_reference: `uni:${profile.universityId}:section:${section.id}` });
  }
  return rows;
}

async function main() {
  const apply = process.argv.includes('--apply');
  const ids = process.argv.filter(v => /^\d{9}$/.test(v));
  if (!ids.length) throw new Error('Pass the university IDs explicitly. No default students are provisioned.');
  const required = ['SUPABASE_URL','SUPABASE_SECRET_KEY','UNI_BASE_URL','UNI_SERVICE_KEY','STUDY_PLAN_ID'];
  for (const name of required) if (!process.env[name]) throw new Error(`Missing ${name}`);
  const { SUPABASE_URL: url, SUPABASE_SECRET_KEY: key, UNI_BASE_URL: uni, UNI_SERVICE_KEY: uniKey, STUDY_PLAN_ID: planId } = process.env;
  async function request(path, init = {}) {
    const response = await fetch(`${url.replace(/\/$/, '')}${path}`, { ...init, signal: AbortSignal.timeout(20000),
      headers: { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json',
        Prefer: 'return=representation', ...init.headers } });
    const body = await response.json();
    if (!response.ok) throw new Error(`Provisioning request ${path.split('?')[0]} failed (${response.status}, ${body.code || 'unknown'})`);
    return body;
  }
  const plans = await request(`/rest/v1/study_plans?id=eq.${planId}&select=id,plan_number,majors(faculties(university_id))`);
  if (plans.length !== 1) throw new Error('Select exactly one existing study plan');
  const universityId = plans[0].majors.faculties.university_id;
  const courses = await request(`/rest/v1/courses?university_id=eq.${universityId}&select=id,course_code`);
  const courseIds = new Map(courses.map(c => [c.course_code, c.id]));
  const users = [];
  for (let page = 1; ; page++) {
    const batch = (await request(`/auth/v1/admin/users?page=${page}&per_page=100`)).users;
    users.push(...batch);
    if (batch.length < 100) break;
  }
  // Validate every source before making the first write.
  const sources = [];
  for (const id of ids) {
    const response = await fetch(`${uni.replace(/\/$/, '')}/v1/integration/students/${id}`, {
      headers: { 'X-Uni-Api-Key': uniKey }, signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error(`University source failed for ${id} (${response.status})`);
    const source = await response.json();
    if (source.profile?.universityId !== id || source.record?.student_id !== id) throw new Error('University identity mismatch');
    if (String(source.record.plan_id) !== String(plans[0].plan_number)) throw new Error('University plan does not match selected database plan');
    sources.push({ id, ...source, attempts: attemptsFor(source.profile, courseIds) });
  }
  const directory = resolve('.secrets');
  const accessFile = resolve(directory, 'student-access.json');
  let credentials = [];
  if (apply) {
    mkdirSync(directory, { recursive: true });
    try { credentials = JSON.parse(readFileSync(accessFile, 'utf8')); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  }
  for (const source of sources) {
    const email = `${source.id}@std.morshidi.edu.jo`;
    let user = users.find(u => u.email?.toLowerCase() === email);
    if (!apply) { console.log(`${source.id}: ${user ? 'existing account' : 'create account'}, ${source.attempts.length} source attempts (dry run)`); continue; }
    if (!user) {
      // Save the generated credential before the network write so a process crash cannot lose it.
      let saved = credentials.find(c => c.studentId === source.id);
      if (!saved) {
        saved = { studentId: source.id, email, temporaryPassword: `${randomBytes(20).toString('base64url')}!9aA`, createdAt: new Date().toISOString() };
        credentials.push(saved);
        writeFileSync(accessFile, JSON.stringify(credentials, null, 2) + '\n', { mode: 0o600 });
      }
      user = await request('/auth/v1/admin/users', { method: 'POST', body: JSON.stringify({
        email, password: saved.temporaryPassword, email_confirm: true,
        user_metadata: { full_name: source.profile.name },
        app_metadata: { university_student_id: source.id },
      }) });
    }
    const existing = await request(`/rest/v1/student_academic_profiles?owner_user_id=eq.${user.id}&select=id,study_plan_id`);
    let academic = existing[0];
    if (academic && academic.study_plan_id !== planId) throw new Error('Existing account belongs to another study plan; no overwrite performed');
    if (!academic) {
      const gpa = source.record.cumulative_gpa;
      const earned = source.record.earned_credits;
      if (typeof gpa !== 'number' || typeof earned !== 'number') throw new Error('Missing numeric academic summary in university source');
      [academic] = await request('/rest/v1/student_academic_profiles', { method: 'POST', body: JSON.stringify({
        owner_user_id: user.id, study_plan_id: planId, reported_cumulative_gpa: gpa,
        reported_gpa_scale: 100, reported_earned_credit_hours: earned,
      }) });
    }
    // Never replace edited grades. Only append the explicitly missing import keys.
    const attempts = await request(`/rest/v1/student_course_attempts?profile_id=eq.${academic.id}&select=course_id,attempt_sequence`);
    const existingKeys = new Set(attempts.map(a => `${a.course_id}:${a.attempt_sequence}`));
    const missing = source.attempts.filter(a => !existingKeys.has(`${a.course_id}:${a.attempt_sequence}`))
      .map(a => ({ ...a, profile_id: academic.id }));
    if (missing.length) await request('/rest/v1/student_course_attempts', { method: 'POST', body: JSON.stringify(missing) });
    console.log(`${source.id}: account and academic profile ready; ${missing.length} imported attempts`);
  }
  if (apply) console.log('Temporary credentials saved only in .secrets/student-access.json. Existing passwords were not changed.');
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
