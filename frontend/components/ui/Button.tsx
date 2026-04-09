"use client";

import React from "react";
import clsx from "clsx";

export function Button({ className, variant = "primary", size = "md", children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary"; size?: "sm" | "md" }) {
  return <button {...props} className={clsx("btn", variant === "secondary" && "btn-secondary", size === "sm" && "btn-sm", className)}>{children}</button>;
}
