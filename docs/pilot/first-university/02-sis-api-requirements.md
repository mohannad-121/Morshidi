# 02 - SIS API Requirements
# متطلبات واجهات برمجة التطبيقات (SIS REST API)

يرجى مراجعة المواصفة الكاملة في: [SIS Integration Contract](../sis-integration-contract.md).

### النقاط الأساسية المطلوبة:
1. **الصيغة:** RESTful JSON عبر HTTPS (TLS 1.2+).
2. **نقاط النهاية الأساسية للقراءة:**
   - `GET /health` أو `GET /healthz`: فحص الجاهزية والاتصال.
   - `GET /calendar`: الفصل الأكاديمي الحالي وحالة التسجيل.
   - `GET /student/me`: استرجاع بيانات الطالب الأكاديمية.
   - `GET /student/grades`: كشف العلامات والمعدل التراكمي.
   - `GET /student/enrollments`: الشعب والمساقات المسجلة حالياً.
   - `GET /student/academic-plan`: الخطة الدراسية وموادها.
   - `GET /offerings?term={term}`: الشعب المطروحة والطاقة الاستيعابية.
3. **التوثيق:** OAuth 2.0 Client Credentials أو Token Exchange.
4. **حدود الطلبات (Rate Limits):** لا تقل عن 600 طلب بالدقيقة لتغطية عمليات المزامنة الدورية.

---

# 03 - SSO & Identity Requirements
# متطلبات الدخول الموحد وإدارة الهويات (SSO & IdP)

يرجى مراجعة المواصفة الكاملة في: [Identity & SSO Requirements](../identity-sso-requirements.md).

### النقاط الأساسية المطلوبة:
1. **البروتوكولات المدعومة:**
   - OpenID Connect (OIDC) - الخيار الموصى به.
   - SAML 2.0.
   - تبادل الرموز الموثق (Token Exchange).
2. **الادعاءات الأساسية المطلوبة في رمز الدخول (Claims):**
   - `sub`: المعرف الفريد الثابت للطالب في مزود الهوية.
   - `student_id` أو `preferred_username`: الرقم الجامعي الرسمي للطالب.
   - `email`: البريد الإلكتروني الجامعي للطالب.
3. **الحماية من تعارض الهويات (Fail-Closed Identity Defense):**
   - يرفض النظام ربط المعرف الخارجي إذا كان مسجلاً لطالب آخر لمنع انتحال الشخصيات.
   - يرفض النظام الدخول إذا كان هناك اختلاف بين المستأجر الجامعي ورمز الـ Token.
