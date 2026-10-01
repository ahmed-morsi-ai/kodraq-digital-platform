import { useState } from "react";
import { CreditCard, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import type { TrackCurriculum } from "@/types/track";
import type { Enrollment } from "@/types/enrollment";

interface PaymentCheckoutProps {
  track: TrackCurriculum;
  enrollment?: Enrollment;
}

function formatAmount(amount: number, currency: string): string {
  return `${new Intl.NumberFormat("en-EG", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)} ${currency}`;
}

export default function PaymentCheckout({
  track,
  enrollment,
}: PaymentCheckoutProps) {
  const [email, setEmail] = useState("");
  const amount = Number(track.price ?? 0);
  
  const hasPendingPayment = enrollment?.status === "pending_payment";
  const isAlreadyEnrolled =
    enrollment?.status === "active" || enrollment?.status === "completed";

  // إخفاء المكون إذا كان المسار مجانياً أو الطالب مشترك بالفعل
  if (!track.is_premium || isAlreadyEnrolled) {
    return null;
  }

  // دالة تحويل المستخدم للواتساب مع رسالة جاهزة
  const handleWhatsAppRedirect = () => {
    const message = `مرحباً، أود تأكيد اشتراكي في مسار "${track.name}".\nإيميلي المسجل هو: ${email}\n\n(سأقوم بإرفاق صورة إيصال التحويل الآن)`;
    const whatsappUrl = `https://wa.me/201140225360?text=${encodeURIComponent(message)}`;
    window.open(whatsappUrl, "_blank");
  };

  return (
    <Card className="border-blue-200 shadow-sm mt-8">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <CreditCard className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-slate-900">حجز التدريب الاحترافي</CardTitle>
            <CardDescription className="mt-1 space-y-1">
              <p>
                استثمار التدريب: <strong>{formatAmount(amount, track.currency)}</strong>. 
                يشمل البرنامج ضمان استرداد 100% من الرسوم. المتفوقون أصحاب النتائج المرتفعة لديهم احتمالية عالية للحصول على فرص توظيف.
              </p>
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* صندوق التعليمات الجديد */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-900 space-y-3">
          <p className="font-bold text-base">خطوات الاشتراك والاستلام السريع:</p>
          <ol className="list-decimal list-inside space-y-2 ml-2">
            <li>قم بتحويل المبلغ <strong>({formatAmount(amount, track.currency)})</strong> عبر المحافظ الإلكترونية.</li>
            <li><strong>فودافون كاش / اتصالات كاش / انستاباي:</strong> على الرقم <span className="font-mono font-bold mx-1 text-lg">01140225360</span></li>
            <li>أدخل إيميلك بالأسفل واضغط على زر الواتساب لإرسال الإيصال.</li>
            <li>بمجرد المراجعة، سيتم إرسال رابط <strong>Google Drive</strong> الذي يحتوي على الفيديوهات والملفات مباشرة إلى إيميلك (Gmail).</li>
          </ol>
        </div>

        {/* نموذج إدخال الإيميل والتحويل للواتساب */}
        <div className="grid gap-5 bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="space-y-3">
            <Label htmlFor="registered-email" className="text-slate-700 font-semibold">
              البريد الإلكتروني (Gmail) لاستلام ملفات التدريب
            </Label>
            <Input
              id="registered-email"
              type="email"
              placeholder="example@gmail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="text-left bg-slate-50 border-slate-300 focus-visible:ring-emerald-500 h-11"
              dir="ltr"
            />
          </div>

          <Button
            type="button"
            disabled={!email.includes('@')}
            onClick={handleWhatsAppRedirect}
            className="w-full gap-2 bg-[#25D366] text-white hover:bg-[#20bd5a] text-base h-12 shadow-md transition-all"
          >
            <Send className="h-5 w-5" />
            إرسال الإيصال وتأكيد الحجز عبر واتساب
          </Button>
        </div>
        
        {hasPendingPayment && (
           <div className="text-center text-sm font-medium text-amber-700 mt-2 bg-amber-50 p-2 rounded-lg border border-amber-200">
             طلبك معلق حالياً، يرجى التأكد من إرسال الإيصال على الواتساب لتسريع الاستلام.
           </div>
        )}
      </CardContent>
    </Card>
  );
}