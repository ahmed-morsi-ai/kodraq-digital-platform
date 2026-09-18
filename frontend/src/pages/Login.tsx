export default function Login() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-sm border border-gray-100">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">Sign in to your account</h2>
        </div>
        {/* Auth form placeholder */}
        <div className="text-center text-sm text-gray-500 border-2 border-dashed border-gray-200 p-6 rounded-md">
          Authentication Form Placeholder
        </div>
      </div>
    </div>
  );
}
