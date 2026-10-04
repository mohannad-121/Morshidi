/** Presentation-only vocabulary. Unknown machine labels are never displayed. */
export const labels: Record<string, string> = {
  UNIVERSITY_REQUIRED: 'متطلبات الجامعة', UNIVERSITY_ELECTIVE: 'اختياري جامعة',
  FACULTY_REQUIRED: 'متطلبات الكلية', SUPPORTING_REQUIRED: 'المساندة',
  MAJOR_REQUIRED: 'التخصص إجباري', MAJOR_ELECTIVE: 'التخصص اختياري',
  COMPLETED: 'منجزة', PASSED: 'ناجح', IN_PROGRESS: 'قيد الدراسة', FAILED: 'راسب',
  WITHDRAWN: 'منسحب', NOT_ATTEMPTED: 'لم تبدأ', ATTEMPTED_NOT_COMPLETED: 'تحتاج إعادة',
  ELIGIBLE: 'مؤهل', NOT_ELIGIBLE: 'غير مؤهل', REVIEW_REQUIRED: 'تحتاج مراجعة',
  ACTIVE: 'نشط', ARCHIVED: 'مؤرشفة', required: 'إجباري', elective: 'اختياري',
  MANDATORY: 'إجباري', ELECTIVE: 'اختياري', IN_PERSON: 'وجاهي', ONLINE: 'عن بُعد', HYBRID: 'مدمج',
  manual_entry: 'إدخال يدوي', transcript_import: 'كشف علامات', university_integration: 'الجامعة', admin_correction: 'تصحيح معتمد',
  FIRST: 'الأول', SECOND: 'الثاني', SUMMER: 'الصيفي', FASTEST: 'الأسرع', BALANCED: 'المتوازن', LOWER_LOAD: 'الأخف',
  DETERMINISTIC_RULES: 'قواعد الجامعة', DETERMINISTIC: 'قواعد الجامعة', POLICY_RETRIEVAL: 'لوائح الجامعة',
  DETERMINISTIC_RULES_ENGINE: 'قواعد الجامعة', FIRST_SEMESTER: 'الأول', SECOND_SEMESTER: 'الثاني',
  POLICY: 'لوائح الجامعة', STUDENT_RECORD: 'السجل الأكاديمي', GENERAL_CHAT: 'محادثة عامة',
  NO_PREREQUISITES: 'بلا متطلبات سابقة', PREREQUISITES_SATISFIED: 'المتطلبات مكتملة',
  MISSING_PREREQUISITE_GROUP: 'متطلب سابق ناقص', TARGET_ALREADY_COMPLETED: 'اجتزت هذه المادة',
  TARGET_CURRENTLY_ENROLLED: 'مسجلة حالياً', PREREQUISITE_LOGIC_UNRESOLVED: 'يلزم تأكيد المتطلبات',
};
export function label(value: string | null | undefined, fallback = ''): string {
  if (!value) return fallback;
  return labels[value] ?? (/^[A-Z][A-Z_0-9]*$/.test(value) ? fallback : value);
}
export const days = [{id:7,code:'ح',name:'الأحد'},{id:1,code:'ن',name:'الاثنين'},{id:2,code:'ث',name:'الثلاثاء'},{id:3,code:'ر',name:'الأربعاء'},{id:4,code:'خ',name:'الخميس'}];
export function conversationTitle(title: string, firstMessage?: string): string {
  const usable = (s: string) => s.trim() && !/[?؟�]{3,}|(?:Ã|Ø|Ù){2}/.test(s);
  return Array.from(usable(title) ? title.trim() : firstMessage && usable(firstMessage) ? firstMessage.trim() : 'محادثة جديدة').slice(0,28).join('');
}
