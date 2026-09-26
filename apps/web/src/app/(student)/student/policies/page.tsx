"use client";

import { UnderDevelopmentState } from "@/components/ui/UnderDevelopmentState";
import { PoliciesIcon } from "@/components/ui/Icons";

export default function PoliciesPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="border-b border-[#EDE2C5] pb-5">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
            اللوائح والسياسات
          </span>
          <span className="text-xs text-[#726B5E]">المكتبة التشريعية الأكاديمية</span>
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
          اللوائح والسياسات الجامعية
        </h1>
        <p className="text-xs text-[#726B5E]">
          استرجاع موثق ومفهرس للأنظمة، تعليمات منح درجة البكالوريوس، وقواعد العبء الدراسي والإنذارات.
        </p>
      </div>

      <UnderDevelopmentState
        title="بوابة اللوائح والسياسات قيد التجهيز"
        badge="الخدمة قيد التجهيز"
        message="محرك الاسترجاع التشريعي الموثق (Institutional Policy Retrieval) قيد الربط والاختبار والاعتماد."
        details="تلتزم مرشدي بأعلى درجات الدقة القانونية والأكاديمية؛ حيث لا يتم عرض أي مادة نظامية إلا بعد التحقق من إصدارها المعتمد وسندها التشريعي في الجامعة لضمان عدم تقديم معلومات غير رسمية."
        features={[
          "البحث الدلالي الذكي في تعليمات منح درجة البكالوريوس المعتمدة",
          "استعراض فصول اللائحة (العبء الدراسي، الحضور والغياب، الإنذارات الأكاديمية)",
          "ربط القرارات الأكاديمية بنصوص المواد والفقرات القانونية الصريحة",
          "تنبيهات فورية عند تعديل أي مادة نظامية تؤثر على مسارك الدراسي",
        ]}
      />
    </div>
  );
}
