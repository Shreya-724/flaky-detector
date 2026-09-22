import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex flex-1 flex-col items-start gap-2 p-4 text-neutral-500">
      <p>
        <span className="text-flaky">404</span> — nothing here.
      </p>
      <Link to="/" className="text-neutral-300 underline outline-none hover:text-flaky focus-visible:text-flaky">
        back to overview
      </Link>
    </div>
  );
}