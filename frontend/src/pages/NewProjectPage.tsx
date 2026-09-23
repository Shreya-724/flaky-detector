import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { authPaths, type CreateProjectResponse } from "../api";
import { useAuth } from "../auth";
import TokenReveal from "../components/TokenReveal";

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
}

export default function NewProjectPage() {
  const { authFetch } = useAuth();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [repo, setRepo] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("main");
  const [isPublic, setIsPublic] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<CreateProjectResponse | null>(null);

  function onNameChange(value: string) {
    setName(value);
    if (!slugTouched) setSlug(slugify(value));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const body = await authFetch<CreateProjectResponse>(authPaths.myProjects, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          slug,
          repo,
          default_branch: defaultBranch,
          is_public: isPublic,
        }),
      });
      setCreated(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the project.");
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <div className="min-h-screen bg-black p-3 font-mono text-xs text-neutral-100">
        <TokenReveal slug={created.project.slug} token={created.token} />
        <div className="mt-4 flex gap-3">
          <Link
            to={`/p/${created.project.slug}`}
            className="border border-neutral-700 px-3 py-1.5 text-neutral-300 outline-none hover:border-flaky hover:text-flaky focus-visible:border-flaky"
          >
            view dashboard
          </Link>
          <Link to="/projects" className="border border-neutral-800 px-3 py-1.5 text-neutral-500 outline-none hover:text-neutral-200">
            back to projects
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center bg-black px-4 py-10 font-mono text-xs text-neutral-100">
      <div className="w-full max-w-md border border-neutral-800 bg-panel p-4">
        <h1 className="mb-4 text-neutral-100">New project</h1>
        <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-neutral-500">name</span>
            <input
              value={name}
              onChange={(e) => onNameChange(e.target.value)}
              placeholder="My App"
              required
              className="border border-neutral-800 bg-black px-2 py-1.5 outline-none focus:border-flaky"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-neutral-500">slug (used in URLs, can't be changed later)</span>
            <input
              value={slug}
              onChange={(e) => {
                setSlugTouched(true);
                setSlug(slugify(e.target.value));
              }}
              placeholder="my-app"
              pattern="[a-z0-9]+(-[a-z0-9]+)*"
              required
              className="border border-neutral-800 bg-black px-2 py-1.5 outline-none focus:border-flaky"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-neutral-500">repo (optional)</span>
            <input
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="you/my-app"
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
          {error && <p className="text-flaky">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="mt-1 border border-flaky/60 bg-flaky/10 py-1.5 text-flaky outline-none hover:bg-flaky/20 focus-visible:bg-flaky/20 disabled:opacity-50"
          >
            {busy ? "creating…" : "create project"}
          </button>
        </form>
      </div>
    </div>
  );
}