import {
  FileEdit,
  Send,
  RotateCcw,
  CheckCircle2,
  type LucideIcon,
} from "lucide-react";

export type QuestionStatus =
  | "DRAFT"
  | "VERIFICATION"
  | "REVISION"
  | "IN_BANK";

export const STATUS_CONFIG: Record<
  QuestionStatus,
  {
    label: string;
    class: string;
    icon: LucideIcon;
    color: string;
  }
> = {
  DRAFT: {
    label: "Черновик",
    class: "badge-draft",
    icon: FileEdit,
    color: "text-gray-500",
  },
  VERIFICATION: {
    label: "На проверке",
    class: "badge-verification",
    icon: Send,
    color: "text-amber-600",
  },
  REVISION: {
    label: "Доработка",
    class: "badge-revision",
    icon: RotateCcw,
    color: "text-red-600",
  },
  IN_BANK: {
    label: "В банке",
    class: "badge-in-bank",
    icon: CheckCircle2,
    color: "text-green-600",
  },
};

export function getStatusBadge(status: QuestionStatus) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.DRAFT;
}
