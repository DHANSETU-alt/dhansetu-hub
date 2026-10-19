"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

type AuthUser = { email: string; signedIn: true };

export default function AuthModal({
  open,
  onClose,
  onSignedIn,
}: {
  open: boolean;
  onClose: () => void;
  onSignedIn: (user: AuthUser) => void;
}) {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [step, setStep] = useState<"email" | "otp">("email");
  const inputs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    if (!open) {
      setStep("email");
      setOtp(["", "", "", "", "", ""]);
    }
  }, [open]);

  if (!open) return null;

  function submitEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (email.trim()) {
      setStep("otp");
      window.setTimeout(() => inputs.current[0]?.focus(), 0);
    }
  }

  function updateOtp(index: number, value: string) {
    const digit = value.replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[index] = digit;
    setOtp(next);
    if (digit && index < 5) inputs.current[index + 1]?.focus();
  }

  function submitOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (otp.join("").length !== 6) return;
    const user = { email: email.trim(), signedIn: true as const };
    localStorage.setItem("dhansetu_user", JSON.stringify(user));
    onSignedIn(user);
    onClose();
  }

  return (
    <div className="auth-modal__backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="auth-modal__close" type="button" onClick={onClose} aria-label="Close sign in">×</button>
        <div className="auth-modal__logo" aria-hidden="true">D</div>
        <h2 id="auth-title">Welcome back</h2>
        <p>Sign in to your private workspace</p>
        {step === "email" ? (
          <form onSubmit={submitEmail}>
            <label htmlFor="auth-email">Email address</label>
            <input id="auth-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="your@email.com" required autoFocus />
            <button className="auth-modal__primary" type="submit">Continue with Email</button>
            <div className="auth-modal__divider"><span>or</span></div>
            <button className="auth-modal__google" type="button" onClick={() => setStep("otp")}>Continue with Google</button>
          </form>
        ) : (
          <form onSubmit={submitOtp}>
            <label htmlFor="auth-otp-0">Enter the 6-digit code</label>
            <div className="auth-modal__otp" aria-label="One-time password">
              {otp.map((digit, index) => <input key={index} id={`auth-otp-${index}`} ref={(element) => { inputs.current[index] = element; }} inputMode="numeric" maxLength={1} value={digit} onChange={(event) => updateOtp(index, event.target.value)} aria-label={`Digit ${index + 1}`} />)}
            </div>
            <button className="auth-modal__primary" type="submit">Verify and Sign in</button>
            <button className="auth-modal__back" type="button" onClick={() => setStep("email")}>Use a different email</button>
          </form>
        )}
      </section>
    </div>
  );
}
