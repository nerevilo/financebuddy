import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service - Ledgi',
  description: 'Terms of Service for using the Ledgi personal finance application.',
};

export default function TermsPage() {
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
          Terms of Service
        </h1>
        <p className="text-sm text-slate-500 mb-8">
          Last updated: January 28, 2026
        </p>

        <div className="prose prose-slate max-w-none space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              1. Acceptance of Terms
            </h2>
            <p className="text-slate-600 leading-relaxed">
              By accessing or using Ledgi (&quot;the Service&quot;), you agree to be bound by these
              Terms of Service (&quot;Terms&quot;). If you do not agree to these Terms, you may not use
              the Service. We reserve the right to modify these Terms at any time, and your
              continued use of the Service constitutes acceptance of any modifications.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              2. Description of Service
            </h2>
            <p className="text-slate-600 leading-relaxed">
              Ledgi is a personal finance management application that allows users to:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2 mt-3">
              <li>Connect and aggregate financial accounts from multiple institutions</li>
              <li>View transactions, balances, and spending analytics</li>
              <li>Receive AI-powered financial insights and recommendations</li>
              <li>Set and track financial goals</li>
              <li>Interact with an AI assistant for financial queries</li>
              <li>Access their data programmatically via API</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              3. Account Registration
            </h2>
            <p className="text-slate-600 leading-relaxed mb-3">
              To use the Service, you must create an account. You agree to:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Provide accurate and complete registration information</li>
              <li>Maintain the security of your password and account</li>
              <li>Notify us immediately of any unauthorized use of your account</li>
              <li>Accept responsibility for all activities that occur under your account</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              4. Financial Data and Bank Connections
            </h2>
            <p className="text-slate-600 leading-relaxed mb-3">
              By connecting your financial institutions to Ledgi:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>You authorize us to access your account information through our banking data provider (Teller.io)</li>
              <li>You represent that you are the legal owner or authorized user of the connected accounts</li>
              <li>You understand that we receive read-only access to your financial data</li>
              <li>You acknowledge that the accuracy of data depends on the information provided by your financial institutions</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              5. Acceptable Use
            </h2>
            <p className="text-slate-600 leading-relaxed mb-3">
              You agree not to:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Use the Service for any unlawful purpose or in violation of any laws</li>
              <li>Access accounts or data belonging to others without authorization</li>
              <li>Attempt to gain unauthorized access to our systems or networks</li>
              <li>Use automated systems to access the Service in a manner that exceeds reasonable use</li>
              <li>Resell, redistribute, or sublicense access to the Service</li>
              <li>Reverse engineer, decompile, or disassemble any part of the Service</li>
              <li>Use the Service to commit fraud or other financial crimes</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              6. API Usage
            </h2>
            <p className="text-slate-600 leading-relaxed mb-3">
              If you use our API:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>You are responsible for maintaining the security of your API keys</li>
              <li>You must comply with all rate limits and usage restrictions</li>
              <li>API access is for personal use only unless otherwise agreed in writing</li>
              <li>We reserve the right to revoke API access for violation of these Terms</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              7. AI Features and Recommendations
            </h2>
            <p className="text-slate-600 leading-relaxed">
              The Service includes AI-powered features that provide financial insights and recommendations.
              You acknowledge that:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2 mt-3">
              <li>AI-generated content is for informational purposes only and does not constitute financial advice</li>
              <li>You should consult qualified financial professionals before making significant financial decisions</li>
              <li>AI recommendations may not be suitable for your specific circumstances</li>
              <li>We do not guarantee the accuracy or completeness of AI-generated insights</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              8. Intellectual Property
            </h2>
            <p className="text-slate-600 leading-relaxed">
              The Service, including its design, features, content, and technology, is owned by
              Ledgi and protected by intellectual property laws. You retain ownership of your
              personal financial data. By using the Service, you grant us a limited license to
              process your data solely to provide the Service to you.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              9. Disclaimers
            </h2>
            <p className="text-slate-600 leading-relaxed mb-3">
              THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; WITHOUT WARRANTIES OF ANY
              KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Merchantability or fitness for a particular purpose</li>
              <li>Accuracy, reliability, or completeness of any data or content</li>
              <li>Uninterrupted or error-free operation</li>
              <li>Security of data transmission or storage</li>
            </ul>
            <p className="text-slate-600 leading-relaxed mt-3">
              We do not guarantee continuous, uninterrupted access to the Service, and operation
              may be interfered with by factors outside our control.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              10. Limitation of Liability
            </h2>
            <p className="text-slate-600 leading-relaxed">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, LEDGI SHALL NOT BE LIABLE FOR ANY
              INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING
              BUT NOT LIMITED TO LOSS OF PROFITS, DATA, OR USE, ARISING OUT OF OR RELATED
              TO YOUR USE OF THE SERVICE. OUR TOTAL LIABILITY SHALL NOT EXCEED THE AMOUNT
              YOU PAID TO US, IF ANY, IN THE TWELVE MONTHS PRECEDING THE CLAIM.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              11. Indemnification
            </h2>
            <p className="text-slate-600 leading-relaxed">
              You agree to indemnify and hold harmless Ledgi, its officers, directors,
              employees, and agents from any claims, damages, losses, or expenses (including
              reasonable attorneys&apos; fees) arising from your use of the Service, violation
              of these Terms, or infringement of any third-party rights.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              12. Termination
            </h2>
            <p className="text-slate-600 leading-relaxed">
              We may suspend or terminate your access to the Service at any time, with or
              without cause, and with or without notice. You may stop using the Service at
              any time by disconnecting your financial institutions and ceasing to use your
              account. Upon termination, your right to use the Service will immediately cease.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              13. Privacy
            </h2>
            <p className="text-slate-600 leading-relaxed">
              Your use of the Service is also governed by our{' '}
              <Link href="/privacy" className="text-slate-800 underline hover:text-slate-600">
                Privacy Policy
              </Link>
              , which describes how we collect, use, and protect your information.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              14. Governing Law
            </h2>
            <p className="text-slate-600 leading-relaxed">
              These Terms shall be governed by and construed in accordance with the laws of
              the State of California, without regard to its conflict of law provisions.
              Any disputes arising from these Terms or the Service shall be resolved in
              the courts located in San Francisco County, California.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              15. Changes to Terms
            </h2>
            <p className="text-slate-600 leading-relaxed">
              We reserve the right to modify these Terms at any time. We will notify users
              of material changes by posting the updated Terms on this page and updating
              the &quot;Last updated&quot; date. Your continued use of the Service after changes
              are posted constitutes acceptance of the modified Terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              16. Contact Information
            </h2>
            <p className="text-slate-600 leading-relaxed">
              For questions about these Terms of Service, please contact us at oliveren88@gmail.com.
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
            <Link href="/privacy" className="text-slate-600 hover:text-slate-900">
              Privacy Policy
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
