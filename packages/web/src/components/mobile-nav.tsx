"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { List, X } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { CadenceLogo } from "./logo";
import {
  DashboardIcon,
  GenerateIcon,
  ProfileIcon,
  SettingsIcon,
} from "./icons";

const navItems = [
  { href: "/", label: "Dashboard", icon: DashboardIcon },
  { href: "/generate", label: "Generate", icon: GenerateIcon },
  { href: "/profiles", label: "Profiles", icon: ProfileIcon },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      <header className="fixed left-0 right-0 top-0 z-40 flex h-16 items-center gap-3 border-b border-border bg-sidebar px-4 lg:hidden">
        <button
          onClick={() => setOpen(!open)}
          className="flex h-10 w-10 items-center justify-center rounded-xl transition-colors hover:bg-muted"
          aria-label="Toggle menu"
        >
          {open ? (
            <X className="h-5 w-5" weight="bold" />
          ) : (
            <List className="h-5 w-5" weight="bold" />
          )}
        </button>

        <Link href="/" className="flex items-center gap-2.5">
          <CadenceLogo className="h-8 w-8" />
          <span className="text-base font-bold tracking-tight text-foreground">
            Cadence
          </span>
        </Link>
      </header>

      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/30 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <nav
        className={cn(
          "fixed left-0 top-16 z-40 h-[calc(100vh-64px)] w-72 transform border-r border-border bg-sidebar p-5 transition-transform duration-300 ease-out lg:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="space-y-1.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-4 py-3.5 text-sm font-semibold",
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
        </div>
      </nav>
    </>
  );
}
