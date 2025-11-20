import { Link, useLocation } from "wouter";
import { User, Sparkles, BookOpen } from "lucide-react";

export const BottomNav = () => {
  const [location] = useLocation();

  const tabs = [
    { path: "/profile", icon: User, label: "Profile" },
    { path: "/generate", icon: Sparkles, label: "Generate" },
    { path: "/cookbook", icon: BookOpen, label: "CookBook" },
  ];

  return (
    <nav className="floating-nav z-50">
      <div className="flex items-center justify-around px-2 py-3">
        {tabs.map((tab) => {
          const isActive = location === tab.path;
          const Icon = tab.icon;

          return (
            <Link
              key={tab.path}
              href={tab.path}
              className={`flex flex-col items-center gap-1 px-6 py-2 rounded-2xl transition-all duration-300 ${
                isActive
                  ? "bg-primary text-primary-foreground scale-110"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon size={isActive ? 24 : 20} className="transition-all" />
              <span
                className={`text-xs font-medium ${
                  isActive ? "font-semibold" : ""
                }`}
              >
                {tab.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
};
