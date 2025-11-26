import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { toast } from 'react-toastify';
import { CameraIcon } from '@heroicons/react/24/outline';
import { updateUser } from '../../store/slices/authSlice';
import authService from '../../services/authService';

const profileSchema = Yup.object().shape({
  name: Yup.string().required('Name is required'),
  email: Yup.string().email('Invalid email').required('Email is required'),
  phone: Yup.string(),
  company: Yup.string(),
  bio: Yup.string().max(500, 'Bio must be less than 500 characters'),
});

const Profile = () => {
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (values) => {
    setIsLoading(true);
    try {
      const response = await authService.updateProfile(values);
      dispatch(updateUser(response));
      toast.success('Profile updated successfully');
    } catch (error) {
      toast.error(error.response?.data?.message || 'Failed to update profile');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="p-6 border-b border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900">Profile Information</h2>
        <p className="text-sm text-slate-500 mt-1">
          Update your personal details and public profile
        </p>
      </div>

      <div className="p-6">
        {/* Avatar Section */}
        <div className="flex items-center gap-6 mb-8">
          <div className="relative">
            <div className="w-24 h-24 bg-indigo-100 rounded-full flex items-center justify-center">
              {user?.avatar ? (
                <img
                  src={user.avatar}
                  alt={user.name}
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                <span className="text-3xl font-bold text-indigo-600">
                  {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                </span>
              )}
            </div>
            <button className="absolute bottom-0 right-0 p-2 bg-white rounded-full shadow-lg border border-slate-200 hover:bg-slate-50">
              <CameraIcon className="w-4 h-4 text-slate-600" />
            </button>
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{user?.name || 'User'}</h3>
            <p className="text-sm text-slate-500">{user?.email}</p>
            <button className="text-sm text-indigo-600 hover:text-indigo-700 mt-1">
              Change avatar
            </button>
          </div>
        </div>

        {/* Profile Form */}
        <Formik
          initialValues={{
            name: user?.name || '',
            email: user?.email || '',
            phone: user?.phone || '',
            company: user?.company || '',
            bio: user?.bio || '',
          }}
          validationSchema={profileSchema}
          onSubmit={handleSubmit}
          enableReinitialize
        >
          {({ errors, touched }) => (
            <Form className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label htmlFor="name" className="label">
                    Full Name
                  </label>
                  <Field
                    id="name"
                    name="name"
                    type="text"
                    className={`input ${
                      errors.name && touched.name ? 'input-error' : ''
                    }`}
                  />
                  {errors.name && touched.name && (
                    <p className="mt-1 text-sm text-red-500">{errors.name}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="email" className="label">
                    Email Address
                  </label>
                  <Field
                    id="email"
                    name="email"
                    type="email"
                    className={`input ${
                      errors.email && touched.email ? 'input-error' : ''
                    }`}
                  />
                  {errors.email && touched.email && (
                    <p className="mt-1 text-sm text-red-500">{errors.email}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="phone" className="label">
                    Phone Number
                  </label>
                  <Field
                    id="phone"
                    name="phone"
                    type="tel"
                    placeholder="+1 (555) 000-0000"
                    className="input"
                  />
                </div>

                <div>
                  <label htmlFor="company" className="label">
                    Company
                  </label>
                  <Field
                    id="company"
                    name="company"
                    type="text"
                    placeholder="Your company name"
                    className="input"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="bio" className="label">
                  Bio
                </label>
                <Field
                  as="textarea"
                  id="bio"
                  name="bio"
                  rows={4}
                  placeholder="Tell us a bit about yourself..."
                  className={`input resize-none ${
                    errors.bio && touched.bio ? 'input-error' : ''
                  }`}
                />
                {errors.bio && touched.bio && (
                  <p className="mt-1 text-sm text-red-500">{errors.bio}</p>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button type="button" className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="btn-primary"
                >
                  {isLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </Form>
          )}
        </Formik>
      </div>
    </div>
  );
};

export default Profile;
