"use client";

// UsersTab — the admin user list: search, sortable columns, role cycling
// (click the badge), edit / deactivate / delete, and add-user.

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { clsx } from "clsx";
import { useApp } from "@/lib/store";
import {
  createUser,
  deleteUser,
  listUsers,
  updateUser,
} from "@/lib/admin";
import type { User, UserRole, UserStatus } from "@/lib/types";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { formatDate, timeAgo } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Input } from "@/components/ui/Input";
import { Modal, ModalTitle } from "@/components/ui/Modal";

const ROLE_ORDER: UserRole[] = ["admin", "user", "pending"];

function roleBadgeClass(role: UserRole): string {
  if (role === "admin") {
    return "bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300";
  }
  if (role === "user") {
    return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300";
  }
  return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
}

/** Next role in the click-to-cycle sequence. */
function nextRole(role: UserRole): UserRole {
  const idx = ROLE_ORDER.indexOf(role);
  return ROLE_ORDER[(idx + 1) % ROLE_ORDER.length];
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

interface UserFormState {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

const EMPTY_FORM: UserFormState = {
  name: "",
  email: "",
  password: "",
  role: "user",
};

export function UsersTab() {
  const { user: sessionUser } = useApp();
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<"role" | "name" | "email" | "created_at">(
    "created_at",
  );
  const [sortAsc, setSortAsc] = useState(true);

  const [showAdd, setShowAdd] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [deleting, setDeleting] = useState<User | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      setUsers(await listUsers());
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortAsc((v) => !v);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const rows = query
      ? users.filter(
          (u) =>
            u.name.toLowerCase().includes(query) ||
            u.email.toLowerCase().includes(query),
        )
      : [...users];
    const dir = sortAsc ? 1 : -1;
    rows.sort((a, b) => {
      const av = String(a[sortKey] ?? "");
      const bv = String(b[sortKey] ?? "");
      return av < bv ? -dir : av > bv ? dir : 0;
    });
    return rows;
  }, [users, search, sortKey, sortAsc]);

  const changeRole = async (user: User) => {
    try {
      await updateUser(user.id, { role: nextRole(user.role) });
      toast.success(`Role changed to ${nextRole(user.role)}`);
      reload();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const handleCreate = async (form: UserFormState) => {
    setBusy(true);
    try {
      await createUser({
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role,
      });
      toast.success("User created");
      setShowAdd(false);
      reload();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async (form: UserFormState) => {
    if (!editing) return;
    setBusy(true);
    try {
      await updateUser(editing.id, {
        name: form.name,
        email: form.email,
        role: form.role,
        ...(form.password ? { password: form.password } : {}),
      });
      toast.success("User updated");
      setEditing(null);
      reload();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    setBusy(true);
    try {
      await deleteUser(deleting.id);
      toast.success("User deleted");
      setDeleting(null);
      reload();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const toggleStatus = async (user: User) => {
    const status: UserStatus =
      user.status === "active" ? "deactivated" : "active";
    try {
      await updateUser(user.id, { status });
      toast.success(status === "active" ? "User activated" : "User deactivated");
      reload();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-col gap-1 my-1.5 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center md:self-center text-xl font-medium px-0.5">
          Users
          <div className="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
          <span className="text-lg font-medium text-gray-500 dark:text-gray-300">
            {users.length}
          </span>
        </div>

        <div className="flex w-full md:w-fit space-x-2">
          <div className="flex flex-1 items-center">
            <div className="self-center ml-1 mr-3">
              <Search className="size-3.5" />
            </div>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent dark:text-gray-100"
              placeholder="Search"
            />
          </div>

          <Button variant="ghost" onClick={() => setShowAdd(true)} aria-label="Add User">
            <Plus className="size-3.5" />
          </Button>
        </div>
      </div>

      <div className="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
        <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
          <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
            <tr>
              {(
                [
                  ["role", "Role"],
                  ["name", "Name"],
                  ["email", "Email"],
                  ["created_at", "Created at"],
                ] as const
              ).map(([key, label]) => (
                <th
                  key={key}
                  scope="col"
                  className="px-3 py-1.5 cursor-pointer select-none"
                  onClick={() => toggleSort(key)}
                >
                  <div className="flex gap-1.5 items-center">
                    {label}
                    <span
                      className={clsx(
                        "font-normal",
                        sortKey !== key && "invisible",
                      )}
                    >
                      {sortAsc ? (
                        <ChevronUp className="size-2" />
                      ) : (
                        <ChevronDown className="size-2" />
                      )}
                    </span>
                  </div>
                </th>
              ))}
              <th scope="col" className="px-3 py-1.5 text-right select-none">
                Last Active
              </th>
              <th scope="col" className="px-3 py-2 text-right" />
            </tr>
          </thead>

          <tbody>
            {filtered.map((user) => (
              <tr
                key={user.id}
                className="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs"
              >
                <td className="px-3 py-1 min-w-[7rem] w-28">
                  <button
                    type="button"
                    onClick={() => changeRole(user)}
                    title="Click to change role"
                    className={clsx(
                      "inline-flex items-center px-2 py-0.5 rounded-full text-[0.7rem] font-medium",
                      roleBadgeClass(user.role),
                    )}
                  >
                    {user.role}
                  </button>
                </td>
                <td className="px-3 py-1 font-medium text-gray-900 dark:text-white w-max">
                  <div className="flex flex-row w-max items-center">
                    <span className="flex size-6 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700 text-[0.6rem] font-semibold text-gray-700 dark:text-gray-200 overflow-hidden mr-2.5 shrink-0">
                      {initials(user.name)}
                    </span>
                    <span className="font-medium self-center">{user.name}</span>
                    {user.status === "deactivated" ? (
                      <span className="ml-2 px-1.5 py-0.5 rounded-md bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300 text-[0.6rem]">
                        deactivated
                      </span>
                    ) : null}
                  </div>
                </td>
                <td className="px-3 py-1">{user.email}</td>
                <td className="px-3 py-1">{formatDate(user.created_at)}</td>
                <td className="px-3 py-1 text-right">{timeAgo(user.last_active_at)}</td>
                <td className="px-3 py-1 text-right">
                  <div className="flex justify-end gap-1">
                    {user.id !== sessionUser?.id ? (
                      <Button
                        variant="icon"
                        onClick={() => toggleStatus(user)}
                        title={
                          user.status === "active"
                            ? "Deactivate"
                            : "Activate"
                        }
                        className="text-gray-500 dark:text-gray-400"
                      >
                        {user.status === "active" ? (
                          <ChevronDown className="size-3.5" />
                        ) : (
                          <ChevronUp className="size-3.5" />
                        )}
                      </Button>
                    ) : null}
                    <Button
                      variant="icon"
                      onClick={() => setEditing(user)}
                      title="Edit User"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    {user.id !== sessionUser?.id ? (
                      <Button
                        variant="icon"
                        onClick={() => setDeleting(user)}
                        title="Delete User"
                        className="text-red-500 dark:text-red-400"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-gray-500 dark:text-gray-400 text-xs mt-1.5 text-right">
        ⓘ Click on the user role button to change a user&apos;s role.
      </div>

      <AddUserModal
        open={showAdd}
        busy={busy}
        onClose={() => setShowAdd(false)}
        onSubmit={handleCreate}
      />

      {editing ? (
        <UserEditorModal
          user={editing}
          busy={busy}
          onClose={() => setEditing(null)}
          onSubmit={handleSave}
        />
      ) : null}

      <ConfirmDialog
        open={!!deleting}
        title="Delete User"
        message={`Delete ${deleting?.name ?? "this user"}? This removes their account and can't be undone.`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}

// ---------------------------------------------------------------- modals

function UserFormFields({
  form,
  onChange,
  passwordPlaceholder,
}: {
  form: UserFormState;
  onChange: (patch: Partial<UserFormState>) => void;
  passwordPlaceholder: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <div className="text-sm font-medium mb-1.5">Name</div>
        <Input
          value={form.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="Enter Your Full Name"
        />
      </div>
      <div>
        <div className="text-sm font-medium mb-1.5">Email</div>
        <Input
          type="email"
          value={form.email}
          onChange={(e) => onChange({ email: e.target.value })}
          placeholder="Enter Your Email"
        />
      </div>
      <div>
        <div className="text-sm font-medium mb-1.5">Password</div>
        <Input
          type="password"
          value={form.password}
          onChange={(e) => onChange({ password: e.target.value })}
          placeholder={passwordPlaceholder}
        />
      </div>
      <div>
        <div className="text-sm font-medium mb-1.5">Role</div>
        <select
          value={form.role}
          onChange={(e) => onChange({ role: e.target.value as UserRole })}
          className="bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5 w-full text-sm outline-none dark:text-gray-100"
        >
          <option value="user">user</option>
          <option value="admin">admin</option>
          <option value="pending">pending</option>
        </select>
      </div>
    </div>
  );
}

function AddUserModal({
  open,
  busy,
  onClose,
  onSubmit,
}: {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (form: UserFormState) => void;
}) {
  const [form, setForm] = useState<UserFormState>(EMPTY_FORM);

  // Reset when reopened.
  useEffect(() => {
    if (open) setForm(EMPTY_FORM);
  }, [open]);

  const valid = form.name.trim() && form.email.trim() && form.password.length >= 6;

  return (
    <Modal open={open} onClose={onClose} size="sm">
      <ModalTitle title="Add User" onClose={onClose} />
      <div className="p-3">
        <UserFormFields
          form={form}
          onChange={(patch) => setForm((f) => ({ ...f, ...patch }))}
          passwordPlaceholder="Enter Your Password"
        />
        <div className="mt-4 flex justify-end">
          <Button
            variant="primary"
            disabled={!valid || busy}
            onClick={() => onSubmit(form)}
          >
            Save
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function UserEditorModal({
  user,
  busy,
  onClose,
  onSubmit,
}: {
  user: User;
  busy: boolean;
  onClose: () => void;
  onSubmit: (form: UserFormState) => void;
}) {
  const [form, setForm] = useState<UserFormState>({
    name: user.name,
    email: user.email,
    password: "",
    role: user.role,
  });

  const valid = form.name.trim() && form.email.trim();

  return (
    <Modal open onClose={onClose} size="sm">
      <ModalTitle title="Edit User" onClose={onClose} />
      <div className="p-3">
        <UserFormFields
          form={form}
          onChange={(patch) => setForm((f) => ({ ...f, ...patch }))}
          passwordPlaceholder="Leave blank to keep current password"
        />
        <div className="mt-4 flex justify-end">
          <Button
            variant="primary"
            disabled={!valid || busy}
            onClick={() => onSubmit(form)}
          >
            Save
          </Button>
        </div>
      </div>
    </Modal>
  );
}
