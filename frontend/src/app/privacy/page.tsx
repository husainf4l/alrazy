import Link from 'next/link';

const PrivacyPage = () => {
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
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Privacy Policy</h1>
          <p className="text-lg text-gray-600">Last updated: July 1, 2025</p>
        </div>

        {/* Content */}
        <div className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
          <div className="prose prose-lg max-w-none">
            <h2>1. Information We Collect</h2>
            <h3>Personal Information</h3>
            <p>
              When you create an account with RazZ Security, we collect:
            </p>
            <ul>
              <li>Name and contact information (email, phone number)</li>
              <li>Company information and job title</li>
              <li>Account credentials and authentication data</li>
              <li>Billing and payment information</li>
            </ul>

            <h3>Security and System Data</h3>
            <p>
              To provide our security services, we may collect:
            </p>
            <ul>
              <li>Network traffic patterns and metadata</li>
              <li>System logs and security event data</li>
              <li>Threat intelligence and incident response data</li>
              <li>Performance and usage analytics</li>
            </ul>

            <h2>2. How We Use Your Information</h2>
            <p>
              RazZ Security uses your information to:
            </p>
            <ul>
              <li>Provide and improve our security services</li>
              <li>Detect, prevent, and respond to security threats</li>
              <li>Send security alerts and system notifications</li>
              <li>Provide customer support and technical assistance</li>
              <li>Comply with legal obligations and industry standards</li>
              <li>Conduct security research and threat analysis</li>
            </ul>

            <h2>3. Data Protection and Security</h2>
            <h3>Encryption and Storage</h3>
            <ul>
              <li>All data is encrypted in transit using TLS 1.3</li>
              <li>Data at rest is encrypted using AES-256 encryption</li>
              <li>Encryption keys are managed using hardware security modules (HSMs)</li>
              <li>Data is stored in SOC 2 Type II certified data centers</li>
            </ul>

            <h3>Access Controls</h3>
            <ul>
              <li>Multi-factor authentication for all administrative access</li>
              <li>Role-based access controls with principle of least privilege</li>
              <li>Regular access reviews and security audits</li>
              <li>Zero-trust network architecture</li>
            </ul>

            <h2>4. Data Sharing and Disclosure</h2>
            <p>
              RazZ Security does not sell your personal information. We may share data in these limited circumstances:
            </p>
            <ul>
              <li><strong>Service Providers:</strong> Trusted third parties who assist in service delivery</li>
              <li><strong>Legal Requirements:</strong> When required by law or to protect rights and safety</li>
              <li><strong>Threat Intelligence:</strong> Anonymized threat data shared with security community</li>
              <li><strong>Business Transfers:</strong> In the event of a merger or acquisition</li>
            </ul>

            <h2>5. Data Retention</h2>
            <p>
              We retain your information for as long as necessary to provide services and comply with legal obligations:
            </p>
            <ul>
              <li>Account data: Retained while your account is active</li>
              <li>Security logs: Retained for 7 years for compliance purposes</li>
              <li>Billing records: Retained per applicable financial regulations</li>
              <li>Anonymized analytics: May be retained indefinitely for research</li>
            </ul>

            <h2>6. Your Rights and Choices</h2>
            <h3>GDPR Rights (EU Residents)</h3>
            <ul>
              <li>Right to access your personal data</li>
              <li>Right to rectify inaccurate information</li>
              <li>Right to erasure ("right to be forgotten")</li>
              <li>Right to restrict processing</li>
              <li>Right to data portability</li>
              <li>Right to object to processing</li>
            </ul>

            <h3>CCPA Rights (California Residents)</h3>
            <ul>
              <li>Right to know what personal information is collected</li>
              <li>Right to delete personal information</li>
              <li>Right to opt-out of sale (we don't sell data)</li>
              <li>Right to non-discrimination</li>
            </ul>

            <h2>7. International Data Transfers</h2>
            <p>
              RazZ Security operates globally and may transfer data across borders. We ensure adequate protection through:
            </p>
            <ul>
              <li>Standard Contractual Clauses (SCCs) for EU data transfers</li>
              <li>Adequacy decisions where available</li>
              <li>Data Processing Agreements with all vendors</li>
              <li>Privacy Shield successor frameworks</li>
            </ul>

            <h2>8. Cookies and Tracking</h2>
            <h3>Essential Cookies</h3>
            <p>
              We use essential cookies for authentication, security, and basic functionality. These cannot be disabled.
            </p>

            <h3>Analytics Cookies</h3>
            <p>
              With your consent, we use analytics cookies to improve our services. You can opt-out at any time.
            </p>

            <h2>9. Third-Party Services</h2>
            <p>
              Our service integrates with various third-party security tools and platforms. Each integration is governed by strict data sharing agreements and security requirements.
            </p>

            <h2>10. Children's Privacy</h2>
            <p>
              RazZ Security does not knowingly collect personal information from children under 13. If we become aware of such collection, we will delete the information immediately.
            </p>

            <h2>11. Changes to This Policy</h2>
            <p>
              We may update this privacy policy periodically. Material changes will be communicated via:
            </p>
            <ul>
              <li>Email notification to account holders</li>
              <li>Prominent notice in the dashboard</li>
              <li>30-day advance notice for significant changes</li>
            </ul>

            <h2>12. Contact Information</h2>
            <p>
              For privacy-related questions or to exercise your rights:
            </p>
            <ul>
              <li><strong>Data Protection Officer:</strong> privacy@razzsecurity.com</li>
              <li><strong>EU Representative:</strong> eu-privacy@razzsecurity.com</li>
              <li><strong>Phone:</strong> +1 (555) 123-RAZZ</li>
              <li><strong>Mail:</strong> RazZ Security Privacy Team, 123 Security Blvd, Cyber City, CC 12345</li>
            </ul>

            <h2>13. Compliance Certifications</h2>
            <p>
              RazZ Security maintains the following privacy and security certifications:
            </p>
            <ul>
              <li>SOC 2 Type II (Security, Availability, Confidentiality)</li>
              <li>ISO 27001:2013 Information Security Management</li>
              <li>ISO 27018:2019 Cloud Privacy</li>
              <li>GDPR Article 32 Technical and Organizational Measures</li>
              <li>FedRAMP Moderate (in progress)</li>
            </ul>
          </div>
        </div>

        {/* Footer Links */}
        <div className="text-center mt-12">
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/terms" className="text-red-600 hover:text-red-500 transition-colors duration-200">
              Terms of Service
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

export default PrivacyPage;
