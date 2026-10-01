import { useState, type ReactNode } from "react";
import { Dialog } from "radix-ui";
import { X } from "lucide-react";

export default function AssignmentDialog({ title, description, onClose, busy = false, children }: {
  title: string;
  description: string;
  onClose: () => void;
  busy?: boolean;
  children: ReactNode;
}) {
  const [opener] = useState(() => document.activeElement);
  return (
    <Dialog.Root open onOpenChange={(open) => { if (!open && !busy) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/50" />
        <Dialog.Content dir="ltr" onCloseAutoFocus={(event) => {
          if (opener instanceof HTMLElement && opener.isConnected) {
            event.preventDefault();
            opener.focus();
          }
        }} className="fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100%_-_2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl bg-white p-6 text-slate-900 shadow-xl">
          <Dialog.Title className="pr-10 text-xl font-bold break-words">{title}</Dialog.Title>
          <Dialog.Description className="mt-2 mb-6 text-sm text-slate-500">{description}</Dialog.Description>
          <Dialog.Close disabled={busy} aria-label="Close assignment dialog" className="absolute top-5 right-5 rounded p-1 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-blue-600">
            <X className="size-5" />
          </Dialog.Close>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
