import { BlackboxChatWidget } from "@/components/BlackboxChatWidget";

export default function BlackboxopsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <BlackboxChatWidget />
    </>
  );
}
