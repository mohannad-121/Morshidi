import { test } from 'node:test';
import assert from 'node:assert/strict';
import { attemptsFor } from './provision-students.mjs';

const profile = { universityId: '100000001', semesterHistory: [{ semesterId: '2025-1', semesterName: 'الأول 2025',
  courses: [{ courseCode: 'CS1', status: 'راسب', grade: 45, credits: 3, letterGrade: 'F' }] }],
  currentRegisteredSections: [{ id: 'section-1', courseCode: 'CS1', credits: 3 }, { id: 'section-2', courseCode: 'CS1', credits: 3 }] };
test('import preserves grade, retake order and unverified provenance without duplicate current courses', () => {
  const rows = attemptsFor(profile, new Map([['CS1', 'course-uuid']]));
  assert.equal(rows.length, 2);
  assert.deepEqual(rows.map(r => [r.outcome, r.attempt_sequence]), [['FAILED', 1], ['IN_PROGRESS', 2]]);
  assert.equal(rows[0].raw_numeric_grade, 45);
  assert.equal(rows[0].performance_verification_state, 'UNVERIFIED');
  assert.equal(rows[1].raw_numeric_grade, null);
  assert.deepEqual(Object.keys(rows[0]).sort(), Object.keys(rows[1]).sort());
});
test('unmapped course fails closed instead of silently losing a student grade', () => {
  assert.throws(() => attemptsFor(profile, new Map()), /not mapped/);
});
