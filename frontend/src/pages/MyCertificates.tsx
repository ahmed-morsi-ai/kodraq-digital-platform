import { useCallback, useEffect, useState } from "react";
import { isAxiosError } from "axios";
import {
  Award,
  ExternalLink,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { certificateService } from "@/services/certificate.service";
import type { Certificate } from "@/types/certificate";

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return "Unable to load your certificates right now.";
}

export default function MyCertificates() {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCertificates = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await certificateService.getMyCertificates();
      setCertificates(data);
    } catch (requestError) {
      console.error("Failed to load certificates", requestError);
      setCertificates([]);
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCertificates();
  }, [loadCertificates]);

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-64px)] items-center justify-center px-6 py-12">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
            <Loader2 className="h-7 w-7 animate-spin" />
          </div>

          <h1 className="mt-5 text-lg font-semibold text-slate-900">
            Loading certificates
          </h1>

          <p className="mt-2 text-sm text-gray-500">
            Retrieving your earned credentials...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full px-6 py-8 md:py-12">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="overflow-hidden rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-950 via-slate-950 to-slate-900 p-6 text-white shadow-xl md:p-10">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs font-semibold text-emerald-200">
                <Award className="h-3.5 w-3.5" />
                Kodraq credentials
              </div>

              <h1 className="mt-5 text-3xl font-black tracking-tight md:text-5xl">
                My Certificates
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/60 md:text-base">
                Keep your verified graduation credentials in one place and
                share them with employers or clients.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-center">
              <p className="text-3xl font-black text-emerald-300">
                {certificates.length}
              </p>
              <p className="text-xs uppercase tracking-[0.18em] text-white/40">
                Certificates
              </p>
            </div>
          </div>
        </section>

        {error && (
          <Card className="border-red-200 bg-red-50 shadow-sm">
            <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm leading-6 text-red-700">{error}</p>
              <Button
                type="button"
                variant="outline"
                onClick={() => void loadCertificates()}
                className="gap-2 border-red-200 bg-white"
              >
                <RefreshCw className="h-4 w-4" />
                Retry
              </Button>
            </CardContent>
          </Card>
        )}

        {certificates.length === 0 ? (
          <Card className="border-gray-200 shadow-sm">
            <CardContent className="flex flex-col items-center px-6 py-16 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                <ShieldCheck className="h-8 w-8" />
              </div>

              <h2 className="mt-5 text-xl font-semibold text-slate-900">
                No certificates yet
              </h2>

              <p className="mt-2 max-w-lg text-sm leading-6 text-gray-500">
                Complete and pass your final project, then return here to
                manage your issued certificates.
              </p>

              <Button
                asChild
                className="mt-6 bg-blue-600 text-white hover:bg-blue-700"
              >
                <Link to="/my-learning">Back to My Learning</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {certificates.map((certificate) => (
              <Card
                key={certificate.id}
                className="overflow-hidden border-gray-200 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                <CardHeader className="border-b border-gray-100 bg-gradient-to-br from-emerald-50 via-white to-white">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                      <Award className="h-5 w-5" />
                    </div>

                    <span className="inline-flex rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                      {certificate.status}
                    </span>
                  </div>

                  <div>
                    <CardTitle className="mt-4 text-lg text-slate-900">
                      Graduation Certificate
                    </CardTitle>
                    <CardDescription className="mt-2 break-all text-xs">
                      {certificate.certificate_number}
                    </CardDescription>
                  </div>
                </CardHeader>

                <CardContent className="space-y-5 p-6">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                        Issued
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-800">
                        {new Date(
                          certificate.created_at,
                        ).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                        Final score
                      </p>
                      <p className="mt-1 text-sm font-semibold text-slate-800">
                        {certificate.final_score !== null
                          ? `${certificate.final_score}/100`
                          : "—"}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button
                      asChild
                      className="flex-1 gap-2 bg-slate-950 text-white hover:bg-slate-800"
                    >
                      <Link
                        to={`/verify/${encodeURIComponent(
                          certificate.certificate_number,
                        )}`}
                      >
                        <ShieldCheck className="h-4 w-4" />
                        Verify
                      </Link>
                    </Button>

                    {certificate.file_url && (
                      <Button
                        asChild
                        variant="outline"
                        className="gap-2"
                      >
                        <a
                          href={certificate.file_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open file
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
