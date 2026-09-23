import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function AccountMenu() {
  const { isAuthenticated, username, logout } = useAuth();
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return (
      <Link to="/login" className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
        log in
      </Link>
    );
  }

  return (
    <span className="flex items-center gap-3">
      <Link to="/projects" className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
        {username}
      </Link>
      <button
        type="button"
        onClick={() => {
          logout();
          navigate("/login");
        }}
        className="text-neutral-500 outline-none hover:text-flaky focus-visible:text-flaky"
      >
        log out
      </button>
    </span>
  );
}