// يمكنك تمرير بيانات المستخدم كـ Props من الـ AuthContext الخاص بك
interface EWalletCheckoutProps {
  userName: string;
  userEmail: string;
  amount: number;
  currency: string;
  trackName?: string;
}

export default function EWalletCheckout({ 
  userName, 
  userEmail, 
  amount,
  currency,
  trackName = "Backend & AI Engineering" 
}: EWalletCheckoutProps) {
  
  const phoneNumber = "201140225360";
  const formattedAmount = `${new Intl.NumberFormat("en-EG", {
    maximumFractionDigits: 0,
  }).format(amount)} ${currency}`;
  
  // تجهيز الرسالة وتشفيرها لتناسب رابط الـ URL
  const message = `مرحباً، أود تأكيد دفع اشتراكي في مسار (${trackName}).\nقيمة الاشتراك: ${formattedAmount}\nالاسم: ${userName}\nالبريد الإلكتروني: ${userEmail}\n\n*ملاحظة: مرفق مع هذه الرسالة صورة إيصال التحويل.*`;
  const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(message)}`;

  return (
    <div className="max-w-md mx-auto p-6 bg-white border border-slate-200 rounded-xl shadow-sm space-y-6">
      <div className="text-center space-y-2">
        <h3 className="text-2xl font-bold text-slate-800">تأكيد الاشتراك</h3>
        <p className="text-slate-600 text-sm">الدفع عبر المحافظ الإلكترونية (فودافون كاش، اتصالات، أورانج)</p>
      </div>

      <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 space-y-3">
        <p className="text-sm font-medium text-slate-700">قيمة البرنامج: <strong>{formattedAmount}</strong></p>
        <p className="text-sm font-medium text-slate-700">برجاء تحويل قيمة الاشتراك إلى الرقم التالي:</p>
        <div className="text-3xl font-black text-blue-600 text-center tracking-wider py-2">
          +20 11 40225360
        </div>
      </div>

      <div className="space-y-3">
        <h4 className="text-sm font-bold text-slate-700">خطوات التفعيل:</h4>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-2">
          <li>حوّل {formattedAmount} من محفظتك الإلكترونية.</li>
          <li>التقط صورة (Screenshot) واضحة لإيصال التحويل.</li>
          <li>اضغط على الزر بالأسفل لإرسال رسالة التأكيد والصورة عبر واتساب.</li>
          <li>يشمل البرنامج ضمان استرداد 100% من الرسوم.</li>
        </ul>
      </div>
      
      <a 
        href={whatsappUrl} 
        target="_blank" 
        rel="noopener noreferrer"
        className="flex items-center justify-center w-full py-3 mt-4 text-white bg-green-500 rounded-lg font-bold hover:bg-green-600 transition-colors gap-2"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
          <path d="M13.601 2.326A7.854 7.854 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.933 7.933 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.898 7.898 0 0 0 13.6 2.326zM7.994 14.521a6.573 6.573 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.557 6.557 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592zm3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.729.729 0 0 0-.529.247c-.182.198-.691.677-.691 1.654 0 .977.71 1.916.81 2.049.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232z"/>
        </svg>
        إرسال إيصال التأكيد عبر واتساب
      </a>
    </div>
  );
}