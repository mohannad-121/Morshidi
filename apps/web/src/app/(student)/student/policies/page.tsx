"use client";

import { useEffect, useState, useMemo } from "react";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import type {
  StudentPolicyDocumentSummary,
  StudentPolicyDocumentDetail,
} from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import {
  PoliciesIcon,
  SearchIcon,
  SparklesIcon,
  InfoIcon,
  AlertTriangleIcon,
} from "@/components/ui/Icons";

const CATEGORY_LABELS: Record<string, string> = {
  academic_bylaws: "اللوائح الأكاديمية",
  disciplinary_rules: "الأنظمة التأديبية",
  examination_regulations: "تعليمات الامتحانات",
  registration_guidelines: "قواعد التسجيل والعبء",
};

const AUTHORITY_LABELS: Record<string, string> = {
  university_council: "مجلس الجامعة",
  deans_council: "مجلس العمداء",
  board_of_trustees: "مجلس الأمناء",
  department_council: "مجلس القسم",
  faculty_council: "مجلس الكلية",
};

export default function PoliciesPage() {
  const client = useAuthenticatedApi();
  const [policies, setPolicies] = useState<StudentPolicyDocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const [selectedDoc, setSelectedDoc] = useState<StudentPolicyDocumentSummary | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<StudentPolicyDocumentDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadPolicies = async () => {
      setLoading(true);
      setError(null);
      try {
        const api = new StudentApiService(client);
        const data = await api.listPolicies();
        if (isMounted) {
          setPolicies(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          console.error("Failed to load student policies", err);
          setError("تعذر تحميل اللوائح والسياسات الجامعية. يرجى إعادة المحاولة لاحقاً.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadPolicies();
    return () => {
      isMounted = false;
    };
  }, [client]);

  const handleOpenDetail = async (policy: StudentPolicyDocumentSummary) => {
    setSelectedDoc(policy);
    setSelectedDetail(null);
    setLoadingDetail(true);
    try {
      const api = new StudentApiService(client);
      const detail = await api.getPolicyDetail(policy.id);
      setSelectedDetail(detail);
    } catch (err) {
      console.error("Failed to load policy detail", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedDoc(null);
    setSelectedDetail(null);
  };

  const categories = useMemo(() => {
    const set = new Set<string>();
    policies.forEach((p) => {
      if (p.category) set.add(p.category);
    });
    return Array.from(set);
  }, [policies]);

  const filteredPolicies = useMemo(() => {
    return policies.filter((p) => {
      const matchesCategory =
        selectedCategory === "ALL" || p.category === selectedCategory;
      const q = searchQuery.trim().toLowerCase();
      const matchesQuery =
        !q ||
        p.title.toLowerCase().includes(q) ||
        p.document_code.toLowerCase().includes(q);
      return matchesCategory && matchesQuery;
    });
  }, [policies, selectedCategory, searchQuery]);

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
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[#28241C]">
              اللوائح والسياسات الجامعية
            </h1>
            <p className="mt-1 text-xs text-[#726B5E]">
              استرجاع موثق ومفهرس للأنظمة، تعليمات منح درجة البكالوريوس، وقواعد العبء الدراسي والإنذارات.
            </p>
          </div>
          <div className="inline-flex items-center gap-1.5 self-start rounded-full border border-[#EDE2C5] bg-[#FFFDF7] px-3 py-1 text-[11px] text-[#726B5E] shadow-2xs">
            <SparklesIcon className="h-3.5 w-3.5 text-[#A66F00]" />
            <span>الذكاء الاصطناعي يشرح — القواعد الأكاديمية تقرر.</span>
          </div>
        </div>
      </div>

      {/* Controls & Search */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <SearchIcon className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#726B5E]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="البحث في اللوائح والتعليمات..."
            className="w-full rounded-xl border border-[#EDE2C5] bg-white py-2 pr-9 pl-4 text-xs text-[#28241C] placeholder-[#726B5E]/60 focus:border-[#A66F00] focus:ring-1 focus:ring-[#A66F00] focus:outline-hidden"
          />
        </div>

        {categories.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              onClick={() => setSelectedCategory("ALL")}
              className={`rounded-lg px-3 py-1 text-xs font-semibold transition-colors ${
                selectedCategory === "ALL"
                  ? "bg-[#28241C] text-[#FFFDF7]"
                  : "bg-white text-[#726B5E] border border-[#EDE2C5] hover:border-[#A66F00]"
              }`}
            >
              الكل ({policies.length})
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`rounded-lg px-3 py-1 text-xs font-semibold transition-colors ${
                  selectedCategory === cat
                    ? "bg-[#28241C] text-[#FFFDF7]"
                    : "bg-white text-[#726B5E] border border-[#EDE2C5] hover:border-[#A66F00]"
                }`}
              >
                {CATEGORY_LABELS[cat] || cat}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="rounded-2xl border border-[#EDE2C5] bg-white p-12 text-center shadow-2xs">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-[#A66F00] border-t-transparent" />
          <p className="mt-3 text-xs font-medium text-[#726B5E]">
            جارٍ استرجاع اللوائح والسياسات المعتمدة لجامعتك...
          </p>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800 shadow-2xs">
          <AlertTriangleIcon className="h-5 w-5 shrink-0 text-red-600" />
          <span className="text-xs font-medium">{error}</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredPolicies.length === 0 && (
        <div className="rounded-3xl border border-[#EDE2C5] bg-gradient-to-b from-[#FFF4C7]/40 via-[#FFF9E8] to-[#FFFFFF] p-8 text-center shadow-xs sm:p-12">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00] shadow-2xs">
            <PoliciesIcon className="h-7 w-7" />
          </div>
          <h2 className="mt-4 text-lg font-bold text-[#28241C]">
            {searchQuery
              ? "لا توجد نتائج مطابقة لبحثك"
              : "لا توجد لوائح معتمدة منشورة حالياً لجامعتك"}
          </h2>
          <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-[#726B5E]">
            {searchQuery
              ? "جرّب تغيير كلمات البحث أو اختيار تصنيف آخر."
              : "تلتزم مرشدي بأعلى درجات الدقة والنزاهة الأكاديمية؛ لا يتم عرض أي تعليمات أو لوائح إلا بعد اعتمادها وفهرستها رسمياً من قِبل إدارة الجامعة."}
          </p>
        </div>
      )}

      {/* Policies Grid */}
      {!loading && !error && filteredPolicies.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredPolicies.map((p) => {
            const categoryName = CATEGORY_LABELS[p.category] || p.category;
            const authorityName = AUTHORITY_LABELS[p.authority_level] || p.authority_level;

            return (
              <div
                key={p.id}
                onClick={() => handleOpenDetail(p)}
                className="group flex flex-col justify-between rounded-2xl border border-[#EDE2C5] bg-white p-5 shadow-2xs transition-all hover:border-[#A66F00] hover:shadow-xs cursor-pointer"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] font-bold text-[#A66F00] bg-[#FFF4C7] px-2 py-0.5 rounded-md">
                      {p.document_code}
                    </span>
                    <Badge variant="neutral" className="text-[10px]">
                      {categoryName}
                    </Badge>
                  </div>

                  <h3 className="mt-3 text-base font-bold text-[#28241C] group-hover:text-[#A66F00] transition-colors leading-snug">
                    {p.title}
                  </h3>

                  <div className="mt-3 flex items-center gap-2 text-xs text-[#726B5E]">
                    <span className="font-medium">{authorityName}</span>
                    <span>•</span>
                    <span>إصدار {p.active_version_tag}</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-[#EDE2C5]/60 flex items-center justify-between text-xs text-[#726B5E]">
                  <span>{p.passage_count} مادة / فقرة مفهرسة</span>
                  <span className="font-bold text-[#A66F00] group-hover:underline">
                    استعراض النصوص ←
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Policy Detail Modal */}
      {selectedDoc && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs"
          onClick={handleCloseDetail}
        >
          <div
            className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-3xl border border-[#EDE2C5] bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-[#EDE2C5] p-5">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-[#A66F00] bg-[#FFF4C7] px-2 py-0.5 rounded-md">
                    {selectedDoc.document_code}
                  </span>
                  <span className="text-xs text-[#726B5E]">
                    الإصدار {selectedDoc.active_version_tag}
                  </span>
                </div>
                <h3 className="mt-1.5 text-lg font-bold text-[#28241C]">
                  {selectedDoc.title}
                </h3>
              </div>
              <button
                onClick={handleCloseDetail}
                className="rounded-xl border border-[#EDE2C5] bg-[#FFFDF7] p-2 text-sm text-[#726B5E] hover:bg-[#EDE2C5]/40"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {loadingDetail && (
                <div className="py-12 text-center">
                  <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-[#A66F00] border-t-transparent" />
                  <p className="mt-2 text-xs text-[#726B5E]">جارٍ تحميل نصوص اللائحة...</p>
                </div>
              )}

              {selectedDetail && selectedDetail.passages.length === 0 && (
                <div className="rounded-xl border border-[#EDE2C5] bg-[#FFFDF7] p-6 text-center text-xs text-[#726B5E]">
                  لا توجد فقرات أو نصوص مفهرسة لهذا الإصدار حالياً.
                </div>
              )}

              {selectedDetail &&
                selectedDetail.passages.map((pas) => (
                  <div
                    key={pas.id}
                    className="rounded-xl border border-[#EDE2C5] bg-[#FFFDF7] p-4 text-right shadow-2xs"
                  >
                    <div className="flex items-center justify-between border-b border-[#EDE2C5]/60 pb-2 mb-2">
                      <span className="font-bold text-[#A66F00] text-xs">
                        {pas.locator_text}
                      </span>
                      {pas.article_number && (
                        <span className="text-[11px] text-[#726B5E]">
                          مادة رقم {pas.article_number}
                        </span>
                      )}
                    </div>
                    <p className="text-xs leading-relaxed text-[#28241C] whitespace-pre-wrap">
                      {pas.passage_text}
                    </p>
                  </div>
                ))}
            </div>

            {/* Modal Footer */}
            <div className="border-t border-[#EDE2C5] p-4 flex items-center justify-between bg-[#FFFDF7] rounded-b-3xl">
              <div className="flex items-center gap-1.5 text-[11px] text-[#726B5E]">
                <InfoIcon className="h-3.5 w-3.5 text-[#A66F00]" />
                <span>سند تشريعي رسمي معتمد</span>
              </div>
              <button
                onClick={handleCloseDetail}
                className="rounded-xl bg-[#28241C] px-4 py-1.5 text-xs font-semibold text-[#FFFDF7] hover:bg-[#3D372B]"
              >
                إغلاق
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
