import { UserRole } from "./types";

export interface MenuSection {
  id: string;
  title: string;
  items: MenuItemConfig[];
}

export interface MenuItemConfig {
  id: string;
  label: string;
  href: string;
  icon: string; // lucide-react icon name
  roles: UserRole[]; // which roles can see this item
  badge?: () => Promise<number>; // optional dynamic badge count
}

/**
 * Extensible menu configuration.
 * To add new features, just add a new section or item here.
 * Each item specifies which roles can access it.
 */
export const menuSections: MenuSection[] = [
  {
    id: "tidrapportering",
    title: "Tidrapportering",
    items: [
      {
        id: "rapportera",
        label: "Rapportera tid",
        href: "/dashboard",
        icon: "Clock",
        roles: ["worker", "admin"],
      },
      {
        id: "vecka",
        label: "Veckoöversikt",
        href: "/week",
        icon: "CalendarDays",
        roles: ["worker", "admin"],
      },
    ],
  },
  {
    id: "admin",
    title: "Administration",
    items: [
      {
        id: "oversikt",
        label: "Översikt",
        href: "/admin",
        icon: "LayoutDashboard",
        roles: ["admin"],
      },
      {
        id: "personal",
        label: "Personal",
        href: "/admin/users",
        icon: "Users",
        roles: ["admin"],
      },
      {
        id: "projekt",
        label: "Projekt",
        href: "/admin/projects",
        icon: "FolderOpen",
        roles: ["admin"],
      },
    ],
  },
  // --- Add new sections here ---
  // Example: Material tracking, Customer portal, etc.
  // {
  //   id: "material",
  //   title: "Material",
  //   items: [
  //     {
  //       id: "lager",
  //       label: "Lagersaldo",
  //       href: "/material",
  //       icon: "Package",
  //       roles: ["worker", "admin"],
  //     },
  //   ],
  // },
];

/**
 * Get menu sections filtered by user role
 */
export function getMenuForRole(role: UserRole): MenuSection[] {
  return menuSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => item.roles.includes(role)),
    }))
    .filter((section) => section.items.length > 0);
}
