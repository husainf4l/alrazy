"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Icon from "./Icon";

interface MenuItem {
  id: string;
  icon: string;
  label: string;
  badge: string | null;
  path: string;
}

interface SidebarProps {
  activeItem: string;
  onItemClick?: (itemId: string) => void; // Make optional for backward compatibility
}

const Sidebar = ({ activeItem, onItemClick }: SidebarProps) => {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const router = useRouter();

  const menuItems: MenuItem[] = [
    {
      id: "dashboard",
      icon: "dashboard",
      label: "Security Dashboard",
      badge: null,
      path: "/dashboard",
    },
    {
      id: "cameras",
      icon: "camera",
      label: "Cameras",
      badge: "4",
      path: "/dashboard/cameras",
    },
    {
      id: "analytics",
      icon: "analytics",
      label: "Threat Analytics",
      badge: null,
      path: "/dashboard/analytics",
    },
    {
      id: "users",
      icon: "users",
      label: "User Access",
      badge: "12",
      path: "/users",
    },
    {
      id: "projects",
      icon: "projects",
      label: "Security Policies",
      badge: "3",
      path: "/dashboard/projects",
    },
    {
      id: "messages",
      icon: "messages",
      label: "Security Alerts",
      badge: "5",
      path: "/dashboard/messages",
    },
    {
      id: "calendar",
      icon: "calendar",
      label: "Incident Timeline",
      badge: null,
      path: "/dashboard/calendar",
    },
    {
      id: "settings",
      icon: "settings",
      label: "Security Settings",
      badge: null,
      path: "/dashboard/settings",
    },
  ];

  const handleItemClick = (item: MenuItem) => {
    // Use Next.js routing for navigation
    router.push(item.path);

    // Call the optional callback for backward compatibility
    if (onItemClick) {
      onItemClick(item.id);
    }
  };

  return (
    <div className="w-14 bg-white/95 backdrop-blur-xl shadow-2xl border-r border-gray-200/50 flex flex-col fixed left-0 top-0 h-screen z-40">
      {/* Content */}
      <div className="flex flex-col h-full">
        {/* Logo */}{" "}
        <div className="h-16 flex items-center justify-center border-b border-gray-100/50">
          <div className="w-8 h-8 bg-gradient-to-br from-red-500 via-orange-500 to-yellow-500 rounded-xl flex items-center justify-center shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105">
            <div className="w-4 h-4 bg-white rounded-md opacity-95 shadow-sm"></div>
          </div>
        </div>
        {/* Menu Items */}
        <nav className="flex-1 py-5">
          <div className="space-y-2">
            {menuItems.slice(0, -1).map((item) => (
              <div
                key={item.id}
                className="relative group"
                onMouseEnter={() => setHoveredItem(item.id)}
                onMouseLeave={() => setHoveredItem(null)}
              >
                <button
                  onClick={() => handleItemClick(item)}
                  className={`relative flex items-center justify-center w-10 h-10 mx-auto rounded-xl transition-all duration-300 transform hover:scale-105 ${
                    activeItem === item.id
                      ? "bg-gradient-to-br from-red-50 to-orange-50 text-red-600 shadow-lg shadow-red-100/50 scale-105"
                      : "text-gray-500 hover:bg-gray-50 hover:text-gray-700 hover:shadow-md"
                  }`}
                >
                  <Icon
                    name={item.icon}
                    className={`transition-all duration-300 ${
                      activeItem === item.id ? "w-5 h-5" : "w-4 h-4"
                    }`}
                  />{" "}
                  {/* Active indicator */}
                  {activeItem === item.id && (
                    <div className="absolute -right-3 top-1/2 transform -translate-y-1/2 w-0.5 h-6 bg-gradient-to-b from-red-500 to-orange-600 rounded-full shadow-lg"></div>
                  )}
                  {/* Badge */}
                  {item.badge && (
                    <div className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-xs font-medium rounded-full flex items-center justify-center shadow-lg">
                      {item.badge}
                    </div>
                  )}
                </button>

                {/* Tooltip */}
                {hoveredItem === item.id && (
                  <div className="absolute left-full top-1/2 transform -translate-y-1/2 ml-4 px-2 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-md shadow-xl opacity-0 animate-fade-in pointer-events-none whitespace-nowrap z-[60]">
                    {item.label}
                    <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1 w-1.5 h-1.5 bg-gray-900 rotate-45"></div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </nav>
        {/* Divider */}
        <div className="mx-4 mb-4">
          <div className="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent"></div>
        </div>
        {/* Bottom Settings */}
        <div className="pb-5">
          <div
            className="relative group"
            onMouseEnter={() => setHoveredItem("settings")}
            onMouseLeave={() => setHoveredItem(null)}
          >
            <button
              onClick={() =>
                handleItemClick(
                  menuItems.find((item) => item.id === "settings")!
                )
              }
              className={`relative flex items-center justify-center w-10 h-10 mx-auto rounded-xl transition-all duration-300 transform hover:scale-105 ${
                activeItem === "settings"
                  ? "bg-gradient-to-br from-red-50 to-orange-50 text-red-600 shadow-lg shadow-red-100/50 scale-105"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-700 hover:shadow-md"
              }`}
            >
              <Icon
                name="settings"
                className={`transition-all duration-300 ${
                  activeItem === "settings"
                    ? "w-5 h-5 animate-spin-slow"
                    : "w-4 h-4"
                }`}
              />

              {/* Active indicator */}
              {activeItem === "settings" && (
                <div className="absolute -right-3 top-1/2 transform -translate-y-1/2 w-0.5 h-6 bg-gradient-to-b from-red-500 to-orange-600 rounded-full shadow-lg"></div>
              )}
            </button>

            {/* Tooltip */}
            {hoveredItem === "settings" && (
              <div className="absolute left-full top-1/2 transform -translate-y-1/2 ml-4 px-2 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-md shadow-xl opacity-0 animate-fade-in pointer-events-none whitespace-nowrap z-[60]">
                Settings
                <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1 w-1.5 h-1.5 bg-gray-900 rotate-45"></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
