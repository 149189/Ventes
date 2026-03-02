import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100">
      <div className="text-center max-w-2xl px-6">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Sales<span className="text-primary-600">Count</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          AI-powered WhatsApp sales conversations that convert.
          Onboard, engage, and track — all in one platform.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/login" className="btn-primary text-lg px-8 py-3">
            Log In
          </Link>
          <Link href="/register" className="btn-secondary text-lg px-8 py-3">
            Get Started
          </Link>
        </div>
      </div>
    </div>
  );
}
