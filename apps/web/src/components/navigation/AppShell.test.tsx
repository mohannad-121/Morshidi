import {render,screen} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
vi.mock('next/navigation',()=>({usePathname:()=>'/student/progress',useRouter:()=>({replace:vi.fn(),refresh:vi.fn()})}));
vi.mock('@/auth/auth-provider',()=>({useAuth:()=>({user:{email:'202310001@shadow.morshidi.internal',user_metadata:{full_name:'أحمد محمد العلي',university_student_id:'202310001'}},signOut:vi.fn()})}));
import {AppShell} from './AppShell';
describe('student navigation',()=>{
 it('renders all fifteen destinations and one active desktop item',()=>{render(<AppShell><h1>التقدم الدراسي</h1></AppShell>);const nav=screen.getByLabelText('قائمة الطالب');expect(nav.querySelectorAll('nav a')).toHaveLength(15);expect(nav.querySelectorAll('[aria-current=page]')).toHaveLength(1);expect(nav.textContent).toContain('اللوائح');expect(nav.textContent).toContain('شباتر المواد');expect(nav.querySelector('a[href="/student/chapters"]')).not.toBeNull();expect(nav.querySelector('a[href="/student/registration"]')).not.toBeNull();});
 it('uses local Apple emoji images without fabricating notification counts or academic numbers',()=>{render(<AppShell><p>المحتوى</p></AppShell>);const notifications=screen.getByLabelText('الإشعارات');expect(notifications.textContent).toBe('');expect(notifications.querySelector('img[src="/emoji/1f514.png"][aria-hidden="true"]')).not.toBeNull();expect(screen.queryByText('116 ساعة متبقية')).toBeNull();expect(document.querySelectorAll('img[src="/emoji/1f3e0.png"]').length).toBeGreaterThan(0);});
 it('shows the university full name and never exposes the shadow email',()=>{render(<AppShell><p>المحتوى</p></AppShell>);expect(screen.getAllByText('أحمد محمد العلي').length).toBeGreaterThan(0);expect(screen.queryByText('202310001@shadow.morshidi.internal')).toBeNull();});
});
