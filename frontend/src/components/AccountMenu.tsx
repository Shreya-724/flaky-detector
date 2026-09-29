import { Link } from "react-router-dom";
import { useAuth } from "../auth";

/** Rendered in the header. Just identity/entry point — the "log out" action
 * itself lives in the sidebar, see Sidebar.tsx. */
export default function AccountMenu() {
  const { isAuthenticated, username } = useAuth();

  if (!isAuthenticated) {
    return (
      <Link to="/login" className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
        log in
      </Link>
    );
  }

  return (
    <Link to="/projects" className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
      {username}
    </Link>
  );
}