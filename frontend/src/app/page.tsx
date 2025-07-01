'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Footer } from '../components';

// Navigation Component for Main Website
const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <nav className="bg-white/90 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <div className="w-8 h-8 bg-gradient-to-br from-red-500 via-orange-500 to-yellow-500 rounded-xl flex items-center justify-center shadow-lg">
              <div className="w-4 h-4 bg-white rounded-md opacity-95"></div>
            </div>
            <span className="ml-3 text-xl font-bold text-gray-900">RazZ Security</span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-8">
              <a href="#" className="text-gray-900 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                Home
              </a>
              <a href="#" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                AI Cameras
              </a>
              <a href="#" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                Motion Detection
              </a>
              <a href="#" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                For Businesses
              </a>
              <a href="#" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                Contact
              </a>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            <Link href="/login" className="text-gray-600 hover:text-gray-900 px-4 py-2 text-sm font-medium transition-colors">
              Sign In
            </Link>
            <Link href="/signup">
              <button className="bg-gradient-to-r from-red-600 to-orange-600 text-white px-6 py-2 rounded-xl text-sm font-semibold hover:from-red-700 hover:to-orange-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105">
                Get Started
              </button>
            </Link>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-600 hover:text-gray-900 focus:outline-none"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={isMenuOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 bg-white border-t border-gray-200">
              <a href="#" className="text-gray-900 block px-3 py-2 text-base font-medium">Home</a>
              <a href="#" className="text-gray-600 block px-3 py-2 text-base font-medium">AI Cameras</a>
              <a href="#" className="text-gray-600 block px-3 py-2 text-base font-medium">Motion Detection</a>
              <a href="#" className="text-gray-600 block px-3 py-2 text-base font-medium">For Businesses</a>
              <a href="#" className="text-gray-600 block px-3 py-2 text-base font-medium">Contact</a>
              <div className="mt-4 space-y-2">
                <Link href="/login" className="w-full text-left text-gray-600 block px-3 py-2 text-base font-medium">
                  Sign In
                </Link>
                <Link href="/signup">
                  <button className="w-full bg-gradient-to-r from-red-600 to-orange-600 text-white px-3 py-2 rounded-xl text-base font-semibold">
                    Start Free Trial
                  </button>
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

// Hero Section
const HeroSection = () => {
  return (
    <section className="bg-gradient-to-br from-gray-50 via-white to-gray-100 py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6 tracking-tight">
            AI-Powered Security Cameras for{' '}
            <span className="bg-gradient-to-r from-red-500 to-orange-500 bg-clip-text text-transparent">
              Smart Protection
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
            Advanced AI security camera system that detects motion and suspicious activities in real-time. 
            Perfect for stores, banks, and retail locations with instant notifications to security teams.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/signup">
              <button className="px-8 py-4 bg-gradient-to-r from-red-600 to-orange-600 text-white text-lg font-semibold rounded-2xl hover:from-red-700 hover:to-orange-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105">
                Start Free Trial
              </button>
            </Link>
            <Link href="/login">
              <button className="px-8 py-4 bg-white text-gray-700 text-lg font-semibold rounded-2xl border border-gray-200 hover:bg-gray-50 transition-all duration-200 shadow-sm hover:shadow-md">
                Access Security Dashboard
              </button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
};

// Features Section
const FeaturesSection = () => {
  const features = [
    {
      icon: "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z",
      title: "AI-Powered Camera Detection",
      description: "Advanced computer vision algorithms analyze live camera feeds to detect motion and identify suspicious activities in real-time."
    },
    {
      icon: "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
      title: "Instant Security Alerts",
      description: "Immediate notifications sent to security teams when suspicious behavior or unauthorized motion is detected."
    },
    {
      icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
      title: "Perfect for Retail & Banks",
      description: "Specifically designed for stores, banks, and point-of-sale locations with customizable security zones and sensitivity settings."
    }
  ];

  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Why Choose RazZ Security Cameras?
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Intelligent AI-powered security cameras that protect your business with advanced motion detection and real-time alerts.
          </p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div key={index} className="text-center p-8 rounded-2xl hover:bg-gray-50 transition-all duration-200">
              <div className="w-16 h-16 bg-gradient-to-br from-red-100 to-orange-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={feature.icon} />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-4">{feature.title}</h3>
              <p className="text-gray-600 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// Main Home Page Component
export default function HomePage() {
  return (
    <div className="min-h-screen bg-white font-sans antialiased">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <Footer />
    </div>
  );
}
