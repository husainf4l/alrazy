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
  const [viewMode, setViewMode] = useState("grid");

  // Clean, professional camera data - Apple-inspired minimal design
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
      aiAlerts: ["Person detected", "After hours"],
    },
    {
      id: "CAM-002", 
      name: "Medical Center",
      location: "Pharmacy Counter",
      status: "normal",
      fps: 30,
      quality: "4K",
      region: "Medical Center",
      lastEvent: "Normal operations",
      eventTime: "Active",
      confidence: 98,
      aiAlerts: [],
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
      aiAlerts: [],
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
      aiAlerts: ["Maintenance required"],
    },
    {
      id: "CAM-005",
      name: "Central Plaza",
      location: "Main Entrance",
      status: "medium",
      fps: 30,
      quality: "4K",
      region: "Downtown District",
      lastEvent: "Unusual activity",
      eventTime: "8 min ago",
      confidence: 87,
      aiAlerts: ["Crowd detected", "Queue forming"],
    },
    // Generate additional cameras
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
        aiAlerts: [],
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

  const alertCameras = allCameras.filter(camera => camera.status !== "normal");

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "critical": return "bg-red-500";
      case "medium": return "bg-orange-500";
      case "warning": return "bg-yellow-500";
      default: return "bg-green-500";
    }
  };

  const getStatusDot = (status: string) => {
    switch (status) {
      case "critical": return "bg-red-500";
      case "medium": return "bg-orange-500";
      case "warning": return "bg-yellow-500";
      default: return "bg-green-500";
    }
  };

  const getStatusCount = (status: string) => {
    return allCameras.filter((camera) => camera.status === status).length;
  };

  return (
    <div className="min-h-screen bg-gray-50 font-system-ui antialiased">
      <Sidebar activeItem="camera-management" />

      <div className="ml-14 flex flex-col min-h-screen">
        <DashboardHeader
          title="Camera Management"
          showSearch={true}
          showAlerts={true}
          showSecurityStatus={true}
        />

        <main className="flex-1 p-6 space-y-6">
          <div className="max-w-7xl mx-auto space-y-6">

            {/* AI Priority Alerts */}
            {alertCameras.length > 0 && (
              <section className="bg-white rounded-2xl shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
                        <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold text-gray-900">Priority Alerts</h2>
                        <p className="text-sm text-gray-500">AI-powered threat detection</p>
                      </div>
                      <div className="px-2 py-1 bg-red-500 text-white text-xs font-medium rounded-full">
                        {alertCameras.length}
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-6 text-xs text-gray-500">
                      <div>AI Confidence: <span className="font-medium text-gray-900">98.7%</span></div>
                      <div>Response: <span className="font-medium text-gray-900">0.3s</span></div>
                      <div>Detection: <span className="font-medium text-gray-900">99.1%</span></div>
                    </div>
                  </div>
                </div>

                <div className="p-6">
                  <div className="flex space-x-4 overflow-x-auto pb-2">
                    {alertCameras.map((camera) => (
                      <button
                        key={camera.id}
                        onClick={() => setSelectedCamera(allCameras.findIndex((c) => c.id === camera.id))}
                        className="flex-shrink-0 w-72 bg-gray-50 rounded-xl p-4 hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-start space-x-3">
                          <div className="w-16 h-12 bg-gray-800 rounded-lg relative flex-shrink-0">
                            <div className={`absolute top-1 left-1 w-2 h-2 rounded-full ${getStatusDot(camera.status)} animate-pulse`}></div>
                            <div className="absolute bottom-1 right-1 text-white text-xs bg-black/60 px-1 rounded">
                              {camera.fps}fps
                            </div>
                          </div>
                          
                          <div className="flex-1 text-left">
                            <div className="flex items-center justify-between mb-1">
                              <h3 className="font-medium text-gray-900 text-sm">{camera.name}</h3>
                              <span className={`text-xs px-2 py-1 rounded-md font-medium ${
                                camera.status === "critical" ? "bg-red-100 text-red-700" :
                                camera.status === "medium" ? "bg-orange-100 text-orange-700" :
                                "bg-yellow-100 text-yellow-700"
                              }`}>
                                {camera.status.toUpperCase()}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 mb-2">{camera.location}</p>
                            <p className="text-xs text-gray-900 font-medium">{camera.lastEvent}</p>
                            <p className="text-xs text-gray-500">{camera.eventTime}</p>
                            
                            {camera.aiAlerts.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {camera.aiAlerts.map((alert, idx) => (
                                  <span key={idx} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-md">
                                    {alert}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* Main Camera View */}
            <section className="bg-white rounded-2xl shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className={`w-3 h-3 rounded-full ${getStatusDot(allCameras[selectedCamera].status)} animate-pulse`}></div>
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {allCameras[selectedCamera].name}
                      </h2>
                      <p className="text-sm text-gray-500">
                        {allCameras[selectedCamera].location} • {allCameras[selectedCamera].id}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-6">
                    <div className="text-right">
                      <div className="text-sm font-semibold text-gray-900">{allCameras[selectedCamera].fps} FPS</div>
                      <div className="text-xs text-gray-500">Frame Rate</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold text-gray-900">{allCameras[selectedCamera].quality}</div>
                      <div className="text-xs text-gray-500">Quality</div>
                    </div>
                    <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
                      Fullscreen
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-6">
                <div className="aspect-[21/9] bg-gray-900 rounded-xl relative overflow-hidden">
                  {/* Camera feed placeholder */}
                  <div className="absolute inset-0 bg-gradient-to-br from-gray-800 to-gray-900"></div>
                  
                  {/* Status overlay */}
                  {allCameras[selectedCamera].status !== "normal" && (
                    <div className={`absolute top-4 left-4 text-white text-sm px-3 py-1.5 rounded-lg font-medium ${
                      allCameras[selectedCamera].status === "critical" ? "bg-red-500/90" :
                      allCameras[selectedCamera].status === "medium" ? "bg-orange-500/90" :
                      "bg-yellow-500/90"
                    }`}>
                      {allCameras[selectedCamera].lastEvent}
                    </div>
                  )}

                  {/* AI Detection boxes (for demo) */}
                  {selectedCamera === 0 && (
                    <>
                      <div className="absolute top-16 left-16 w-16 h-24 border-2 border-green-400 rounded">
                        <div className="absolute -top-6 left-0 bg-green-400 text-black text-xs px-2 py-1 rounded font-medium">
                          Person
                        </div>
                      </div>
                      <div className="absolute top-20 right-20 w-12 h-20 border-2 border-yellow-400 rounded">
                        <div className="absolute -top-6 right-0 bg-yellow-400 text-black text-xs px-2 py-1 rounded font-medium">
                          Motion
                        </div>
                      </div>
                    </>
                  )}

                  {/* Timestamp */}
                  <div className="absolute bottom-4 left-4 bg-black/70 text-white text-sm px-3 py-1.5 rounded-lg">
                    {currentTime.toLocaleTimeString()}
                  </div>

                  {/* Controls */}
                  <div className="absolute bottom-4 right-4 flex space-x-2">
                    <button className="bg-black/70 text-white p-2 rounded-lg hover:bg-black/90 transition-colors">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </button>
                    <button className="bg-black/70 text-white p-2 rounded-lg hover:bg-black/90 transition-colors">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                    <button className="bg-black/70 text-white p-2 rounded-lg hover:bg-black/90 transition-colors">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4a1 1 0 011-1h4M20 8V4a1 1 0 00-1-1h-4m5 8v4a1 1 0 01-1 1h-4M4 16v4a1 1 0 001 1h4" />
                      </svg>
                    </button>
                  </div>

                  {/* Signal strength */}
                  <div className="absolute top-4 right-4 flex space-x-1">
                    <div className={`w-1 h-3 rounded ${allCameras[selectedCamera].fps > 25 ? "bg-green-400" : "bg-gray-400"}`}></div>
                    <div className={`w-1 h-4 rounded ${allCameras[selectedCamera].fps > 20 ? "bg-green-400" : "bg-gray-400"}`}></div>
                    <div className={`w-1 h-5 rounded ${allCameras[selectedCamera].fps > 15 ? "bg-green-400" : "bg-gray-400"}`}></div>
                  </div>
                </div>

                {/* Camera details */}
                <div className="mt-6 grid grid-cols-4 gap-6">
                  <div className="text-center">
                    <div className={`text-sm font-semibold ${
                      allCameras[selectedCamera].status === "normal" ? "text-green-600" :
                      allCameras[selectedCamera].status === "warning" ? "text-yellow-600" : "text-red-600"
                    }`}>
                      {allCameras[selectedCamera].status.toUpperCase()}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Status</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-semibold text-gray-900">{allCameras[selectedCamera].region}</div>
                    <div className="text-xs text-gray-500 mt-1">Region</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-semibold text-gray-900">{allCameras[selectedCamera].confidence}%</div>
                    <div className="text-xs text-gray-500 mt-1">AI Confidence</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-semibold text-gray-900">{allCameras[selectedCamera].eventTime}</div>
                    <div className="text-xs text-gray-500 mt-1">Last Event</div>
                  </div>
                </div>
              </div>
            </section>

            {/* Camera Grid */}
            <section className="bg-white rounded-2xl shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Camera Network</h2>
                    <p className="text-sm text-gray-500">{allCameras.length} cameras total</p>
                  </div>
                  
                  <div className="flex items-center space-x-4 text-xs text-gray-500">
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
                      <span>{getStatusCount("medium")} Medium</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                      <span>{getStatusCount("critical")} Critical</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="Search cameras..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="all">All Status</option>
                    <option value="normal">Normal</option>
                    <option value="warning">Warning</option>
                    <option value="medium">Medium</option>
                    <option value="critical">Critical</option>
                  </select>
                  <div className="text-sm text-gray-500">
                    {filteredCameras.length} of {allCameras.length}
                  </div>
                </div>
              </div>

              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {filteredCameras.map((camera) => (
                    <button
                      key={camera.id}
                      onClick={() => setSelectedCamera(allCameras.findIndex((c) => c.id === camera.id))}
                      className={`group bg-gray-50 rounded-xl p-4 hover:bg-gray-100 transition-all duration-200 ${
                        selectedCamera === allCameras.findIndex((c) => c.id === camera.id)
                          ? "ring-2 ring-blue-500 bg-blue-50"
                          : ""
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <div className={`w-2 h-2 rounded-full ${getStatusDot(camera.status)} ${
                            camera.status !== "normal" ? "animate-pulse" : ""
                          }`}></div>
                          <span className="text-xs text-gray-500 font-medium">{camera.id}</span>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded-md font-medium ${
                          camera.status === "critical" ? "bg-red-100 text-red-700" :
                          camera.status === "medium" ? "bg-orange-100 text-orange-700" :
                          camera.status === "warning" ? "bg-yellow-100 text-yellow-700" :
                          "bg-green-100 text-green-700"
                        }`}>
                          {camera.status.toUpperCase()}
                        </span>
                      </div>

                      <div className="aspect-video bg-gray-800 rounded-lg relative overflow-hidden mb-3">
                        <div className="absolute inset-0 bg-gradient-to-br from-gray-700 to-gray-900"></div>
                        
                        {camera.status !== "normal" && (
                          <div className={`absolute top-2 left-2 w-2 h-2 rounded-full ${getStatusDot(camera.status)} animate-pulse`}></div>
                        )}
                        
                        <div className="absolute top-2 right-2 text-white text-xs bg-black/60 px-1.5 py-0.5 rounded">
                          LIVE
                        </div>
                        
                        <div className="absolute bottom-2 left-2 text-white text-xs bg-black/60 px-1.5 py-0.5 rounded">
                          {camera.fps}fps
                        </div>
                        
                        <div className="absolute bottom-2 right-2 text-white text-xs bg-black/60 px-1.5 py-0.5 rounded">
                          {camera.quality}
                        </div>

                        {selectedCamera === allCameras.findIndex((c) => c.id === camera.id) && (
                          <div className="absolute inset-0 border-2 border-blue-400 rounded-lg bg-blue-400/10"></div>
                        )}
                      </div>

                      <div className="text-left">
                        <h3 className="text-sm font-medium text-gray-900 truncate">{camera.name}</h3>
                        <p className="text-xs text-gray-500 truncate">{camera.location}</p>
                        <p className="text-xs text-gray-400 mt-1">{camera.region}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </section>

          </div>
        </main>
      </div>
    </div>
  );
}
