"use client";

import { UnderDevelopmentState } from "@/components/ui/UnderDevelopmentState";
import { DecisionHistoryIcon } from "@/components/ui/Icons";

export default function DecisionHistoryPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="border-b border-[#EDE2C5] pb-5">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
            سجل القرارات والتدقيق
          </span>
          <span className="text-xs text-[#726B5E]">سجل قرارات غير قابل للتعديل</span>
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
          سجل القرارات والتدقيق الأكاديمي
        </h1>
        <p className="text-xs text-[#726B5E]">
          سجل غير قابل للتعديل (Decision Trace Ledger) يوثق كل توصية وقرار أهليّة مع سنده وقواعده الحتمية.
        </p>
      </div>

      <UnderDevelopmentState
        title="سجل القرارات الأكاديمية قيد التجهيز"
        badge="الخدمة قيد التجهيز"
        message="سجل التدقيق والتتبع الأكاديمي المشفر (Decision Trace Ledger - P8) قيد الإنجاز في الطبقة الأمنية."
        details="يوفر مرشدي سجلاً رقمياً موثقاً ومحمياً بتشفير SHA-256 لتسجيل كافة قرارات الأهلية والتوصيات والمحاكاة الفصيلة لضمان الشفافية وقابلية إعادة المحاكاة والتدقيق المستقبلي."
        features={[
          "سجل زمني تسلسلي لكل قرار أو استشارة صادرة للطالب",
          "بصمة رقمية معتمدة لكل قرار (Cryptographic SHA-256 Digest)",
          "إمكانية إعادة تشغيل وفحص القرار (Deterministic Replay Verification)",
          "إبراز إصدار الخطة والسياسة الأكاديمية المطبقة عند صدور القرار بدقة",
        ]}
      />
    </div>
  );
}
