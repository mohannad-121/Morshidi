# 07 - Inbound Webhooks & Synchronization
# الإشعارات اللحظية ومزامنة البيانات

يرجى مراجعة المواصفة الكاملة في: [Webhook Contract](../webhook-contract.md) و [Sync & Reconciliation](../sync-reconciliation.md).

### النقاط الأساسية:
1. **توقيع الويب هوك:** توقيع الترويسة بـ HMAC-SHA256 عبر الترويسة `x-morshidi-signature`.
2. **الحماية من هجمات الإعادة:** التحقق من الطابع الزمني في الترويسة `x-morshidi-timestamp` ورفض أي طلب يزيد عمره عن 300 ثانية.
3. **منع التكرار (Idempotency):** فحص المعرف الفريد للحدث `x-morshidi-event-id` لتفادي معالجة نفس التغيير مرتين.
4. **تقرير الفروقات (Reconciliation):** كشف أي تباين بين حالة نظام الجامعة والنسخة المتزامنة في مرشدي دون أي تعديل قسري.
