"use client";

// EvaluationsTab — the admin evaluations panel: enable/mode config, plus the
// Feedback History table (list, delete rows, export, clear all).
//
// The upstream arena-style leaderboard is not included (client-side Elo was
// driven by onnxruntime-web/transformers embeddings); feedback itself is.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, EllipsisVertical, Trash2 } from "lucide-react";
import {
  deleteAllFeedbacks,
  deleteFeedback,
  exportFeedbacks,
  getEvalConfig,
  listAllFeedbacks,
  setEvalConfig,
  type EvalConfig,
} from "@/lib/admin";
import type { EvaluationFeedback } from "@/lib/types";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { timeAgo } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Dropdown, DropdownItem } from "@/components/ui/Dropdown";
import { Input } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Result badge: 1 = won, 0 = draw, -1 = lost; otherwise plain rating. */
function ResultBadge({ rating }: { rating: number }) {
  if (rating === 1) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.7rem] font-medium bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300">
        Won
      </span>
    );
  }
  if (rating === 0) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.7rem] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
        Draw
      </span>
    );
  }
  if (rating === -1) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.7rem] font-medium bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300">
        Lost
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.7rem] font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
      {rating}
    </span>
  );
}

function downloadJson(rows: EvaluationFeedback[]) {
  const blob = new Blob([JSON.stringify(rows, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `feedback-history-export-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function EvaluationsTab() {
  const [config, setConfig] = useState<EvalConfig>({
    enable_evaluations: false,
    model: "",
  });
  const [configLoaded, setConfigLoaded] = useState(false);
  const [feedbacks, setFeedbacks] = useState<EvaluationFeedback[]>([]);
  const [page, setPage] = useState(1);
  const [clearing, setClearing] = useState(false);
  const [deleting, setDeleting] = useState<EvaluationFeedback | null>(null);

  const reload = useCallback(async () => {
    try {
      setFeedbacks(await listAllFeedbacks());
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await getEvalConfig();
        setConfig(cfg);
      } catch (error) {
        toast.error(errorMessage(error));
      } finally {
        setConfigLoaded(true);
      }
    })();
    reload();
  }, [reload]);

  const saveConfig = async (patch: Partial<EvalConfig>) => {
    const next = { ...config, ...patch };
    setConfig(next);
    try {
      await setEvalConfig(next);
      toast.success("Settings saved successfully");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const handleExport = async () => {
    try {
      const rows = await exportFeedbacks();
      downloadJson(rows);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await deleteFeedback(deleting.id);
      toast.success("Feedback deleted");
      setDeleting(null);
      reload();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const handleClearAll = async () => {
    setClearing(true);
    try {
      await deleteAllFeedbacks();
      toast.success("All feedback cleared");
      reload();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setClearing(false);
    }
  };

  const perPage = 10;
  const pages = Math.max(1, Math.ceil(feedbacks.length / perPage));
  const pageRows = useMemo(
    () => feedbacks.slice((page - 1) * perPage, page * perPage),
    [feedbacks, page],
  );

  return (
    <div className="flex flex-col h-full">
      {/* config */}
      <div className="flex flex-col gap-3 my-1.5 text-sm">
        <div className="text-xl font-medium px-0.5">Evaluations</div>

        <div className="flex flex-col gap-4 rounded-2xl p-4 bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-850">
          <div className="flex items-start justify-between gap-4 w-full">
            <div className="min-w-0">
              <div className="text-sm font-medium">Enable Evaluations</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Allow users to rate model responses in chat.
              </div>
            </div>
            <Toggle
              checked={config.enable_evaluations}
              disabled={!configLoaded}
              onChange={(value) => saveConfig({ enable_evaluations: value })}
            />
          </div>

          <div>
            <div className="text-sm font-medium mb-1.5">Default Model</div>
            <Input
              value={config.model}
              onChange={(e) => setConfig((c) => ({ ...c, model: e.target.value }))}
              onBlur={() => saveConfig({ model: config.model.trim() })}
              placeholder="Model used for evaluation requests"
              className="max-w-sm"
            />
          </div>
        </div>
      </div>

      {/* feedback history */}
      <div className="flex flex-col gap-1 my-1.5 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center md:self-center text-lg font-medium px-0.5">
          Feedback History
          <div className="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
          <span className="text-lg font-medium text-gray-500 dark:text-gray-300">
            {feedbacks.length}
          </span>
        </div>

        <div className="flex gap-1">
          <Button
            variant="ghost"
            onClick={handleClearAll}
            disabled={clearing || feedbacks.length === 0}
            title="Clear all feedback"
          >
            <Trash2 className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            onClick={handleExport}
            disabled={feedbacks.length === 0}
            title="Export"
          >
            <Download className="size-3.5" />
          </Button>
        </div>
      </div>

      <div className="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
        {pageRows.length === 0 ? (
          <div className="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
            No feedbacks found
          </div>
        ) : (
          <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
              <tr>
                <th scope="col" className="px-3 text-right cursor-pointer select-none w-0">
                  User
                </th>
                <th scope="col" className="px-3 pr-1.5 cursor-pointer select-none">
                  Models
                </th>
                <th scope="col" className="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
                  Result
                </th>
                <th scope="col" className="px-3 py-1.5 text-right cursor-pointer select-none w-0">
                  Updated At
                </th>
                <th scope="col" className="px-3 py-1.5 text-right cursor-pointer select-none w-0" />
              </tr>
            </thead>
            <tbody>
              {pageRows.map((feedback) => {
                const data = feedback.data ?? {};
                const modelId =
                  (data.model_id as string | undefined) ?? "—";
                const rating = Number(data.rating ?? data.score ?? 0);
                return (
                  <tr
                    key={feedback.id}
                    className="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs"
                  >
                    <td className="py-0.5 text-right font-semibold">
                      <div className="flex justify-center">
                        <span
                          title={feedback.user?.name ?? feedback.user_id}
                          className="flex size-5 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700 text-[0.55rem] font-semibold text-gray-700 dark:text-gray-200 overflow-hidden shrink-0"
                        >
                          {initials(feedback.user?.name ?? "?")}
                        </span>
                      </div>
                    </td>
                    <td className="py-1 pl-3">
                      <div className="text-sm font-medium text-gray-600 dark:text-gray-400 py-1.5">
                        {modelId}
                      </div>
                    </td>
                    <td className="px-3 py-1 text-right font-medium text-gray-900 dark:text-white w-max">
                      <div className="flex justify-end">
                        <ResultBadge rating={rating} />
                      </div>
                    </td>
                    <td className="px-3 py-1 text-right font-medium">
                      {timeAgo(feedback.updated_at ?? feedback.created_at)}
                    </td>
                    <td className="px-3 py-1 text-right font-semibold">
                      <Dropdown
                        trigger={
                          <span className="inline-flex p-1.5 rounded-xl hover:bg-black/5 dark:hover:bg-white/5">
                            <EllipsisVertical className="size-4" />
                          </span>
                        }
                      >
                        <div className="text-sm rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary min-w-36">
                          <DropdownItem
                            onClick={() => setDeleting(feedback)}
                            className="text-red-600 dark:text-red-500"
                          >
                            <Trash2 className="size-4" /> Delete
                          </DropdownItem>
                        </div>
                      </Dropdown>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {feedbacks.length > perPage ? (
        <div className="flex flex-col justify-end w-full text-right gap-1">
          <div className="flex gap-1 justify-end items-center text-sm">
            <Button
              variant="ghost"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              ‹
            </Button>
            <span className="px-2 text-xs text-gray-500 dark:text-gray-400">
              {page} / {pages}
            </span>
            <Button
              variant="ghost"
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
            >
              ›
            </Button>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={!!deleting}
        title="Delete Feedback"
        message="Delete this feedback row?"
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
      />

      <ConfirmDialog
        open={clearing}
        title="Clear All Feedback"
        message="Delete every feedback row?"
        confirmLabel="Clear All"
        onConfirm={handleClearAll}
        onCancel={() => setClearing(false)}
      />
    </div>
  );
}
