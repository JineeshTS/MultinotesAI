import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import authService from '../../services/authService';

const VerifyEmail = () => {
  const { token } = useParams();
  const [status, setStatus] = useState('loading'); // loading, success, error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      try {
        await authService.verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been verified successfully!');
      } catch (error) {
        setStatus('error');
        setMessage(
          error.response?.data?.message ||
            'Failed to verify email. The link may be expired or invalid.'
        );
      }
    };

    verifyEmail();
  }, [token]);

  if (status === 'loading') {
    return (
      <div className="text-center space-y-6">
        <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto animate-pulse">
          <svg
            className="w-8 h-8 text-indigo-600 animate-spin"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Verifying your email...
          </h1>
          <p className="text-slate-600 mt-2">
            Please wait while we verify your email address.
          </p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="text-center space-y-6">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
          <CheckCircleIcon className="w-8 h-8 text-green-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Email verified!</h1>
          <p className="text-slate-600 mt-2">{message}</p>
        </div>
        <Link to="/login" className="btn-primary inline-block px-8 py-3">
          Continue to login
        </Link>
      </div>
    );
  }

  return (
    <div className="text-center space-y-6">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
        <XCircleIcon className="w-8 h-8 text-red-600" />
      </div>
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Verification failed
        </h1>
        <p className="text-slate-600 mt-2">{message}</p>
      </div>
      <div className="space-y-3">
        <Link to="/login" className="btn-primary inline-block px-8 py-3">
          Go to login
        </Link>
        <p className="text-sm text-slate-500">
          Need help?{' '}
          <a
            href="mailto:support@multinotes.ai"
            className="text-indigo-600 hover:text-indigo-700"
          >
            Contact support
          </a>
        </p>
      </div>
    </div>
  );
};

export default VerifyEmail;
