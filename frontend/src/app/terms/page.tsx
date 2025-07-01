import Link from 'next/link';

const TermsPage = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <Link href="/" className="inline-flex items-center mb-8 text-red-600 hover:text-red-500 transition-colors duration-200">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Home
          </Link>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Terms of Service</h1>
          <p className="text-lg text-gray-600">Last updated: July 1, 2025</p>
        </div>

        {/* Content */}
        <div className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
          <div className="prose prose-lg max-w-none">
            <h2>1. Acceptance of Terms</h2>
            <p>
              By accessing and using RazZ Security's services, you accept and agree to be bound by the terms 
              and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
            </p>

            <h2>2. Description of Service</h2>
            <p>
              RazZ Security provides AI-powered cybersecurity solutions including but not limited to:
            </p>
            <ul>
              <li>Real-time threat detection and monitoring</li>
              <li>Automated security response systems</li>
              <li>Compliance management tools</li>
              <li>Security analytics and reporting</li>
              <li>Incident response coordination</li>
            </ul>

            <h2>3. User Responsibilities</h2>
            <p>
              As a user of RazZ Security services, you agree to:
            </p>
            <ul>
              <li>Provide accurate and complete information during registration</li>
              <li>Maintain the security of your account credentials</li>
              <li>Use the service in compliance with all applicable laws and regulations</li>
              <li>Not attempt to gain unauthorized access to our systems</li>
              <li>Report any security vulnerabilities responsibly</li>
            </ul>

            <h2>4. Data Security and Privacy</h2>
            <p>
              RazZ Security implements enterprise-grade security measures to protect your data:
            </p>
            <ul>
              <li>256-bit SSL encryption for all data transmission</li>
              <li>SOC 2 Type II compliance</li>
              <li>ISO 27001 certified security practices</li>
              <li>GDPR compliance for data protection</li>
              <li>Regular security audits and penetration testing</li>
            </ul>

            <h2>5. Service Availability</h2>
            <p>
              While we strive for 99.9% uptime, RazZ Security does not guarantee uninterrupted service. 
              Scheduled maintenance will be communicated in advance when possible.
            </p>

            <h2>6. Limitation of Liability</h2>
            <p>
              RazZ Security shall not be liable for any indirect, incidental, special, consequential, 
              or punitive damages resulting from your access to or use of, or inability to access or use, the service.
            </p>

            <h2>7. Termination</h2>
            <p>
              Either party may terminate this agreement at any time. Upon termination, your access to 
              the service will be discontinued, and any data associated with your account may be deleted 
              according to our data retention policy.
            </p>

            <h2>8. Intellectual Property</h2>
            <p>
              All content, features, and functionality of RazZ Security services are owned by us or our 
              licensors and are protected by international copyright, trademark, and other intellectual property laws.
            </p>

            <h2>9. Modifications to Terms</h2>
            <p>
              RazZ Security reserves the right to modify these terms at any time. Users will be notified 
              of significant changes via email or through the service dashboard.
            </p>

            <h2>10. Contact Information</h2>
            <p>
              If you have any questions about these Terms of Service, please contact us:
            </p>
            <ul>
              <li>Email: legal@razzsecurity.com</li>
              <li>Phone: +1 (555) 123-RAZZ</li>
              <li>Address: 123 Security Blvd, Cyber City, CC 12345</li>
            </ul>
          </div>
        </div>

        {/* Footer Links */}
        <div className="text-center mt-12">
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/privacy" className="text-red-600 hover:text-red-500 transition-colors duration-200">
              Privacy Policy
            </Link>
            <Link href="/signup" className="text-red-600 hover:text-red-500 transition-colors duration-200">
              Create Account
            </Link>
            <Link href="/login" className="text-red-600 hover:text-red-500 transition-colors duration-200">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TermsPage;
