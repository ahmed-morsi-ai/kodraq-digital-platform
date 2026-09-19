import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ username: email, password });
      navigate("/dashboard");
    } catch (requestError) {
      console.error("Login failed", requestError);
      setError("Invalid email or password. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050817] px-4 py-12 text-white sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-6rem)] max-w-md items-center">
        <div className="w-full">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-300/20 bg-emerald-300/10 text-lg font-black text-emerald-300">
              KD
            </div>
            <h1 className="text-2xl font-black">Kodraq Digital</h1>
            <p className="mt-2 text-sm text-white/40">
              Access your Kodraq workspace.
            </p>
          </div>

          <Card className="border-white/10 bg-white/[0.04] text-white shadow-2xl backdrop-blur-2xl">
            <CardHeader>
              <CardTitle className="text-2xl font-black">Sign in</CardTitle>
              <CardDescription className="text-white/45">
                Enter your account credentials to continue.
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-5">
                {error && (
                  <div className="rounded-xl border border-red-300/15 bg-red-400/10 p-3 text-sm text-red-200">
                    {error}
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-white/75">
                    Email address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    className="border-white/10 bg-white/[0.04] text-white placeholder:text-white/25"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-white/75">
                    Password
                  </Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    className="border-white/10 bg-white/[0.04] text-white placeholder:text-white/25"
                  />
                </div>
              </CardContent>

              <CardFooter>
                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-emerald-300 to-cyan-300 font-black text-slate-950 hover:brightness-105"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Signing in..." : "Sign in"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
