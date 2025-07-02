"use client";

import { useRouter } from "next/navigation";
import { Sidebar, DashboardHeader } from "../../components";
import { useAuth } from "../../contexts/AuthContext";
import { useState, useEffect } from "react";

export default function CameraManagement() {
  const { user } = useAuth();
  const router = useRouter();
  const [currentTime, setCurrentTime] = useState(new Date());
  const [selectedCamera, setSelectedCamera] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [viewMode, setViewMode] = useState("grid"); // grid, list, alerts

  // Clean, professional camera data without emojis
  const allCameras = [
    {
      id: "CAM-001",
      name: "Downtown Main",
      location: "Main Entrance",
      status: "critical",
      fps: 30,
      quality: "4K",
      region: "Downtown District",
      lastEvent: "Motion detected",
      eventTime: "2 min ago",
      confidence: 94,
    },
    {
      id: "CAM-002", 
      name: "Medical Center",
      location: "Pharmacy Counter",
      status: "normal",
      fps: 30,
      quality: "HD",
      region: "Medical Center",
      lastEvent: "Normal operations",
      eventTime: "Active",
      confidence: 98,
    },
    {
      id: "CAM-003",
      name: "Parking Area",
      location: "Customer Parking",
      status: "normal", 
      fps: 25,
      quality: "HD",
      region: "Suburban",
      lastEvent: "Vehicle detected",
      eventTime: "5 min ago",
      confidence: 91,
    },
    {
      id: "CAM-004",
      name: "Loading Dock",
      location: "Delivery Area",
      status: "warning",
      fps: 18,
      quality: "720p",
      region: "Industrial",
      lastEvent: "Equipment maintenance",
      eventTime: "30 min ago",
      confidence: 76,
    },
    {
      id: "CAM-005",
      name: "Central Plaza",
      location: "Main Entrance",
      status: "normal",
      fps: 30,
      quality: "4K",
      region: "Downtown District",
      lastEvent: "Normal operations",
      eventTime: "Active",
      confidence: 97,
    },
    ...Array.from({ length: 95 }, (_, i) => {
      const camNum = 6 + i;
      const regions = ["Downtown District", "Suburban", "Medical Center", "Industrial", "University Zone"];
      const locations = ["Main Entrance", "Parking Area", "Counter", "Office", "Storage", "Exit"];
      const statuses = ["normal", "normal", "normal", "normal", "warning"];
      const qualities = ["4K", "HD", "HD", "720p"];
      
      return {
        id: `CAM-${String(camNum).padStart(3, "0")}`,
        name: `Camera ${camNum}`,
        location: locations[i % locations.length],
        status: statuses[i % statuses.length],
        fps: [20, 25, 30][i % 3],
        quality: qualities[i % qualities.length],
        region: regions[i % regions.length],
        lastEvent: "Normal operations",
        eventTime: "Active",
        confidence: 85 + Math.floor(Math.random() * 15),
      };
    }),
  ];

  const filteredCameras = allCameras.filter((camera) => {
    const matchesSearch =
      camera.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      camera.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
      camera.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter =
      filterStatus === "all" || camera.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "high-alert":
        return "bg-red-500";
      case "medium-alert":
        return "bg-orange-500";
      case "warning":
        return "bg-yellow-500";
      default:
        return "bg-green-500";
    }
  };

  const getStatusCount = (status: string) => {
    return allCameras.filter((camera) => camera.status === status).length;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-100 font-sans antialiased">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl animate-pulse"></div>
      </div>

      {/* Sidebar */}
      <Sidebar activeItem="camera-management" />

      {/* Main Content */}
      <div className="ml-14 flex flex-col min-h-screen relative z-10">
        {/* Header */}
        <DashboardHeader
          title="Camera Management Center"
          showSearch={true}
          showAlerts={true}
          showSecurityStatus={true}
        />

        {/* Content Area */}
        <main className="flex-1 p-4 overflow-auto">
          <div className="max-w-7xl mx-auto space-y-4">
            {/* AI Priority Alerts Row */}
            {allCameras.filter((camera) => camera.status !== "normal").length >
              0 && (
              <section className="bg-gradient-to-r from-red-500/10 via-orange-500/10 to-yellow-500/10 backdrop-blur-xl rounded-3xl p-6 border border-red-200/50 shadow-lg mb-4">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-600 rounded-2xl flex items-center justify-center shadow-lg animate-pulse">
                      <span className="text-2xl">🚨</span>
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
                        <span>AI Priority Alerts</span>
                        <div className="px-3 py-1 bg-red-500 text-white text-sm font-semibold rounded-full animate-bounce">
                          {
                            allCameras.filter(
                              (camera) => camera.status !== "normal"
                            ).length
                          }
                        </div>
                      </h2>
                      <p className="text-gray-600 text-sm">
                        Real-time AI-powered threat detection and anomaly
                        monitoring
                      </p>
                    </div>
                  </div>

                  {/* AI Performance Metrics */}
                  <div className="flex items-center space-x-6 bg-white/70 rounded-2xl px-6 py-3 shadow-sm">
                    <div className="text-center">
                      <div className="text-lg font-bold text-green-600">
                        98.7%
                      </div>
                      <div className="text-xs text-gray-500">AI Confidence</div>
                    </div>
                    <div className="w-px h-8 bg-gray-300"></div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-blue-600">
                        1.2s
                      </div>
                      <div className="text-xs text-gray-500">Response Time</div>
                    </div>
                    <div className="w-px h-8 bg-gray-300"></div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-purple-600">
                        99.2%
                      </div>
                      <div className="text-xs text-gray-500">
                        Detection Rate
                      </div>
                    </div>
                    <div className="w-px h-8 bg-gray-300"></div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-orange-600">
                        Active
                      </div>
                      <div className="text-xs text-gray-500">Model Status</div>
                    </div>
                  </div>
                </div>

                {/* Alert Cameras Horizontal Scroll */}
                <div className="overflow-x-auto">
                  <div className="flex space-x-4 pb-2">
                    {allCameras
                      .filter((camera) => camera.status !== "normal")
                      .map((camera, index) => (
                        <button
                          key={camera.id}
                          onClick={() =>
                            setSelectedCamera(
                              allCameras.findIndex((c) => c.id === camera.id)
                            )
                          }
                          className="flex-shrink-0 w-80 bg-white/90 backdrop-blur-sm rounded-2xl p-4 shadow-lg border border-gray-200/50 hover:shadow-xl transition-all duration-300 hover:scale-[1.02] group"
                        >
                          <div className="flex items-start space-x-4">
                            {/* Alert Camera Feed */}
                            <div
                              className={`w-24 h-16 bg-gradient-to-br ${camera.gradient} rounded-xl relative overflow-hidden shadow-md flex-shrink-0`}
                            >
                              <div className="absolute inset-0 bg-black/30"></div>
                              <div
                                className={`absolute top-1 left-1 w-2 h-2 rounded-full animate-pulse ${getStatusColor(
                                  camera.status
                                )}`}
                              ></div>
                              <div className="absolute top-1 right-1 text-white text-xs bg-black/60 px-1 py-0.5 rounded">
                                {camera.fps}fps
                              </div>
                              <div className="absolute bottom-1 left-1 text-white text-xs bg-red-500/80 px-1 py-0.5 rounded font-medium">
                                ALERT
                              </div>
                            </div>

                            {/* Alert Details */}
                            <div className="flex-1 text-left">
                              <div className="flex items-center justify-between mb-2">
                                <h3 className="font-semibold text-gray-900 text-sm">
                                  {camera.name}
                                </h3>
                                <div
                                  className={`px-2 py-1 rounded-lg text-xs font-medium ${
                                    camera.status === "high-alert"
                                      ? "bg-red-100 text-red-700"
                                      : camera.status === "medium-alert"
                                      ? "bg-orange-100 text-orange-700"
                                      : "bg-yellow-100 text-yellow-700"
                                  }`}
                                >
                                  {camera.status
                                    .replace("-", " ")
                                    .toUpperCase()}
                                </div>
                              </div>

                              <p className="text-xs text-gray-600 mb-2">
                                {camera.location} • {camera.region}
                              </p>

                              <div className="flex items-center justify-between mb-3">
                                <span className="text-sm font-medium text-gray-900">
                                  {camera.alert}
                                </span>
                              </div>

                              {/* AI Detection Tags */}
                              <div className="flex flex-wrap gap-1 mb-3">
                                {camera.status === "high-alert" && (
                                  <>
                                    <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full font-medium">
                                      Motion Detected
                                    </span>
                                    <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-full font-medium">
                                      After Hours
                                    </span>
                                    <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">
                                      High Value Area
                                    </span>
                                  </>
                                )}
                                {camera.status === "medium-alert" && (
                                  <>
                                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-full font-medium">
                                      Unusual Activity
                                    </span>
                                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                                      Controlled Access
                                    </span>
                                  </>
                                )}
                                {camera.status === "warning" && (
                                  <>
                                    <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full font-medium">
                                      Maintenance
                                    </span>
                                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-full font-medium">
                                      Low Quality
                                    </span>
                                  </>
                                )}
                              </div>

                              {/* Action Buttons */}
                              <div className="flex items-center space-x-2">
                                <button
                                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                                    camera.status === "high-alert"
                                      ? "bg-red-600 hover:bg-red-700 text-white"
                                      : camera.status === "medium-alert"
                                      ? "bg-orange-600 hover:bg-orange-700 text-white"
                                      : "bg-yellow-600 hover:bg-yellow-700 text-white"
                                  }`}
                                >
                                  View Details
                                </button>
                                <button className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium rounded-lg transition-colors">
                                  Acknowledge
                                </button>
                                {camera.status === "high-alert" && (
                                  <button className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium rounded-lg transition-colors">
                                    Dispatch
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                  </div>
                </div>

                {/* Quick Actions Bar */}
                <div className="mt-6 flex items-center justify-between bg-white/60 rounded-2xl p-4">
                  <div className="flex items-center space-x-4">
                    <button className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-xl transition-colors flex items-center space-x-2">
                      <span>🚨</span>
                      <span>Emergency Protocol</span>
                    </button>
                    <button className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-xl transition-colors flex items-center space-x-2">
                      <span>📞</span>
                      <span>Contact Security</span>
                    </button>
                    <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors flex items-center space-x-2">
                      <span>📊</span>
                      <span>Generate Report</span>
                    </button>
                  </div>
                  <div className="text-xs text-gray-500">
                    Last AI scan: {currentTime.toLocaleTimeString()} • Next scan
                    in 15s
                  </div>
                </div>
              </section>
            )}

            {/* Camera Management Header */}
            <section className="bg-white/80 backdrop-blur-xl rounded-2xl p-4 shadow-sm border border-gray-100/50">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                    <span className="text-xl">📹</span>
                  </div>
                  <div>
                    <h1 className="text-xl font-semibold text-gray-900">
                      Camera Network Management
                    </h1>
                    <p className="text-gray-500 text-sm">
                      {allCameras.length} total cameras across all locations
                    </p>
                  </div>
                </div>

                {/* Status Summary */}
                <div className="flex items-center space-x-4 text-xs">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>{getStatusCount("normal")} Normal</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                    <span>{getStatusCount("warning")} Warning</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                    <span>{getStatusCount("medium-alert")} Medium Alert</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    <span>{getStatusCount("high-alert")} High Alert</span>
                  </div>
                </div>
              </div>

              {/* Search and Filter Controls */}
              <div className="flex items-center space-x-4">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Search cameras by name, location, or ID..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full px-4 py-2 bg-white/50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2 bg-white/50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="normal">Normal</option>
                  <option value="warning">Warning</option>
                  <option value="medium-alert">Medium Alert</option>
                  <option value="high-alert">High Alert</option>
                </select>
                <div className="text-xs text-gray-500">
                  {filteredCameras.length} of {allCameras.length} cameras
                </div>
              </div>
            </section>

            {/* AI Priority Alerts Row - Super Elegant */}
            <section className="bg-gradient-to-r from-red-50 via-orange-50 to-yellow-50 border border-red-200/50 rounded-3xl p-6 shadow-lg relative overflow-hidden">
              {/* Background Pattern */}
              <div className="absolute inset-0 opacity-5">
                <div className="absolute top-4 left-4 w-32 h-32 bg-red-500 rounded-full blur-3xl"></div>
                <div className="absolute bottom-4 right-4 w-24 h-24 bg-orange-500 rounded-full blur-2xl"></div>
              </div>

              <div className="relative z-10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-600 rounded-2xl flex items-center justify-center shadow-lg">
                      <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-900 flex items-center">
                        🤖 AI Priority Alerts
                        <span className="ml-3 px-3 py-1 bg-red-500 text-white text-sm font-medium rounded-full animate-pulse">
                          {
                            allCameras.filter((cam) => cam.status !== "normal")
                              .length
                          }{" "}
                          Active
                        </span>
                      </h2>
                      <p className="text-gray-600 text-sm">
                        Real-time AI analysis detecting critical situations
                        requiring immediate attention
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <button className="px-4 py-2 bg-red-600 text-white rounded-xl text-sm font-medium hover:bg-red-700 transition-colors shadow-lg">
                      View All Alerts
                    </button>
                    <button className="px-4 py-2 bg-white/80 text-gray-700 rounded-xl text-sm font-medium hover:bg-white transition-colors border border-gray-200">
                      AI Settings
                    </button>
                  </div>
                </div>

                {/* Alert Cameras Horizontal Scroll */}
                <div
                  className="flex space-x-4 overflow-x-auto pb-2"
                  style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
                >
                  {allCameras
                    .filter((camera) => camera.status !== "normal")
                    .map((camera, index) => (
                      <button
                        key={camera.id}
                        onClick={() =>
                          setSelectedCamera(
                            allCameras.findIndex((c) => c.id === camera.id)
                          )
                        }
                        className={`group flex-shrink-0 w-80 bg-white/90 backdrop-blur-sm rounded-2xl p-4 shadow-lg border transition-all duration-300 hover:scale-105 hover:shadow-xl ${
                          selectedCamera ===
                          allCameras.findIndex((c) => c.id === camera.id)
                            ? "border-red-400 ring-2 ring-red-200 shadow-xl scale-105"
                            : "border-gray-200/50 hover:border-red-300"
                        }`}
                      >
                        {/* Alert Header */}
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-2">
                            <div
                              className={`w-3 h-3 rounded-full ${getStatusColor(
                                camera.status
                              )} animate-pulse shadow-sm`}
                            ></div>
                            <span
                              className={`text-xs font-bold px-2 py-1 rounded-lg ${
                                camera.status === "high-alert"
                                  ? "bg-red-100 text-red-700"
                                  : camera.status === "medium-alert"
                                  ? "bg-orange-100 text-orange-700"
                                  : "bg-yellow-100 text-yellow-700"
                              }`}
                            >
                              {camera.status.replace("-", " ").toUpperCase()}
                            </span>
                          </div>
                          <span className="text-xs text-gray-500 font-medium bg-gray-100 px-2 py-1 rounded">
                            {camera.id}
                          </span>
                        </div>

                        {/* Alert Camera Preview */}
                        <div
                          className={`aspect-video bg-gradient-to-br ${camera.gradient} rounded-xl relative overflow-hidden mb-3 shadow-inner`}
                        >
                          <div className="absolute inset-0 bg-black/30 group-hover:bg-black/20 transition-colors"></div>

                          {/* Critical Alert Overlay */}
                          <div
                            className={`absolute top-2 left-2 text-white text-xs px-2 py-1 rounded-lg font-medium shadow-sm ${
                              camera.alertType === "critical"
                                ? "bg-red-600/95"
                                : camera.alertType === "warning"
                                ? "bg-yellow-600/95"
                                : camera.alertType === "medium"
                                ? "bg-orange-600/95"
                                : "bg-blue-600/95"
                            }`}
                          >
                            {camera.alert}
                          </div>

                          {/* AI Confidence Score */}
                          <div className="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded-lg font-medium">
                            AI: {95 - index * 2}%
                          </div>

                          {/* Live Pulse */}
                          <div className="absolute bottom-2 left-2 flex items-center space-x-1">
                            <div className="w-2 h-2 bg-red-500 rounded-full animate-ping"></div>
                            <span className="text-white text-xs font-medium bg-black/60 px-1.5 py-0.5 rounded">
                              ALERT
                            </span>
                          </div>

                          {/* Priority Level */}
                          <div className="absolute bottom-2 right-2 flex space-x-0.5">
                            {[
                              ...Array(
                                camera.status === "high-alert"
                                  ? 5
                                  : camera.status === "medium-alert"
                                  ? 3
                                  : 2
                              ),
                            ].map((_, i) => (
                              <div
                                key={i}
                                className="w-1 h-4 bg-red-400 rounded animate-pulse"
                                style={{ animationDelay: `${i * 0.2}s` }}
                              ></div>
                            ))}
                          </div>

                          {/* Selection Highlight */}
                          {selectedCamera ===
                            allCameras.findIndex((c) => c.id === camera.id) && (
                            <div className="absolute inset-0 border-2 border-red-400 rounded-xl bg-red-400/10"></div>
                          )}
                        </div>

                        {/* Alert Details */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold text-gray-900 truncate">
                              {camera.name}
                            </h4>
                            <span className="text-xs text-gray-500">
                              {Math.floor(Math.random() * 5) + 1}m ago
                            </span>
                          </div>
                          <p className="text-xs text-gray-600">
                            {camera.location} • {camera.region}
                          </p>

                          {/* AI Analysis Tags */}
                          <div className="flex flex-wrap gap-1 mt-2">
                            {camera.status === "high-alert" && (
                              <>
                                <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                                  High Value
                                </span>
                                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                                  Person Detected
                                </span>
                              </>
                            )}
                            {camera.status === "medium-alert" && (
                              <>
                                <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-medium">
                                  Controlled Substance
                                </span>
                                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                                  Queue Alert
                                </span>
                              </>
                            )}
                            {camera.status === "warning" && (
                              <>
                                <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">
                                  Maintenance
                                </span>
                                <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full font-medium">
                                  Low Quality
                                </span>
                              </>
                            )}
                          </div>

                          {/* Action Buttons */}
                          <div className="flex space-x-2 mt-3">
                            <button
                              className={`flex-1 text-xs font-medium py-1.5 rounded-lg transition-colors ${
                                camera.status === "high-alert"
                                  ? "bg-red-600 text-white hover:bg-red-700"
                                  : camera.status === "medium-alert"
                                  ? "bg-orange-600 text-white hover:bg-orange-700"
                                  : "bg-yellow-600 text-white hover:bg-yellow-700"
                              }`}
                            >
                              Investigate
                            </button>
                            <button className="px-3 py-1.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-200 transition-colors">
                              Dismiss
                            </button>
                          </div>
                        </div>
                      </button>
                    ))}

                  {/* Add More Alerts Indicator */}
                  {allCameras.filter((cam) => cam.status !== "normal")
                    .length === 0 ? (
                    <div className="flex-shrink-0 w-80 bg-green-50 border border-green-200 rounded-2xl p-6 flex items-center justify-center">
                      <div className="text-center">
                        <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-3">
                          <svg
                            className="w-6 h-6 text-white"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        </div>
                        <h3 className="text-sm font-semibold text-green-800">
                          All Systems Normal
                        </h3>
                        <p className="text-xs text-green-600 mt-1">
                          No active alerts detected
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-shrink-0 w-20 flex items-center justify-center">
                      <button className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center hover:bg-gray-300 transition-colors">
                        <svg
                          className="w-5 h-5 text-gray-600"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>

                {/* AI Insights Footer */}
                <div className="mt-4 bg-white/60 backdrop-blur-sm rounded-xl p-3 border border-gray-200/50">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-4">
                      <span className="text-gray-600">
                        🧠 AI Confidence:{" "}
                        <strong className="text-gray-900">94.2%</strong>
                      </span>
                      <span className="text-gray-600">
                        ⚡ Response Time:{" "}
                        <strong className="text-gray-900">0.3s</strong>
                      </span>
                      <span className="text-gray-600">
                        🎯 Detection Rate:{" "}
                        <strong className="text-gray-900">99.1%</strong>
                      </span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <span className="text-gray-600">
                        AI Model:{" "}
                        <strong className="text-green-600">Active</strong>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Main Camera Display - Full Width */}
            <section className="bg-white/80 backdrop-blur-xl rounded-3xl p-6 shadow-sm border border-gray-100/50">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <div
                    className={`w-4 h-4 rounded-full animate-pulse ${getStatusColor(
                      allCameras[selectedCamera].status
                    )}`}
                  ></div>
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-900">
                      {allCameras[selectedCamera].name}
                    </h2>
                    <p className="text-gray-500 text-sm">
                      {allCameras[selectedCamera].location} •{" "}
                      {allCameras[selectedCamera].id} •{" "}
                      {allCameras[selectedCamera].region}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-right">
                    <div className="text-lg font-semibold text-gray-900">
                      {allCameras[selectedCamera].fps} FPS
                    </div>
                    <div className="text-xs text-gray-500">Frame Rate</div>
                  </div>
                  <div className="text-right">
                    <div
                      className={`text-lg font-semibold ${
                        allCameras[selectedCamera].quality === "HD"
                          ? "text-green-600"
                          : "text-yellow-600"
                      }`}
                    >
                      {allCameras[selectedCamera].quality}
                    </div>
                    <div className="text-xs text-gray-500">Quality</div>
                  </div>
                  <button className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
                    Full Screen
                  </button>
                </div>
              </div>

              {/* Large Camera Feed */}
              <div
                className={`aspect-[21/9] bg-gradient-to-br ${allCameras[selectedCamera].gradient} rounded-2xl relative overflow-hidden shadow-2xl`}
              >
                <div className="absolute inset-0 bg-black/20"></div>

                {/* Alert Overlay */}
                <div
                  className={`absolute top-6 left-6 text-white text-base px-4 py-2 rounded-xl font-medium ${
                    allCameras[selectedCamera].alertType === "critical"
                      ? "bg-red-500/90"
                      : allCameras[selectedCamera].alertType === "warning"
                      ? "bg-yellow-500/90"
                      : allCameras[selectedCamera].alertType === "medium"
                      ? "bg-orange-500/90"
                      : allCameras[selectedCamera].alertType === "info"
                      ? "bg-blue-500/90"
                      : "bg-green-500/90"
                  }`}
                >
                  {allCameras[selectedCamera].alert}
                </div>

                {/* AI Detection Overlays */}
                {selectedCamera === 0 && (
                  <>
                    <div className="absolute top-20 left-20 w-20 h-28 border-3 border-green-400 rounded-lg">
                      <div className="absolute -top-8 left-0 bg-green-400 text-black text-sm px-3 py-1 rounded-lg font-medium">
                        Employee - Sarah K.
                      </div>
                    </div>
                    <div className="absolute top-24 right-16 w-16 h-24 border-3 border-yellow-400 rounded-lg">
                      <div className="absolute -top-8 right-0 bg-yellow-400 text-black text-sm px-3 py-1 rounded-lg font-medium">
                        Customer
                      </div>
                    </div>
                  </>
                )}

                {/* Timestamp */}
                <div className="absolute bottom-6 left-6 bg-black/70 text-white text-base px-4 py-2 rounded-xl font-medium">
                  {currentTime.toLocaleTimeString()}
                </div>

                {/* Camera Controls */}
                <div className="absolute bottom-6 right-6 flex space-x-3">
                  <button className="bg-black/70 text-white p-3 rounded-xl hover:bg-black/90 transition-colors">
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                      />
                    </svg>
                  </button>
                  <button className="bg-black/70 text-white p-3 rounded-xl hover:bg-black/90 transition-colors">
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                  </button>
                  <button className="bg-black/70 text-white p-3 rounded-xl hover:bg-black/90 transition-colors">
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 8V4a1 1 0 011-1h4M20 8V4a1 1 0 00-1-1h-4m5 8v4a1 1 0 01-1 1h-4M4 16v4a1 1 0 001 1h4"
                      />
                    </svg>
                  </button>
                </div>

                {/* Signal Strength */}
                <div className="absolute top-6 right-6 flex space-x-1">
                  <div
                    className={`w-1.5 h-4 rounded ${
                      allCameras[selectedCamera].fps > 25
                        ? "bg-green-400"
                        : "bg-gray-400"
                    }`}
                  ></div>
                  <div
                    className={`w-1.5 h-5 rounded ${
                      allCameras[selectedCamera].fps > 20
                        ? "bg-green-400"
                        : "bg-gray-400"
                    }`}
                  ></div>
                  <div
                    className={`w-1.5 h-6 rounded ${
                      allCameras[selectedCamera].fps > 15
                        ? "bg-green-400"
                        : "bg-gray-400"
                    }`}
                  ></div>
                </div>
              </div>

              {/* Camera Details Bar */}
              <div className="mt-6 grid grid-cols-4 gap-6">
                <div className="text-center">
                  <div
                    className={`text-lg font-semibold ${
                      allCameras[selectedCamera].status === "normal"
                        ? "text-green-600"
                        : allCameras[selectedCamera].status === "warning"
                        ? "text-yellow-600"
                        : "text-red-600"
                    }`}
                  >
                    {allCameras[selectedCamera].status
                      .replace("-", " ")
                      .toUpperCase()}
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-wide">
                    Status
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-900">
                    {allCameras[selectedCamera].region}
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-wide">
                    Region
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-blue-600">
                    {allCameras[selectedCamera].location}
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-wide">
                    Location
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-purple-600">
                    {allCameras[selectedCamera].id}
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-wide">
                    Camera ID
                  </div>
                </div>
              </div>
            </section>

            {/* Camera Grid - All Cameras Below */}
            <section className="bg-white/80 backdrop-blur-xl rounded-3xl p-6 shadow-sm border border-gray-100/50">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900">
                  All Cameras ({filteredCameras.length})
                </h2>
                <div className="flex items-center space-x-3">
                  <span className="text-sm text-gray-500">
                    Click any camera to view in main display
                  </span>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-xs text-gray-600">Online</span>
                    <div className="w-2 h-2 bg-red-500 rounded-full ml-3"></div>
                    <span className="text-xs text-gray-600">Alert</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {filteredCameras.map((camera, index) => (
                  <button
                    key={camera.id}
                    onClick={() =>
                      setSelectedCamera(
                        allCameras.findIndex((c) => c.id === camera.id)
                      )
                    }
                    className={`group bg-white/70 rounded-3xl p-5 shadow-lg border transition-all duration-300 hover:scale-[1.02] hover:shadow-xl ${
                      selectedCamera ===
                      allCameras.findIndex((c) => c.id === camera.id)
                        ? "border-blue-500 ring-2 ring-blue-200 shadow-xl scale-[1.02] bg-white/90"
                        : "border-gray-200/50 hover:border-blue-300"
                    }`}
                  >
                    {/* Camera Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div
                          className={`w-3 h-3 rounded-full ${getStatusColor(
                            camera.status
                          )} ${
                            camera.status.includes("alert")
                              ? "animate-pulse"
                              : ""
                          }`}
                        ></div>
                        <div className="text-left">
                          <h3 className="text-sm font-semibold text-gray-900">
                            {camera.name}
                          </h3>
                          <p className="text-xs text-gray-500">
                            {camera.location}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-gray-600 font-medium bg-gray-100 px-2 py-1 rounded-lg">
                          {camera.id}
                        </span>
                      </div>
                    </div>

                    {/* Camera Feed */}
                    <div
                      className={`aspect-video bg-gradient-to-br ${camera.gradient} rounded-2xl relative overflow-hidden mb-4 shadow-inner`}
                    >
                      <div className="absolute inset-0 bg-black/25 group-hover:bg-black/15 transition-colors"></div>

                      {/* Alert Overlay */}
                      {camera.status !== "normal" && (
                        <div
                          className={`absolute top-3 left-3 text-white text-xs px-2 py-1 rounded-lg font-medium ${
                            camera.alertType === "critical"
                              ? "bg-red-500/90"
                              : camera.alertType === "warning"
                              ? "bg-yellow-500/90"
                              : camera.alertType === "medium"
                              ? "bg-orange-500/90"
                              : "bg-blue-500/90"
                          }`}
                        >
                          {camera.alert}
                        </div>
                      )}

                      {/* Live Recording Indicator */}
                      <div className="absolute top-3 right-3 flex items-center space-x-1">
                        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                        <span className="text-white text-xs font-medium bg-black/50 px-1.5 py-0.5 rounded">
                          LIVE
                        </span>
                      </div>

                      {/* FPS and Quality */}
                      <div className="absolute bottom-3 left-3 flex items-center space-x-2">
                        <span className="text-white text-xs bg-black/60 px-2 py-1 rounded font-medium">
                          {camera.fps} FPS
                        </span>
                        <span
                          className={`text-white text-xs px-2 py-1 rounded font-medium ${
                            camera.quality === "HD"
                              ? "bg-green-600/80"
                              : "bg-yellow-600/80"
                          }`}
                        >
                          {camera.quality}
                        </span>
                      </div>

                      {/* Signal Strength */}
                      <div className="absolute bottom-3 right-3 flex space-x-0.5">
                        <div
                          className={`w-1 h-3 rounded ${
                            camera.fps > 25 ? "bg-green-400" : "bg-gray-400"
                          }`}
                        ></div>
                        <div
                          className={`w-1 h-4 rounded ${
                            camera.fps > 20 ? "bg-green-400" : "bg-gray-400"
                          }`}
                        ></div>
                        <div
                          className={`w-1 h-5 rounded ${
                            camera.fps > 15 ? "bg-green-400" : "bg-gray-400"
                          }`}
                        ></div>
                      </div>

                      {/* Selection Indicator */}
                      {selectedCamera ===
                        allCameras.findIndex((c) => c.id === camera.id) && (
                        <div className="absolute inset-0 border-2 border-blue-400 rounded-2xl bg-blue-400/10"></div>
                      )}
                    </div>

                    {/* Camera Info */}
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="text-center bg-gray-50 rounded-xl py-2">
                        <div
                          className={`font-semibold ${
                            camera.status === "normal"
                              ? "text-green-600"
                              : camera.status === "warning"
                              ? "text-yellow-600"
                              : "text-red-600"
                          }`}
                        >
                          {camera.status.replace("-", " ").toUpperCase()}
                        </div>
                        <div className="text-gray-500 text-xs">Status</div>
                      </div>
                      <div className="text-center bg-gray-50 rounded-xl py-2">
                        <div className="font-semibold text-gray-900">
                          {camera.region}
                        </div>
                        <div className="text-gray-500 text-xs">Region</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
