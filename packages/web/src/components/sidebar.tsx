"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  DashboardIcon,
  GenerateIcon,
  ProfileIcon,
} from "./icons";
import { CadenceLogo } from "./logo";

const navItems = [
  { href: "/", label: "Dashboard", icon: DashboardIcon },
  { href: "/generate", label: "Generate", icon: GenerateIcon },
  { href: "/profiles", label: "Profiles", icon: ProfileIcon },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 flex h-screen w-60 flex-col border-r border-border bg-sidebar px-4 py-6">
      <div className="mb-10 px-3">
        <Link href="/" className="flex items-center gap-3">
          <CadenceLogo className="h-9 w-9" />
          <span className="text-lg font-bold tracking-tight text-foreground">
            Cadence
          </span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1.5">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold",
                isActive
                  ? "bg-primary text-white"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon
                className="h-[18px] w-[18px]"
                weight={isActive ? "fill" : "regular"}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
