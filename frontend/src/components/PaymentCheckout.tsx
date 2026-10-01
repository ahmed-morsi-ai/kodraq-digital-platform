import { useEffect, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import {
  AlertCircle,
  BookOpen,
  Briefcase,
  CheckCircle2,
  Copy,
  CreditCard,
  Landmark,
  Loader2,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Upload,
  Wallet,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { paymentService } from "@/services/payment.service";
import type { Enrollment } from "@/types/enrollment";
import type { Payment, PaymentInstructions, PaymentMethod } from "@/types/payment";
import type { TrackCurriculum } from "@/types/track";

interface PaymentCheckoutProps {
  track: TrackCurriculum;
  enrollment?: Enrollment;
}

const PAYMENT_METHODS: {
  value: PaymentMethod;
  label: string;
  icon: typeof Wallet;
}[] = [
  { value: "INSTAPAY", label: "InstaPay", icon: Wallet },
  { value: "VODAFONE_CASH", label: "Vodafone Cash", icon: Smartphone },
  { value: "BANK_TRANSFER", label: "تحويل بنكي", icon: Landmark },
];

function getErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return error instanceof Error
    ? error.message
    : "تعذر إرسال طلب الدفع. يرجى المحاولة مرة أخرى.";
}

export default function PaymentCheckout({ track, enrollment }: PaymentCheckoutProps) {
  const [instructions, setInstructions] = useState<PaymentInstructions | null>(null);
  const [instructionsError, setInstructionsError] = useState<string | null>(null);
  const [method, setMethod] = useState<PaymentMethod>("INSTAPAY");
  const [transferReference, setTransferReference] = useState("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payment, setPayment] = useState<Payment | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    void paymentService.getInstructions()
      .then((result) => {
        if (active) setInstructions(result);
      })
      .catch((requestError: unknown) => {
        if (active) setInstructionsError(getErrorMessage(requestError));
      });
    return () => {
      active = false;
    };
  }, []);

  const amount = Number(track.price ?? 0);
  const formattedAmount = new Intl.NumberFormat("en-EG", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
  const currency = track.currency || "EGP";
  const isAlreadyEnrolled = enrollment?.status === "active" || enrollment?.status === "completed";

  if (!track.is_premium || isAlreadyEnrolled) return null;

  const paymentAccount = method === "INSTAPAY"
    ? instructions?.instapay
    : method === "VODAFONE_CASH"
      ? instructions?.vodafone_cash
      : null;

  const copyAccount = async () => {
    if (!paymentAccount) return;
    try {
      await navigator.clipboard.writeText(paymentAccount);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("تعذر نسخ بيانات الدفع. يمكنك تحديدها ونسخها يدوياً.");
    }
  };

  const submitPayment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!transferReference.trim()) {
      setError("أدخل رقم الهاتف أو مرجع التحويل.");
      return;
    }
    if (!receipt) {
      setError("أرفق إيصال التحويل لإرسال الطلب.");
      return;
    }

    setIsSubmitting(true);
    try {
      const createdPayment = await paymentService.submitPayment(
        track.id,
        method,
        receipt,
        transferReference,
      );
      setPayment(createdPayment);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section dir="rtl" aria-labelledby="checkout-title" className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg shadow-slate-900/5">
      <div role="alert" className="flex items-start gap-3 bg-rose-700 px-5 py-4 text-sm font-bold leading-7 text-white sm:px-7">
        <span aria-hidden="true" className="text-lg">🚨</span>
        <p>تنبيه هام: يُغلق باب التسجيل رسمياً يوم الإثنين 05/10/2026، ولن يُفتح باب الانضمام للمسار مرة أخرى إلا بعد 6 أشهر كاملة.</p>
      </div>

      <div className="grid lg:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-6 p-5 sm:p-7">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase text-sky-700">
              <ShieldCheck aria-hidden="true" className="size-4" /> Kodraq Digital
            </p>
            <h2 id="checkout-title" className="mt-2 text-xl font-bold text-slate-950 sm:text-2xl">ابدأ مسارك المهني الآن</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">منهج تطبيقي متكامل من بناء الأنظمة إلى تشغيلها في بيئة الإنتاج.</p>
          </div>

          <ul className="grid gap-x-6 gap-y-5 sm:grid-cols-2">
            <li className="flex gap-3">
              <BookOpen aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-sky-700" />
              <div><p className="text-sm font-bold text-slate-900">منهج إنتاجي متكامل</p><p className="mt-1 text-xs leading-5 text-slate-600">4 وحدات معمارية تشمل FastAPI وPostgreSQL + pgvector وRAG والنشر السحابي.</p></div>
            </li>
            <li className="flex gap-3">
              <Sparkles aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-violet-700" />
              <div><p className="text-sm font-bold text-slate-900">معلم ذكاء اصطناعي مخصص</p><p className="mt-1 text-xs leading-5 text-slate-600">AI Tutor متاح 24/7 للإجابة عن استفساراتك ومساعدتك في تصحيح الأكواد.</p></div>
            </li>
            <li className="flex gap-3">
              <Briefcase aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-emerald-700" />
              <div><p className="text-sm font-bold text-slate-900">مسار التوظيف</p><p className="mt-1 text-xs leading-5 text-slate-600">إمكانية الانضمام إلى Talent Pool والمشاريع الحقيقية للمتفوقين، مع شهادات رسمية برمز QR.</p></div>
            </li>
            <li className="flex gap-3">
              <Wrench aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-amber-700" />
              <div><p className="text-sm font-bold text-slate-900">تطبيقات عملية حقيقية</p><p className="mt-1 text-xs leading-5 text-slate-600">ابنِ منصات إنتاجية قابلة للنشر الفوري وتدرب على قرارات التصميم والتنفيذ.</p></div>
            </li>
          </ul>

          <div className="flex items-end justify-between gap-3 border-t border-slate-200 pt-5">
            <div><p className="text-xs font-semibold text-slate-500">رسوم المسار</p><p className="mt-1 text-3xl font-extrabold tabular-nums text-slate-950">{currency} {formattedAmount}</p></div>
            <span className="mb-1 inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700"><ShieldCheck aria-hidden="true" className="size-4" /> دفع آمن ومراجعة يدوية</span>
          </div>
        </div>

        <div className="border-t border-slate-200 bg-slate-50 p-5 sm:p-7 lg:border-r lg:border-t-0">
          {payment ? (
            <div role="status" className="flex min-h-full flex-col items-center justify-center py-8 text-center">
              <CheckCircle2 aria-hidden="true" className="size-12 text-emerald-600" />
              <h3 className="mt-4 text-lg font-bold text-slate-950">تم استلام طلب الدفع</h3>
              <p className="mt-2 max-w-sm text-sm leading-6 text-slate-600">تم إرسال الإيصال للمراجعة. رقم الطلب <span className="font-mono font-bold">#{payment.id}</span>. سيظهر تفعيل الاشتراك بعد اعتماد الدفع.</p>
            </div>
          ) : (
            <form onSubmit={(event) => void submitPayment(event)} className="space-y-5">
              <div>
                <h3 className="flex items-center gap-2 text-base font-bold text-slate-950"><CreditCard aria-hidden="true" className="size-5 text-sky-700" /> إتمام الدفع</h3>
                <p className="mt-1 text-xs leading-5 text-slate-600">اختر وسيلة الدفع، ثم أدخل مرجع التحويل وأرفق صورة الإيصال.</p>
              </div>

              <fieldset className="space-y-2">
                <legend className="text-xs font-bold text-slate-700">وسيلة الدفع</legend>
                <div className="grid grid-cols-3 gap-2">
                  {PAYMENT_METHODS.map(({ value, label, icon: Icon }) => (
                    <label key={value} className={`flex min-h-16 cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-center text-xs font-semibold transition focus-within:ring-2 focus-within:ring-sky-500 ${method === value ? "border-sky-600 bg-sky-50 text-sky-900" : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"}`}>
                      <input className="sr-only" type="radio" name="payment-method" value={value} checked={method === value} onChange={() => setMethod(value)} />
                      <Icon aria-hidden="true" className="size-4" />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>

              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-xs font-bold text-slate-800">بيانات التحويل</p>
                {instructionsError ? (
                  <p role="alert" className="mt-2 text-xs leading-5 text-rose-700">{instructionsError}</p>
                ) : !instructions ? (
                  <p role="status" className="mt-2 flex items-center gap-2 text-xs text-slate-500"><Loader2 aria-hidden="true" className="size-3.5 animate-spin" /> جارٍ تحميل بيانات الدفع...</p>
                ) : method === "BANK_TRANSFER" ? (
                  <p className="mt-2 text-xs leading-5 text-amber-800">{instructions.bank_transfer} لا تحوّل قبل استلام بيانات الحساب من قناة الدعم الرسمية.</p>
                ) : (
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <p dir="ltr" className="min-w-0 break-all text-left font-mono text-sm font-bold text-slate-900">
                      {method === "INSTAPAY" ? instructions.instapay : instructions.vodafone_cash}
                    </p>
                    <button type="button" onClick={() => void copyAccount()} className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50" aria-label="نسخ بيانات الدفع">
                      <Copy aria-hidden="true" className="size-3.5" /> {copied ? "تم النسخ" : "نسخ"}
                    </button>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="transfer-reference" className="text-xs font-bold text-slate-700">رقم الهاتف أو مرجع التحويل</Label>
                <Input id="transfer-reference" name="transfer_reference" required maxLength={255} value={transferReference} onChange={(event) => setTransferReference(event.target.value)} placeholder="أدخل الرقم أو المرجع الظاهر في إيصالك" dir="auto" className="h-11 border-slate-300 bg-white" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment-proof" className="text-xs font-bold text-slate-700">إثبات الدفع (الإيصال)</Label>
                <label htmlFor="payment-proof" className="flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-white px-3 py-3 text-sm font-semibold text-slate-700 transition hover:border-sky-500 hover:bg-sky-50">
                  <Upload aria-hidden="true" className="size-4 text-sky-700" />
                  <span className="max-w-full truncate">{receipt?.name ?? "اختر صورة أو ملف PDF"}</span>
                </label>
                <input id="payment-proof" name="receipt" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" required className="sr-only" onChange={(event) => setReceipt(event.target.files?.[0] ?? null)} />
                <p className="text-[11px] text-slate-500">PNG أو JPG أو WEBP أو PDF</p>
              </div>

              {enrollment?.status === "pending_payment" && <p className="rounded-md bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">طلب التسجيل موجود بانتظار مراجعة الدفع.</p>}
              {error && <p role="alert" className="flex items-start gap-2 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs leading-5 text-rose-800"><AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />{error}</p>}

              <Button type="submit" disabled={isSubmitting || !instructions} className="h-12 w-full gap-2 bg-sky-700 text-sm font-bold text-white hover:bg-sky-800 disabled:opacity-60">
                {isSubmitting ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <ShieldCheck aria-hidden="true" className="size-4" />}
                {isSubmitting ? "جارٍ إرسال طلبك..." : "احجز مقعدك الآن قبل إغلاق التسجيل 🚀"}
              </Button>
              <p className="text-center text-[11px] leading-5 text-slate-500">سيُراجع الإيصال يدوياً، ثم يتحدث اشتراكك بعد اعتماد الدفع.</p>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}