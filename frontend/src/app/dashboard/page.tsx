"use client";

import { useRouter } from "next/navigation";
import { Sidebar, Icon, DashboardHeader } from "../../components";
import CameraStreamGridEnhanced from "../../components/CameraStreamGridEnhanced";
import { useAuth } from "../../contexts/AuthContext";
import { useState, useEffect } from "react";

// Pharmacy Chain AI Security Data - Scalable for 100+ locations
const aiAnalysisData = {
  // Core Security Metrics
  activePeople: 156,
  recognizedEmployees: 89,
  unknownVisitors: 67,
  securityScore: 94,

  // System Intelligence
  aiModelsActive: 6,
  processingSpeed: 8.2,
  accuracyRate: 96.3,

  // Pharmacy-specific metrics
  totalLocations: 127,
  activeCameras: 98,
  offlineCameras: 2,

  // Today's Activity
  todayStats: {
    totalCustomers: 2847,
    peakHour: "14:30",
    avgVisitTime: "12m 45s",
    securityIncidents: 0,
    highValueTransactions: 34,
  },

  // Recent Events across all locations
  recentEvents: [
    {
      time: "15:42",
      type: "high_value_alert",
      person: "Customer #2847",
      location: "Downtown Branch #12",
      action: "monitoring",
      mood: "�",
      priority: "medium",
    },
    {
      time: "15:38",
      type: "employee_shift",
      person: "Dr. Sarah Martinez",
      location: "Main Street #03",
      action: "clock_in",
      mood: "�‍⚕️",
      priority: "low",
    },
    {
      time: "15:35",
      type: "delivery_arrival",
      person: "MedSupply Delivery",
      location: "Westside #07",
      action: "authorized",
      mood: "�",
      priority: "normal",
    },
    {
      time: "15:32",
      type: "prescription_pickup",
      person: "Regular Customer",
      location: "Central Plaza #01",
      action: "completed",
      mood: "✅",
      priority: "low",
    },
    {
      time: "15:28",
      type: "security_check",
      person: "Night Supervisor",
      location: "East End #15",
      action: "routine_patrol",
      mood: "�",
      priority: "low",
    },
  ],

  // Regional camera status summary
  regions: [
    {
      name: "Downtown District",
      locations: 23,
      online: 22,
      offline: 1,
      status: "good",
      alerts: 0,
    },
    {
      name: "Suburban Area",
      locations: 31,
      online: 31,
      offline: 0,
      status: "excellent",
      alerts: 0,
    },
    {
      name: "Medical Center Zone",
      locations: 18,
      online: 18,
      offline: 0,
      status: "excellent",
      alerts: 0,
    },
    {
      name: "Shopping Centers",
      locations: 28,
      online: 27,
      offline: 1,
      status: "good",
      alerts: 1,
    },
    {
      name: "Rural Locations",
      locations: 27,
      online: 27,
      offline: 0,
      status: "excellent",
      alerts: 0,
    },
  ],

  // Smart Insights for pharmacy operations
  insights: [
    {
      type: "trend",
      text: "Customer traffic up 23% compared to last week",
      confidence: 94,
    },
    {
      type: "security",
      text: "All high-value medication areas secured",
      confidence: 100,
    },
    {
      type: "efficiency",
      text: "Average prescription wait time reduced by 8%",
      confidence: 91,
    },
    {
      type: "maintenance",
      text: "2 cameras offline - maintenance scheduled",
      confidence: 85,
    },
    {
      type: "compliance",
      text: "All DEA compliance checks passed today",
      confidence: 98,
    },
  ],

  // Top performing locations
  topLocations: [
    {
      name: "Central Plaza #01",
      customers: 289,
      efficiency: 98,
      security: 100,
    },
    {
      name: "Medical Center #04",
      customers: 267,
      efficiency: 96,
      security: 98,
    },
    { name: "Downtown Main #12", customers: 245, efficiency: 94, security: 97 },
    {
      name: "Westside Plaza #07",
      customers: 223,
      efficiency: 95,
      security: 99,
    },
  ],
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [currentTime, setCurrentTime] = useState(new Date());
  const [liveStats, setLiveStats] = useState(aiAnalysisData);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
      // Simulate live data updates for pharmacy chain
      setLiveStats((prev) => ({
        ...prev,
        activePeople: prev.activePeople + Math.floor(Math.random() * 10 - 5),
        securityScore: 92 + Math.random() * 8,
        processingSpeed: 6 + Math.random() * 6,
        todayStats: {
          ...prev.todayStats,
          totalCustomers:
            prev.todayStats.totalCustomers + Math.floor(Math.random() * 3),
        },
      }));
    }, 5000);

    return () => clearInterval(timer);
  }, []);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-100 font-sans antialiased">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/3 rounded-full blur-3xl animate-pulse"></div>
      </div>

      {/* Neural Network Pattern Overlay */}
      <div className="fixed inset-0 opacity-10 pointer-events-none">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern
              id="neural-pattern"
              x="0"
              y="0"
              width="100"
              height="100"
              patternUnits="userSpaceOnUse"
            >
              <circle
                cx="50"
                cy="50"
                r="1.5"
                fill="currentColor"
                className="text-blue-400"
              >
                <animate
                  attributeName="r"
                  values="1;2;1"
                  dur="4s"
                  repeatCount="indefinite"
                />
              </circle>
              <line
                x1="50"
                y1="50"
                x2="100"
                y2="25"
                stroke="currentColor"
                strokeWidth="0.3"
                className="text-blue-400/40"
              />
              <line
                x1="50"
                y1="50"
                x2="100"
                y2="75"
                stroke="currentColor"
                strokeWidth="0.3"
                className="text-blue-400/40"
              />
              <line
                x1="50"
                y1="50"
                x2="0"
                y2="25"
                stroke="currentColor"
                strokeWidth="0.3"
                className="text-blue-400/40"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#neural-pattern)" />
        </svg>
      </div>

      {/* Sidebar */}
      <Sidebar activeItem="dashboard" />

      {/* Main Content */}
      <div className="ml-14 flex flex-col min-h-screen relative z-10">
        {/* Header */}
        <DashboardHeader
          title="AI Security Intelligence Center"
          showSearch={true}
          showAlerts={true}
          showSecurityStatus={true}
        />

        {/* Content Area */}
        <main className="flex-1 p-4 overflow-auto">
          <div className="max-w-6xl mx-auto space-y-4">
            {/* Pharmacy Chain Header */}
            <section className="bg-white/80 backdrop-blur-xl rounded-3xl p-6 shadow-sm border border-gray-100/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center">
                    <span className="text-xl">🏥</span>
                  </div>
                  <div>
                    <h1 className="text-2xl font-semibold text-gray-900">
                      Pharmacy Chain Security
                    </h1>
                    <p className="text-gray-500 text-sm">
                      {liveStats.totalLocations} locations •{" "}
                      {liveStats.activeCameras} cameras online
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-gray-900">
                    {liveStats.securityScore}%
                  </div>
                  <div className="text-sm text-gray-500">Security Score</div>
                </div>
              </div>
            </section>
            {/* Key Metrics - Pharmacy Focused */}
            <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
                    <span className="text-xl">👥</span>
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-gray-900">
                      {liveStats.activePeople}
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">
                      Active Customers
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center">
                    <span className="text-xl">📹</span>
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-gray-900">
                      {liveStats.activeCameras}
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">
                      Cameras Online
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center">
                    <span className="text-xl">⚠️</span>
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-gray-900">
                      {liveStats.offlineCameras}
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">
                      Offline Cameras
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-purple-50 rounded-xl flex items-center justify-center">
                    <span className="text-xl">⚡</span>
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-gray-900">
                      {liveStats.processingSpeed.toFixed(1)}ms
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">
                      AI Response
                    </p>
                  </div>
                </div>
              </div>
            </section>
            {/* Regional Overview */}
            <section className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">
                  Regional Network Status
                </h3>
                <button className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors">
                  View Map
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
                {liveStats.regions.map((region, index) => (
                  <div
                    key={index}
                    className="p-3 border border-gray-200 rounded-xl hover:bg-gray-50/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-gray-900">
                        {region.name}
                      </h4>
                      <div
                        className={`w-2 h-2 rounded-full ${
                          region.status === "excellent"
                            ? "bg-green-500"
                            : region.status === "good"
                            ? "bg-blue-500"
                            : "bg-yellow-500"
                        }`}
                      ></div>
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Locations:</span>
                        <span className="font-medium">{region.locations}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Online:</span>
                        <span className="font-medium text-green-600">
                          {region.online}
                        </span>
                      </div>
                      {region.offline > 0 && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Offline:</span>
                          <span className="font-medium text-red-600">
                            {region.offline}
                          </span>
                        </div>
                      )}
                      {region.alerts > 0 && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Alerts:</span>
                          <span className="font-medium text-orange-600">
                            {region.alerts}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>{" "}
            {/* Camera System Overview */}
            <section className="bg-white/80 backdrop-blur-xl rounded-2xl p-6 shadow-sm border border-gray-100/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center">
                    <span className="text-xl">📹</span>
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                      <span className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></span>
                      Camera Network Overview
                    </h2>
                    <p className="text-gray-500 text-sm">
                      100+ cameras monitoring all pharmacy locations in
                      real-time
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <button
                    onClick={() => router.push("/camera-management")}
                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all transform hover:scale-105 shadow-lg"
                  >
                    Manage All Cameras
                  </button>
                </div>
              </div>

              {/* Camera Stats Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
                <div className="bg-gradient-to-br from-green-50 to-emerald-100 rounded-xl p-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                      <span className="text-white text-sm">✓</span>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-green-700">
                        {liveStats.activeCameras}
                      </p>
                      <p className="text-xs text-green-600 font-medium">
                        Cameras Online
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
                      <span className="text-white text-sm">!</span>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-red-700">
                        {liveStats.offlineCameras}
                      </p>
                      <p className="text-xs text-red-600 font-medium">
                        Cameras Offline
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                      <span className="text-white text-sm">👁</span>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-blue-700">
                        {liveStats.totalLocations}
                      </p>
                      <p className="text-xs text-blue-600 font-medium">
                        Locations Covered
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                      <span className="text-white text-sm">⚡</span>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-purple-700">
                        {liveStats.processingSpeed.toFixed(1)}ms
                      </p>
                      <p className="text-xs text-purple-600 font-medium">
                        AI Response Time
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Camera Actions */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={() => router.push("/camera-management")}
                  className="p-4 text-left border border-gray-200 rounded-xl hover:bg-gray-50/50 transition-colors group"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                      <span className="text-blue-600">🎯</span>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        View All Cameras
                      </div>
                      <div className="text-xs text-gray-500">
                        Access complete camera grid
                      </div>
                    </div>
                  </div>
                </button>

                <button className="p-4 text-left border border-gray-200 rounded-xl hover:bg-gray-50/50 transition-colors group">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center group-hover:bg-orange-200 transition-colors">
                      <span className="text-orange-600">⚠️</span>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        Alert Cameras
                      </div>
                      <div className="text-xs text-gray-500">
                        View cameras with alerts
                      </div>
                    </div>
                  </div>
                </button>

                <button className="p-4 text-left border border-gray-200 rounded-xl hover:bg-gray-50/50 transition-colors group">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center group-hover:bg-green-200 transition-colors">
                      <span className="text-green-600">📊</span>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        Camera Analytics
                      </div>
                      <div className="text-xs text-gray-500">
                        Performance & usage stats
                      </div>
                    </div>
                  </div>
                </button>
              </div>
            </section>
            {/* Three Column Layout for Analytics */}
            <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Recent Activity Across Chain */}
              <div className="bg-white/80 backdrop-blur-xl rounded-2xl shadow-sm border border-gray-100/50">
                <div className="p-4 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-900 flex items-center">
                    <span className="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse"></span>
                    Chain-wide Activity
                  </h3>
                </div>
                <div className="p-4 space-y-3 max-h-64 overflow-y-auto">
                  {liveStats.recentEvents.map((event, index) => (
                    <div
                      key={index}
                      className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50/50 transition-colors"
                    >
                      <span className="text-lg">{event.mood}</span>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-900">
                            {event.person}
                          </p>
                          <span className="text-xs text-gray-400">
                            {event.time}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500">
                          {event.location}
                        </p>
                        <p className="text-xs text-blue-600">{event.action}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Smart Pharmacy Insights */}
              <div className="bg-white/80 backdrop-blur-xl rounded-2xl shadow-sm border border-gray-100/50">
                <div className="p-4 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-900">AI Insights</h3>
                </div>
                <div className="p-4 space-y-3">
                  {liveStats.insights.map((insight, index) => (
                    <div
                      key={index}
                      className="flex items-start space-x-3 p-2 rounded-lg hover:bg-gray-50/50 transition-colors"
                    >
                      <div
                        className={`w-2 h-2 rounded-full mt-2 ${
                          insight.type === "security"
                            ? "bg-green-500"
                            : insight.type === "maintenance"
                            ? "bg-yellow-500"
                            : insight.type === "compliance"
                            ? "bg-purple-500"
                            : insight.type === "trend"
                            ? "bg-blue-500"
                            : "bg-gray-500"
                        }`}
                      ></div>
                      <div className="flex-1">
                        <p className="text-sm text-gray-900">{insight.text}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {insight.confidence}% confidence
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Performing Locations */}
              <div className="bg-white/80 backdrop-blur-xl rounded-2xl shadow-sm border border-gray-100/50">
                <div className="p-4 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-900">Top Locations</h3>
                </div>
                <div className="p-4 space-y-3">
                  {liveStats.topLocations.map((location, index) => (
                    <div
                      key={index}
                      className="p-2 rounded-lg hover:bg-gray-50/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-sm font-medium text-gray-900">
                          {location.name}
                        </h4>
                        <span className="text-xs text-gray-500">
                          #{index + 1}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="text-center">
                          <div className="font-semibold text-blue-600">
                            {location.customers}
                          </div>
                          <div className="text-gray-500">Customers</div>
                        </div>
                        <div className="text-center">
                          <div className="font-semibold text-green-600">
                            {location.efficiency}%
                          </div>
                          <div className="text-gray-500">Efficiency</div>
                        </div>
                        <div className="text-center">
                          <div className="font-semibold text-purple-600">
                            {location.security}%
                          </div>
                          <div className="text-gray-500">Security</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
            {/* Today's Chain Performance */}
            <section className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
              <h3 className="font-semibold text-gray-900 mb-4">
                Today's Chain Performance
              </h3>
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {liveStats.todayStats.totalCustomers.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500">Total Customers</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {liveStats.todayStats.peakHour}
                  </div>
                  <div className="text-xs text-gray-500">Peak Hour</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {liveStats.todayStats.avgVisitTime}
                  </div>
                  <div className="text-xs text-gray-500">Avg Visit Time</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {liveStats.todayStats.highValueTransactions}
                  </div>
                  <div className="text-xs text-gray-500">High-Value RX</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {liveStats.todayStats.securityIncidents}
                  </div>
                  <div className="text-xs text-gray-500">
                    Security Incidents
                  </div>
                </div>
              </div>
            </section>
            {/* Quick Actions */}
            <section className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
              <h3 className="font-semibold text-gray-900 mb-4">
                Quick Actions
              </h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <button
                  onClick={() => router.push("/camera-management")}
                  className="p-3 text-left border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  <div className="text-sm font-medium text-gray-900">
                    Camera Management
                  </div>
                  <div className="text-xs text-gray-500">
                    Manage all 100+ cameras
                  </div>
                </button>
                <button className="p-3 text-left border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                  <div className="text-sm font-medium text-gray-900">
                    Incident Reports
                  </div>
                  <div className="text-xs text-gray-500">
                    View security incidents
                  </div>
                </button>
                <button className="p-3 text-left border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                  <div className="text-sm font-medium text-gray-900">
                    Compliance Dashboard
                  </div>
                  <div className="text-xs text-gray-500">
                    DEA & regulatory checks
                  </div>
                </button>
                <button className="p-3 text-left border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                  <div className="text-sm font-medium text-gray-900">
                    Analytics Reports
                  </div>
                  <div className="text-xs text-gray-500">
                    Generate chain reports
                  </div>
                </button>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
