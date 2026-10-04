import {render,screen} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
vi.mock('next/navigation',()=>({usePathname:()=>'/student/progress',useRouter:()=>({replace:vi.fn(),refresh:vi.fn()})}));
vi.mock('@/auth/auth-provider',()=>({useAuth:()=>({user:{email:'student@example.edu',user_metadata:{}},signOut:vi.fn()})}));
import {AppShell} from './AppShell';
describe('student navigation',()=>{
 it('renders all thirteen destinations and one active desktop item',()=>{render(<AppShell><h1>التقدم الدراسي</h1></AppShell>);const nav=screen.getByLabelText('قائمة الطالب');expect(nav.querySelectorAll('nav a')).toHaveLength(13);expect(nav.querySelectorAll('[aria-current=page]')).toHaveLength(1);expect(nav.textContent).toContain('اللوائح');});
 it('does not fabricate a notification count or academic numbers',()=>{render(<AppShell><p>المحتوى</p></AppShell>);expect(screen.getByLabelText('الإشعارات').textContent).toBe('');expect(screen.queryByText('116 ساعة متبقية')).toBeNull();});
});
