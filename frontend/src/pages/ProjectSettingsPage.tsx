import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { API_BASE, authPaths, badgeUrl, type OwnedProject } from "../api";
import { useAuth } from "../auth";
import TokenReveal from "../components/TokenReveal";

export default function ProjectSettingsPage() {
  const { slug } = useParams<{ slug: string }>();
  const { authFetch } = useAuth();

  const [project, setProject] = useState<OwnedProject | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [repo, setRepo] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  const [confirmingRegen, setConfirmingRegen] = useState(false);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [regenError, setRegenError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    authFetch<OwnedProject>(authPaths.myProject(slug))
      .then((p) => {
        setProject(p);
        setRepo(p.repo);
        setDefaultBranch(p.default_branch);
        setIsPublic(p.is_public);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : String(err)));
  }, [slug, authFetch]);

  async function onSave() {
    if (!slug) return;
    setSaveError(null);
    setSaved(false);
    setBusy(true);
    try {
      const updated = await authFetch<OwnedProject>(authPaths.myProject(slug), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo, default_branch: defaultBranch, is_public: isPublic }),
      });
      setProject(updated);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1500);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  async function onRegenerate() {
    if (!slug) return;
    setRegenError(null);
    try {
      const body = await authFetch<{ token: string }>(authPaths.regenerateToken(slug), { method: "POST" });
      setNewToken(body.token);
      setConfirmingRegen(false);
    } catch (err) {
      setRegenError(err instanceof Error ? err.message : "Could not regenerate the token.");
    }
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-black p-3 font-mono text-xs text-flaky">
        Could not load this project: {loadError}
      </div>
    );
  }
  if (!project) {
    return <div className="min-h-screen bg-black p-3 font-mono text-xs text-neutral-500">loading</div>;
  }

  return (
    <div className="min-h-screen bg-black font-mono text-xs text-neutral-100">
      <header className="flex items-center justify-between border-b border-neutral-800 bg-panel px-3 py-2">
        <Link to="/projects" className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
          ← my projects
        </Link>
        <Link to={`/p/${project.slug}`} className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
          view dashboard →
        </Link>
      </header>

      <div className="mx-auto max-w-md p-4">
        <h1 className="mb-1 text-neutral-100">{project.name}</h1>
        <p className="mb-4 text-neutral-600">{project.slug} · slug can't be changed</p>

        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-neutral-500">repo</span>
            <input
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              className="border border-neutral-800 bg-black px-2 py-1.5 outline-none focus:border-flaky"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-neutral-500">default branch</span>
            <input
              value={defaultBranch}
              onChange={(e) => setDefaultBranch(e.target.value)}
              className="border border-neutral-800 bg-black px-2 py-1.5 outline-none focus:border-flaky"
            />
          </label>
          <label className="flex items-center gap-2 text-neutral-400">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="accent-flaky"
            />
            Public dashboard (viewable without logging in)
          </label>
          {saveError && <p className="text-flaky">{saveError}</p>}
          <button
            type="button"
            onClick={() => void onSave()}
            disabled={busy}
            className="border border-flaky/60 bg-flaky/10 py-1.5 text-flaky outline-none hover:bg-flaky/20 focus-visible:bg-flaky/20 disabled:opacity-50"
          >
            {busy ? "saving…" : saved ? "saved" : "save changes"}
          </button>
        </div>
        
                <div className="mt-8 border-t border-neutral-800 pt-4">
          <h2 className="text-neutral-500">Status badge</h2>
          {project.is_public ? (
            <>
              <p className="mt-1 text-neutral-600">Paste this into your repo's README:</p>
              <pre className="mt-1 overflow-x-auto border border-neutral-800 bg-black p-2 text-[11px] leading-5 text-neutral-300">
                {`[![flaky tests](${badgeUrl(API_BASE, project.slug)})](${window.location.origin}/p/${project.slug})`}
              </pre>
            </>
          ) : (
            <p className="mt-1 text-neutral-600">Make this project public to get an embeddable badge.</p>
          )}
        </div>

        <div className="mt-8 border-t border-neutral-800 pt-4">
          <h2 className="text-neutral-500">CI upload token</h2>
          <p className="mt-1 text-neutral-600">
            Regenerating breaks any CI job still using the old token, until you update its secret.
          </p>

          {newToken ? (
            <div className="mt-3">
              <TokenReveal slug={project.slug} token={newToken} />
            </div>
          ) : confirmingRegen ? (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-flaky">Really regenerate? This can't be undone.</span>
              <button
                type="button"
                onClick={() => void onRegenerate()}
                className="border border-flaky/60 px-2 py-1 text-flaky outline-none hover:bg-flaky/10"
              >
                yes, regenerate
              </button>
              <button
                type="button"
                onClick={() => setConfirmingRegen(false)}
                className="border border-neutral-800 px-2 py-1 text-neutral-500 outline-none hover:text-neutral-200"
              >
                cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingRegen(true)}
              className="mt-3 border border-neutral-700 px-3 py-1.5 text-neutral-300 outline-none hover:border-flaky hover:text-flaky focus-visible:border-flaky"
            >
              regenerate token
            </button>
          )}
          {regenError && <p className="mt-2 text-flaky">{regenError}</p>}
        </div>
      </div>
    </div>
  );
}