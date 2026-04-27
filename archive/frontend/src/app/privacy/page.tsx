import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy - Ledgi',
  description: 'Learn how Ledgi collects, uses, and protects your personal and financial information.',
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-surface-base py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <Link
            href="/login"
            className="text-sm text-slate-600 hover:text-slate-900"
          >
            &larr; Back to Login
          </Link>
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">
          Privacy Policy
        </h1>
        <p className="text-sm text-slate-500 mb-8">
          Last updated: January 28, 2026
        </p>

        <div className="prose prose-slate max-w-none space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              1. Introduction
            </h2>
            <p className="text-slate-600 leading-relaxed">
              Ledgi (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) is committed to protecting your privacy.
              This Privacy Policy explains how we collect, use, disclose, and safeguard your
              information when you use our personal finance tracking application. Please read
              this policy carefully. By using Ledgi, you consent to the practices described herein.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              2. Information We Collect
            </h2>

            <h3 className="text-lg font-medium text-slate-800 mt-6 mb-3">
              2.1 Account Information
            </h3>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Email address</li>
              <li>Name</li>
              <li>Password (stored securely using bcrypt encryption)</li>
              <li>Account creation and update timestamps</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-800 mt-6 mb-3">
              2.2 Financial Data
            </h3>
            <p className="text-slate-600 mb-3">
              When you connect your financial institutions, we collect:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Bank and financial institution names</li>
              <li>Account types (checking, savings, credit card)</li>
              <li>Account balances and available credit</li>
              <li>Last 4 digits of account numbers</li>
              <li>Transaction history including amounts, dates, merchant names, and categories</li>
              <li>Transaction status (pending or posted)</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-800 mt-6 mb-3">
              2.3 User-Generated Content
            </h3>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Financial goals and budgets you create</li>
              <li>Custom transaction tags and categories</li>
              <li>Chat conversations with our AI assistant</li>
              <li>Profile information (income, household size, location)</li>
              <li>Feedback on insights and recommendations</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-800 mt-6 mb-3">
              2.4 Automatically Collected Information
            </h3>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Device information and browser type</li>
              <li>IP address</li>
              <li>Usage patterns and feature interactions</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              3. How We Use Your Information
            </h2>
            <p className="text-slate-600 mb-3">We use the collected information to:</p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Provide and maintain the Ledgi service</li>
              <li>Display your financial accounts and transactions</li>
              <li>Generate spending analytics and insights</li>
              <li>Detect unusual transactions and potential anomalies</li>
              <li>Power AI-driven financial advice through our chat feature</li>
              <li>Categorize and enrich transaction data for better insights</li>
              <li>Track progress toward your financial goals</li>
              <li>Send password reset emails when requested</li>
              <li>Improve and optimize our services</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              4. Third-Party Services
            </h2>
            <p className="text-slate-600 mb-4">
              We integrate with the following third-party services to provide our features:
            </p>

            <h3 className="text-lg font-medium text-slate-800 mt-6 mb-3">
              4.1 Teller.io (Banking Data Provider)
            </h3>
            <p className="text-slate-600">
              We use Teller to securely connect to your financial institutions. Teller receives
              your banking credentials directly and provides us with read-only access to your
              account and transaction data. We never see or store your banking login credentials.
            </p>

            <h3 className="text-lg font-medium text-slate-800 mt-6 mb-3">
              4.2 AI Services (Anthropic Claude)
            </h3>
            <p className="text-slate-600">
              We use AI services to provide intelligent transaction categorization, financial
              insights, and chat assistance. Transaction descriptions and amounts may be
              processed by these services to provide personalized recommendations.
            </p>

            <h3 className="text-lg font-medium text-slate-800 mt-6 mb-3">
              4.3 Optional Enrichment Services
            </h3>
            <p className="text-slate-600">
              We may use additional services to improve merchant name recognition and
              transaction categorization accuracy. These services receive anonymized
              transaction data only.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              5. Data Security
            </h2>
            <p className="text-slate-600 mb-3">
              We implement appropriate security measures to protect your information:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Passwords are hashed using bcrypt with salt</li>
              <li>All data transmission uses TLS encryption</li>
              <li>Banking connections use certificate-based authentication (mTLS)</li>
              <li>Access tokens are encrypted in production environments</li>
              <li>API endpoints are protected with rate limiting</li>
              <li>JWT-based authentication with secure token refresh</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              6. Data Retention
            </h2>
            <p className="text-slate-600">
              We retain your personal and financial data for as long as your account is active
              or as needed to provide you services. You may request deletion of your account
              and associated data at any time. Transaction history and analytics data are
              retained to provide historical spending insights. Chat conversation history is
              retained to improve your experience and provide context for future interactions.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              7. Your Rights and Data Management
            </h2>
            <p className="text-slate-600 mb-3">You have the right to:</p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Access your personal and financial information through the dashboard and API</li>
              <li>Disconnect financial institutions at any time through Settings, which removes all associated account and transaction data</li>
              <li>Delete chat conversations through the chat interface</li>
              <li>Modify your profile information and financial goals</li>
              <li>Revoke API keys at any time</li>
            </ul>
            <p className="text-slate-600 mt-4 mb-3">
              To exercise the following rights, please contact us at support@example.com:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Request a full export of your data</li>
              <li>Request deletion of your account and all associated data</li>
              <li>Request correction of inaccurate information</li>
              <li>Opt out of AI-powered transaction enrichment</li>
            </ul>
            <p className="text-slate-600 mt-4">
              We will respond to data requests within 30 days.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              8. Data Sharing
            </h2>
            <p className="text-slate-600 mb-3">
              We do not sell your personal or financial information. We may share data only:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>With service providers who assist in operating our platform (as described in Section 4)</li>
              <li>When required by law or to respond to legal process</li>
              <li>To protect our rights, privacy, safety, or property</li>
              <li>In connection with a merger, acquisition, or sale of assets (with notice to you)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              9. Children&apos;s Privacy
            </h2>
            <p className="text-slate-600">
              Ledgi is not intended for use by individuals under the age of 18. We do not
              knowingly collect personal information from children. If you believe we have
              collected information from a child, please contact us immediately.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              10. Changes to This Policy
            </h2>
            <p className="text-slate-600">
              We may update this Privacy Policy from time to time. We will notify you of any
              material changes by posting the new policy on this page and updating the
              &quot;Last updated&quot; date. Your continued use of Ledgi after changes are posted
              constitutes acceptance of the modified policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              11. Contact Us
            </h2>
            <p className="text-slate-600">
              If you have questions about this Privacy Policy or our data practices, please
              contact us at support@example.com.
            </p>
          </section>
        </div>

        <div className="mt-12 pt-8 border-t border-slate-200">
          <p className="text-center text-sm text-slate-500">
            <Link href="/login" className="text-slate-600 hover:text-slate-900">
              Sign in
            </Link>
            {' '}&middot;{' '}
            <Link href="/register" className="text-slate-600 hover:text-slate-900">
              Create an account
            </Link>
            {' '}&middot;{' '}
            <Link href="/terms" className="text-slate-600 hover:text-slate-900">
              Terms of Service
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
