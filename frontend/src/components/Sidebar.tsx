import { NavLink, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth";

export default function Sidebar() {
  const { slug } = useParams<{ slug: string }>();
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const items = [
    { to: `/p/${slug}`, label: "Overview", end: true },
    { to: `/p/${slug}/tests`, label: "Tests" },
    { to: `/p/${slug}/errors`, label: "Errors" },
  ];

  return (
    <nav
      aria-label="Sections"
      className="flex shrink-0 flex-col border-b border-neutral-800 bg-panel lg:h-full lg:w-40 lg:border-r lg:border-b-0"
    >
      <div className="flex flex-row overflow-x-auto lg:flex-col lg:overflow-visible">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }: { isActive: boolean }) =>
              `whitespace-nowrap border-b-2 px-3 py-2 outline-none lg:border-b-0 lg:border-l-2 lg:px-4 ${
                isActive
                  ? "border-flaky text-flaky"
                  : "border-transparent text-neutral-500 hover:text-neutral-200 focus-visible:text-neutral-200"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
      {isAuthenticated && (
        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="whitespace-nowrap border-t border-neutral-800 px-3 py-2 text-left text-neutral-600 outline-none hover:text-flaky focus-visible:text-flaky lg:mt-auto lg:px-4"
        >
          log out
        </button>
      )}
    </nav>
  );
}