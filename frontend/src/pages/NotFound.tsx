import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
      <h2 className="text-4xl font-bold text-gray-900 mb-2">404</h2>
      <p className="text-gray-500 mb-6">The page you are looking for does not exist.</p>
      <Link to="/" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
        Return to Dashboard
      </Link>
    </div>
  );
}
