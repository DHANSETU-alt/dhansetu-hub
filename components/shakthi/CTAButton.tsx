"use client";

import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { auditId: string };

export function CTAButton({ auditId, onClick, ...props }: Props) {
  return <button {...props} data-audit-id={auditId} onClick={(event) => {
    window.dispatchEvent(new CustomEvent("shakthi:cta", { detail: { auditId } }));
    onClick?.(event);
  }} />;
}
