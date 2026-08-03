import {
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  ClipboardList,
  FileQuestion,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
} from "lucide-react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import toast from "react-hot-toast";

import { api } from "../services/api";


type VariantStatus =
  | "DRAFT"
  | "VERIFICATION"
  | "REVISION"
  | "APPROVED"
  | "IN_BANK";


interface Variant {
  id: number;
  title: string;
  description: string | null;
  subject_id: number | null;
  developer_id: number;
  status: VariantStatus;
  question_count: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
}


interface VariantListResponse {
  items: Variant[];
  total: number;
  page: number;
  page_size: number;
}


interface VariantDashboard {
  total_variants: number;
  draft_variants: number;
  verification_variants: number;
  revision_variants: number;
  approved_variants: number;
  bank_variants: number;
  total_questions: number;
}


interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}


const PAGE_SIZE = 20;


const STATUS_LABELS: Record<VariantStatus, string> = {
  DRAFT: "Черновик",
  VERIFICATION: "На верификации",
  REVISION: "На доработке",
  APPROVED: "Утверждён",
  IN_BANK: "В банке",
};


const STATUS_CLASSES: Record<VariantStatus, string> = {
  DRAFT: "badge bg-gray-100 text-gray-700",
  VERIFICATION: "badge bg-blue-100 text-blue-800",
  REVISION: "badge bg-amber-100 text-amber-800",
  APPROVED: "badge bg-green-100 text-green-800",
  IN_BANK: "badge bg-purple-100 text-purple-800",
};


function getErrorMessage(
  error: unknown,
  fallback: string
): string {
  const apiError = error as ApiError;
  const detail = apiError.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  return fallback;
}


export default function DeveloperPage() {
  const [variants, setVariants] = useState<Variant[]>([]);

  const [dashboard, setDashboard] =
    useState<VariantDashboard>({
      total_variants: 0,
      draft_variants: 0,
      verification_variants: 0,
      revision_variants: 0,
      approved_variants: 0,
      bank_variants: 0,
      total_questions: 0,
    });

  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const [statusFilter, setStatusFilter] =
    useState<VariantStatus | "">("");

  const [loading, setLoading] = useState(true);


  useEffect(() => {
    const loadDeveloperData = async (): Promise<void> => {
      setLoading(true);

      try {
        const params: {
          page: number;
          page_size: number;
          status?: VariantStatus;
        } = {
          page,
          page_size: PAGE_SIZE,
        };

        if (statusFilter) {
          params.status = statusFilter;
        }

        const [variantsResponse, dashboardResponse] =
          await Promise.all([
            api.get<VariantListResponse>(
              "/api/v1/variants/my",
              {
                params,
              }
            ),

            api.get<VariantDashboard>(
              "/api/v1/variants/dashboard"
            ),
          ]);

        setVariants(variantsResponse.data.items);
        setTotal(variantsResponse.data.total);
        setDashboard(dashboardResponse.data);
      } catch (error: unknown) {
        toast.error(
          getErrorMessage(
            error,
            "Не удалось загрузить кабинет разработчика."
          )
        );
      } finally {
        setLoading(false);
      }
    };

    void loadDeveloperData();
  }, [page, statusFilter]);


  const totalPages = Math.max(
    1,
    Math.ceil(total / PAGE_SIZE)
  );


  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Мои варианты
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Создавайте варианты и добавляйте внутрь вопросы
          </p>
        </div>

        <Link
          to="/variants/new"
          className="btn-primary"
        >
          <Plus className="h-4 w-4" />
          Новый вариант
        </Link>
      </div>


      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <DashboardCard
          label="Всего вариантов"
          value={dashboard.total_variants}
          icon={<ClipboardList className="h-5 w-5" />}
        />

        <DashboardCard
          label="Всего вопросов"
          value={dashboard.total_questions}
          icon={<FileQuestion className="h-5 w-5" />}
        />

        <DashboardCard
          label="Черновики"
          value={dashboard.draft_variants}
          icon={<RefreshCw className="h-5 w-5" />}
        />

        <DashboardCard
          label="На верификации"
          value={dashboard.verification_variants}
          icon={<Send className="h-5 w-5" />}
        />

        <DashboardCard
          label="На доработке"
          value={dashboard.revision_variants}
          icon={<RotateCcw className="h-5 w-5" />}
          warning={dashboard.revision_variants > 0}
        />

        <DashboardCard
          label="Утверждено"
          value={dashboard.approved_variants}
          icon={<CheckCircle2 className="h-5 w-5" />}
        />

        <DashboardCard
          label="В банке"
          value={dashboard.bank_variants}
          icon={<CheckCircle2 className="h-5 w-5" />}
        />
      </section>


      <section className="flex flex-wrap items-center justify-between gap-3">
        <select
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(
              event.target.value as VariantStatus | ""
            );
            setPage(1);
          }}
          className="input-field w-full sm:w-56"
        >
          <option value="">
            Все статусы
          </option>

          <option value="DRAFT">
            Черновики
          </option>

          <option value="VERIFICATION">
            На верификации
          </option>

          <option value="REVISION">
            На доработке
          </option>

          <option value="APPROVED">
            Утверждённые
          </option>

          <option value="IN_BANK">
            В банке
          </option>
        </select>

        <p className="text-sm text-gray-500">
          Найдено вариантов: {total}
        </p>
      </section>


      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : variants.length === 0 ? (
        <section className="card py-12 text-center">
          <ClipboardList className="mx-auto h-12 w-12 text-gray-300" />

          <h2 className="mt-4 text-lg font-semibold text-gray-900">
            Вариантов пока нет
          </h2>

          <p className="mx-auto mt-2 max-w-md text-sm text-gray-500">
            Создайте первый вариант, затем добавьте в него
            необходимое количество вопросов.
          </p>

          <Link
            to="/variants/new"
            className="btn-primary mt-5"
          >
            <Plus className="h-4 w-4" />
            Создать первый вариант
          </Link>
        </section>
      ) : (
        <section className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <TableHeader>ID</TableHeader>
                  <TableHeader>Вариант</TableHeader>
                  <TableHeader>Предмет</TableHeader>
                  <TableHeader>Вопросы</TableHeader>
                  <TableHeader>Статус</TableHeader>
                  <TableHeader>Обновлён</TableHeader>
                  <TableHeader>Действия</TableHeader>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-200 bg-white">
                {variants.map((variant) => (
                  <tr
                    key={variant.id}
                    className="hover:bg-gray-50"
                  >
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      #{variant.id}
                    </td>

                    <td className="min-w-64 px-6 py-4">
                      <Link
                        to={`/variants/${variant.id}`}
                        className="text-sm font-medium text-gray-900 hover:text-primary-600"
                      >
                        {variant.title}
                      </Link>

                      {variant.description && (
                        <p className="mt-1 line-clamp-2 text-xs text-gray-500">
                          {variant.description}
                        </p>
                      )}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                      {variant.subject_id === null
                        ? "Не назначен"
                        : `Предмет #${variant.subject_id}`}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                      {variant.question_count}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4">
                      <span
                        className={
                          STATUS_CLASSES[variant.status]
                        }
                      >
                        {STATUS_LABELS[variant.status]}
                      </span>
                    </td>

                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {format(
                        new Date(variant.updated_at),
                        "d MMM yyyy, HH:mm",
                        {
                          locale: ru,
                        }
                      )}
                    </td>

                    <td className="whitespace-nowrap px-6 py-4">
                      <Link
                        to={`/variants/${variant.id}`}
                        className="font-medium text-primary-600 hover:text-primary-500"
                      >
                        Открыть
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}


      {total > PAGE_SIZE && (
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => {
              setPage((current) =>
                Math.max(1, current - 1)
              );
            }}
            disabled={page === 1}
            className="btn-secondary"
          >
            Назад
          </button>

          <span className="text-sm text-gray-500">
            Страница {page} из {totalPages}
          </span>

          <button
            type="button"
            onClick={() => {
              setPage((current) =>
                Math.min(totalPages, current + 1)
              );
            }}
            disabled={page >= totalPages}
            className="btn-secondary"
          >
            Вперёд
          </button>
        </div>
      )}
    </div>
  );
}


function DashboardCard({
  label,
  value,
  icon,
  warning = false,
}: {
  label: string;
  value: number;
  icon: ReactNode;
  warning?: boolean;
}) {
  return (
    <div className="card flex items-center gap-4">
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${
          warning
            ? "bg-amber-100 text-amber-700"
            : "bg-primary-100 text-primary-700"
        }`}
      >
        {icon}
      </div>

      <div>
        <p className="text-2xl font-bold text-gray-900">
          {value}
        </p>

        <p className="text-xs text-gray-500">
          {label}
        </p>
      </div>
    </div>
  );
}


function TableHeader({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
      {children}
    </th>
  );
}