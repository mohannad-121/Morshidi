import {describe,it,expect} from 'vitest';
import {label,conversationTitle,days} from './labels';
describe('Arabic visual vocabulary',()=>{
 it('maps requirement groups without leaking machine keys',()=>{expect(label('MAJOR_REQUIRED')).toBe('التخصص إجباري');expect(label('MODEL_BASED')).toBe('');expect(label('MODELED_STRUCTURAL_FALLBACK_NO_GRADE_MASTERY')).toBe('');});
 it('repairs broken titles without mutating persisted history',()=>{expect(conversationTitle('??????','كيف أرتب فصلي؟')).toBe('كيف أرتب فصلي؟');expect(conversationTitle('')).toBe('محادثة جديدة');expect(Array.from(conversationTitle('أ'.repeat(40)))).toHaveLength(28);});
 it('uses Jordanian university day codes',()=>expect(days.map(d=>d.code).join(' ')).toBe('ح ن ث ر خ'));
});
