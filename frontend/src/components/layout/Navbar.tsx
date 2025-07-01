'use client';

import { useState } from 'react';
import Link from 'next/link';

interface NavbarProps {
  className?: string;
}

const Navbar = ({ className = "" }: NavbarProps) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <nav className={`bg-white/90 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-50 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <div className="w-8 h-8 bg-gradient-to-br from-red-500 via-orange-500 to-yellow-500 rounded-xl flex items-center justify-center shadow-lg">
              <div className="w-4 h-4 bg-white rounded-md opacity-95"></div>
            </div>
            <span className="ml-3 text-xl font-bold text-gray-900">RazZ Security</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-8">
              <Link href="/" className="text-gray-900 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                Home
              </Link>
              <a href="#features" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                Features
              </a>
              <a href="#pricing" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                Pricing
              </a>
              <a href="#about" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
                About
              </a>
              <a href="#contact" className="text-gray-600 hover:text-red-600 px-3 py-2 text-sm font-medium transition-colors">
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
              <Link href="/" className="text-gray-900 block px-3 py-2 text-base font-medium">Home</Link>
              <a href="#features" className="text-gray-600 block px-3 py-2 text-base font-medium">Features</a>
              <a href="#pricing" className="text-gray-600 block px-3 py-2 text-base font-medium">Pricing</a>
              <a href="#about" className="text-gray-600 block px-3 py-2 text-base font-medium">About</a>
              <a href="#contact" className="text-gray-600 block px-3 py-2 text-base font-medium">Contact</a>
              <div className="mt-4 space-y-2">
                <Link href="/login" className="w-full text-left text-gray-600 block px-3 py-2 text-base font-medium">
                  Sign In
                </Link>
                <Link href="/signup">
                  <button className="w-full bg-gradient-to-r from-red-600 to-orange-600 text-white px-3 py-2 rounded-xl text-base font-semibold">
                    Get Started
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

export default Navbar;
