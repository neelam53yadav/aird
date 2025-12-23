"use client"

import { SessionProvider } from "next-auth/react"
import { ReactNode } from "react"
import { ToastProvider } from "@/components/ui/toast"

interface ProvidersProps {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <SessionProvider>
      <ToastProvider>
        {children}
      </ToastProvider>
    </SessionProvider>
  )
}
