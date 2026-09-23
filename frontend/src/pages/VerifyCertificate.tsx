import { useCallback, useEffect, useState } from "react";
import {
  Award,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Search,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { certificateService } from "@/services/certificate.service";
import type { CertificateVerification } from "@/types/certificate";

export default function VerifyCertificate() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<CertificateVerification | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [invalid, setInvalid] = useState(false);

  const verify = useCallback(async () => {
    if (!code?.trim()) {
      setInvalid(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setInvalid(false);

    try {
      const verification = await certificateService.verifyCertificate(code);
      setResult(verification);
    } catch (error) {
      console.error("Certificate verification failed", error);
      setResult(null);
      setInvalid(true);
    } finally {
      setIsLoading(false);
    }
  }, [code]);

  useEffect(() => {
    void verify();
  }, [verify]);

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-10 text-white md:py-16">
      <div className="mx-auto flex min-h-[calc(100vh-80px)] max-w-5xl items-center justify-center">
        {isLoading ? (
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-300/20 bg-emerald-300/10 text-emerald-300">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>

            <h1 className="mt-6 text-2xl font-bold">
              Verifying certificate
            </h1>

            <p className="mt-2 text-sm text-white/50">
              Checking the credential against Kodraq Digital records...
            </p>
          </div>
        ) : invalid || !result?.valid ? (
          <Card className="w-full max-w-2xl border-red-300/20 bg-white text-slate-900 shadow-2xl">
            <CardContent className="flex flex-col items-center px-6 py-14 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 text-red-600">
                <XCircle className="h-8 w-8" />
              </div>

              <h1 className="mt-6 text-2xl font-bold">
                Certificate Not Found / Invalid
              </h1>

              <p className="mt-3 max-w-lg text-sm leading-6 text-gray-500">
                The certificate code could not be verified against Kodraq
                Digital&apos;s public credential records.
              </p>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Button
                  type="button"
                  onClick={() => void verify()}
                  className="gap-2 bg-slate-950 text-white hover:bg-slate-800"
                >
                  <Search className="h-4 w-4" />
                  Try again
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/")}
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back home
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="w-full max-w-4xl">
            <div className="mb-8 text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 py-2 text-xs font-semibold text-emerald-200">
                <ShieldCheck className="h-4 w-4" />
                Verified credential
              </div>

              <h1 className="mt-5 text-3xl font-black tracking-tight md:text-5xl">
                Certificate Verification
              </h1>

              <p className="mt-3 text-sm text-white/50">
                This credential has been verified by Kodraq Digital.
              </p>
            </div>

            <Card className="overflow-hidden border-emerald-200 bg-white text-slate-900 shadow-2xl">
              <div className="border-b border-emerald-100 bg-gradient-to-br from-emerald-950 via-slate-950 to-slate-900 p-6 text-white md:p-10">
                <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-300/10 text-emerald-300">
                      <Award className="h-7 w-7" />
                    </div>

                    <p className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200/60">
                      Kodraq Digital
                    </p>

                    <h2 className="mt-2 text-3xl font-black">
                      Graduation Certificate
                    </h2>
                  </div>

                  <div className="inline-flex items-center gap-2 self-start rounded-full bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-200">
                    <CheckCircle2 className="h-4 w-4" />
                    Verified by Kodraq Digital
                  </div>
                </div>
              </div>

              <CardContent className="space-y-6 p-6 md:p-10">
                <div className="grid gap-5 md:grid-cols-2">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Student
                    </p>
                    <p className="mt-2 text-xl font-bold text-slate-900">
                      {result.student_name}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Track
                    </p>
                    <p className="mt-2 text-xl font-bold text-slate-900">
                      {result.track_name}
                    </p>
                  </div>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Issue date
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-800">
                      {new Date(result.issue_date).toLocaleDateString()}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Certificate number
                    </p>
                    <p className="mt-2 break-all text-sm font-semibold text-slate-800">
                      {result.certificate_number}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                  <div className="flex items-start gap-3">
                    <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />
                    <div>
                      <p className="font-semibold text-emerald-900">
                        Verified by Kodraq Digital
                      </p>
                      <p className="mt-1 text-sm leading-6 text-emerald-800/80">
                        This public verification result confirms that the
                        certificate number belongs to a credential recorded by
                        Kodraq Digital.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:justify-between">
                  <Button
                    asChild
                    variant="outline"
                    className="gap-2"
                  >
                    <Link to="/">
                      <ArrowLeft className="h-4 w-4" />
                      Kodraq Digital
                    </Link>
                  </Button>

                  <Button
                    type="button"
                    onClick={() => window.print()}
                    className="bg-slate-950 text-white hover:bg-slate-800"
                  >
                    Print verification
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
