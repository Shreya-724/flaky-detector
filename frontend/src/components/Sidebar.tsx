import { NavLink } from "react-router-dom";

const ITEMS: { to: string; label: string; end?: boolean }[] = [
  { to: "/", label: "Overview", end: true },
  { to: "/tests", label: "Tests" },
  { to: "/errors", label: "Errors" },
];

export default function Sidebar() {
  return (
    <nav
      aria-label="Sections"
      className="flex shrink-0 flex-row overflow-x-auto border-b border-neutral-800 bg-panel lg:w-40 lg:flex-col lg:overflow-visible lg:border-r lg:border-b-0"
    >
      {ITEMS.map((item) => (
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
    </nav>
  );
}