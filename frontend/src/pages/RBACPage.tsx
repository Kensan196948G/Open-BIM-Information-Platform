import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  ChevronDown,
  Lock,
  Plus,
  Shield,
  Trash2,
  X,
} from "lucide-react";
import {
  type Organization,
  type Permission,
  type Role,
  rbacApi,
} from "@/api/rbac";

// ─── helpers ───────────────────────────────────────────────────────────────

function groupByCategory(perms: Permission[]): Record<string, Permission[]> {
  return perms.reduce<Record<string, Permission[]>>((acc, p) => {
    (acc[p.category] ??= []).push(p);
    return acc;
  }, {});
}

// ─── sub-components ────────────────────────────────────────────────────────

interface RoleFormProps {
  orgId: string;
  role?: Role;
  onClose: () => void;
}

function RoleForm({ orgId, role, onClose }: RoleFormProps) {
  const qc = useQueryClient();
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => rbacApi.createRole(orgId, { name, description }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles", orgId] });
      onClose();
    },
    onError: () => setError("ロールの作成に失敗しました"),
  });

  const updateMutation = useMutation({
    mutationFn: () => rbacApi.updateRole(role!.id, { name, description }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles", orgId] });
      onClose();
    },
    onError: () => setError("ロールの更新に失敗しました"),
  });

  const isPending = createMutation.isPending || updateMutation.isPending;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("ロール名は必須です");
      return;
    }
    role ? updateMutation.mutate() : createMutation.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {role ? "ロールを編集" : "ロールを作成"}
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">ロール名</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例: プロジェクト閲覧者"
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">
              説明（任意）
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {isPending ? "保存中..." : "保存"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface PermissionPanelProps {
  role: Role;
  orgId: string;
  allPermissions: Permission[];
}

function PermissionPanel({
  role,
  orgId,
  allPermissions,
}: PermissionPanelProps) {
  const qc = useQueryClient();
  const assigned = new Set(role.permissions.map((p) => p.id));
  const grouped = groupByCategory(allPermissions);

  const assignMutation = useMutation({
    mutationFn: (permId: string) => rbacApi.assignPermission(role.id, permId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roles", orgId] }),
  });

  const revokeMutation = useMutation({
    mutationFn: (permId: string) => rbacApi.revokePermission(role.id, permId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roles", orgId] }),
  });

  function toggle(permId: string) {
    if (role.is_system_role) return;
    if (assigned.has(permId)) {
      revokeMutation.mutate(permId);
    } else {
      assignMutation.mutate(permId);
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800/50">
      {role.is_system_role && (
        <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
          <Lock className="h-3 w-3" />
          システムロールの権限は変更できません
        </div>
      )}
      {Object.entries(grouped).map(([category, perms]) => (
        <div key={category}>
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            {category}
          </div>
          <div className="space-y-1">
            {perms.map((p) => {
              const isAssigned = assigned.has(p.id);
              return (
                <button
                  key={p.id}
                  onClick={() => toggle(p.id)}
                  disabled={role.is_system_role}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-zinc-100 disabled:cursor-not-allowed dark:hover:bg-zinc-700"
                >
                  <span
                    className={`flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border ${
                      isAssigned
                        ? "border-blue-600 bg-blue-600 text-white"
                        : "border-zinc-400"
                    }`}
                  >
                    {isAssigned && <Check className="h-3 w-3" />}
                  </span>
                  <span className="flex-1 font-mono text-xs">{p.code}</span>
                  {p.description && (
                    <span className="text-xs text-zinc-500">
                      {p.description}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

interface RoleCardProps {
  role: Role;
  orgId: string;
  allPermissions: Permission[];
  onEdit: (role: Role) => void;
  onDelete: (role: Role) => void;
}

function RoleCard({
  role,
  orgId,
  allPermissions,
  onEdit,
  onDelete,
}: RoleCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900">
      <div className="flex items-start gap-3 p-4">
        <Shield className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-500" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{role.name}</span>
            {role.is_system_role && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                システム
              </span>
            )}
            <span className="text-xs text-zinc-500">
              {role.permissions.length} 権限
            </span>
          </div>
          {role.description && (
            <p className="mt-0.5 text-sm text-zinc-500">{role.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1">
          {!role.is_system_role && (
            <>
              <button
                onClick={() => onEdit(role)}
                className="rounded p-1.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                編集
              </button>
              <button
                onClick={() => onDelete(role)}
                className="rounded p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="rounded p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            <ChevronDown
              className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`}
            />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4">
          <PermissionPanel
            role={role}
            orgId={orgId}
            allPermissions={allPermissions}
          />
        </div>
      )}
    </div>
  );
}

// ─── main page ─────────────────────────────────────────────────────────────

export default function RBACPage() {
  const qc = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [formRole, setFormRole] = useState<Role | "new" | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Role | null>(null);

  const orgsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: rbacApi.listOrganizations,
    select: (data) => {
      if (!selectedOrgId && data.length > 0) {
        setSelectedOrgId(data[0].id);
      }
      return data;
    },
  });

  const permsQuery = useQuery({
    queryKey: ["permissions"],
    queryFn: rbacApi.listPermissions,
  });

  const rolesQuery = useQuery({
    queryKey: ["roles", selectedOrgId],
    queryFn: () => rbacApi.listRoles(selectedOrgId!),
    enabled: !!selectedOrgId,
  });

  const deleteMutation = useMutation({
    mutationFn: (roleId: string) => rbacApi.deleteRole(roleId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles", selectedOrgId] });
      setDeleteTarget(null);
    },
  });

  const orgs: Organization[] = orgsQuery.data ?? [];
  const roles: Role[] = rolesQuery.data ?? [];
  const allPermissions: Permission[] = permsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-4xl p-6">
      {/* header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">ロール・権限管理</h1>
          <p className="mt-1 text-sm text-zinc-500">
            組織ごとのロールと付与された権限を管理します
          </p>
        </div>
        {selectedOrgId && (
          <button
            onClick={() => setFormRole("new")}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            ロールを作成
          </button>
        )}
      </div>

      {/* org selector */}
      {orgs.length > 1 && (
        <div className="mb-6">
          <label className="mb-1.5 block text-sm font-medium">組織を選択</label>
          <select
            value={selectedOrgId ?? ""}
            onChange={(e) => setSelectedOrgId(e.target.value)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* loading / empty states */}
      {orgsQuery.isLoading && (
        <div className="py-16 text-center text-sm text-zinc-500">
          読み込み中...
        </div>
      )}
      {orgsQuery.isSuccess && orgs.length === 0 && (
        <div className="py-16 text-center text-sm text-zinc-500">
          所属している組織がありません
        </div>
      )}

      {/* role list */}
      {selectedOrgId && (
        <>
          {rolesQuery.isLoading && (
            <div className="py-8 text-center text-sm text-zinc-500">
              ロードチュー...
            </div>
          )}
          {rolesQuery.isSuccess && roles.length === 0 && (
            <div className="rounded-xl border border-zinc-200 py-16 text-center text-sm text-zinc-500 dark:border-zinc-700">
              ロールがありません。「ロールを作成」から追加してください。
            </div>
          )}
          <div className="space-y-3">
            {roles.map((role) => (
              <RoleCard
                key={role.id}
                role={role}
                orgId={selectedOrgId}
                allPermissions={allPermissions}
                onEdit={(r) => setFormRole(r)}
                onDelete={(r) => setDeleteTarget(r)}
              />
            ))}
          </div>
        </>
      )}

      {/* create / edit dialog */}
      {formRole !== null && selectedOrgId && (
        <RoleForm
          orgId={selectedOrgId}
          role={formRole === "new" ? undefined : formRole}
          onClose={() => setFormRole(null)}
        />
      )}

      {/* delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900">
            <h2 className="mb-2 text-lg font-semibold">ロールを削除</h2>
            <p className="mb-4 text-sm text-zinc-600 dark:text-zinc-400">
              「{deleteTarget.name}」を削除しますか？この操作は元に戻せません。
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg px-4 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                キャンセル
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                disabled={deleteMutation.isPending}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? "削除中..." : "削除する"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
