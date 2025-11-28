import { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import {
  CheckIcon,
  SparklesIcon,
  RocketLaunchIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    description: 'Perfect for getting started',
    icon: SparklesIcon,
    features: [
      '1,000 tokens/month',
      'Access to 3 AI models',
      '5GB storage',
      'Basic templates',
      'Email support',
    ],
    cta: 'Current Plan',
    popular: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 19,
    description: 'Best for professionals',
    icon: RocketLaunchIcon,
    features: [
      '50,000 tokens/month',
      'Access to all AI models',
      '50GB storage',
      'Premium templates',
      'Priority support',
      'API access',
      'Advanced analytics',
    ],
    cta: 'Upgrade to Pro',
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 99,
    description: 'For large teams and organizations',
    icon: BuildingOfficeIcon,
    features: [
      'Unlimited tokens',
      'All AI models + custom',
      'Unlimited storage',
      'Custom templates',
      'Dedicated support',
      'Full API access',
      'Team management',
      'SSO & SAML',
      'SLA guarantee',
    ],
    cta: 'Contact Sales',
    popular: false,
  },
];

const Subscription = () => {
  const { user } = useSelector((state) => state.auth);
  const [currentPlan, setCurrentPlan] = useState('free');
  const [billingCycle, setBillingCycle] = useState('monthly');

  useEffect(() => {
    // Get current plan from user data
    setCurrentPlan(user?.subscription?.plan || 'free');
  }, [user]);

  const handleUpgrade = (planId) => {
    if (planId === 'enterprise') {
      window.location.href = 'mailto:sales@multinotes.ai?subject=Enterprise Plan Inquiry';
      return;
    }
    // Handle Stripe checkout
    toast.info('Redirecting to payment...');
  };

  const handleCancelSubscription = () => {
    if (confirm('Are you sure you want to cancel your subscription?')) {
      toast.success('Subscription cancelled');
    }
  };

  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900">Current Plan</h2>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold text-indigo-600">
              {plans.find((p) => p.id === currentPlan)?.name || 'Free'}
            </p>
            <p className="text-sm text-slate-500 mt-1">
              Your plan renews on January 15, 2025
            </p>
          </div>
          {currentPlan !== 'free' && (
            <button
              onClick={handleCancelSubscription}
              className="text-sm text-red-600 hover:text-red-700"
            >
              Cancel Subscription
            </button>
          )}
        </div>
      </div>

      {/* Billing Cycle Toggle */}
      <div className="flex justify-center">
        <div className="inline-flex items-center p-1 bg-slate-100 rounded-lg">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingCycle === 'monthly'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingCycle('yearly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingCycle === 'yearly'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Yearly <span className="text-green-600 ml-1">Save 20%</span>
          </button>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`card relative ${
              plan.popular ? 'border-2 border-indigo-500' : ''
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-indigo-500 text-white text-xs font-medium rounded-full">
                Most Popular
              </div>
            )}

            <div className="p-6">
              <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center mb-4">
                <plan.icon className="w-6 h-6 text-indigo-600" />
              </div>

              <h3 className="text-xl font-bold text-slate-900">{plan.name}</h3>
              <p className="text-sm text-slate-500 mt-1">{plan.description}</p>

              <div className="mt-4">
                <span className="text-4xl font-bold text-slate-900">
                  ${billingCycle === 'yearly' ? Math.round(plan.price * 0.8) : plan.price}
                </span>
                {plan.price > 0 && (
                  <span className="text-slate-500">/month</span>
                )}
              </div>

              <ul className="mt-6 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <CheckIcon className="w-5 h-5 text-green-500 flex-shrink-0" />
                    <span className="text-sm text-slate-600">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleUpgrade(plan.id)}
                disabled={currentPlan === plan.id}
                className={`w-full mt-6 py-3 rounded-lg font-medium transition-colors ${
                  currentPlan === plan.id
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    : plan.popular
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {currentPlan === plan.id ? 'Current Plan' : plan.cta}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Frequently Asked Questions
        </h2>
        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-slate-900">
              Can I change plans at any time?
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Yes, you can upgrade or downgrade your plan at any time. Changes
              take effect immediately.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-slate-900">
              What happens to my data if I downgrade?
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Your data is preserved, but you may lose access to premium features.
              If you exceed storage limits, you wont be able to upload new files.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-slate-900">
              Do you offer refunds?
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              We offer a 14-day money-back guarantee for all paid plans.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Subscription;
