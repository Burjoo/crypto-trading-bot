import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { TrendingUp, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { api, useAuthStore } from '../store';

const schema = z.object({
  username: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      const form = new URLSearchParams();
      form.append('username', data.username);
      form.append('password', data.password);

      const res = await api.post('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      setTokens(res.data.access_token, res.data.refresh_token);
      setUser(res.data.user);
      toast.success(`Welcome back, ${res.data.user.username}!`);
      navigate('/');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Login failed');
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary bg-grid-pattern bg-grid flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-accent-cyan/20 border border-accent-cyan/40 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-accent-cyan" />
          </div>
          <span className="font-display font-bold text-xl">
            CryptoBot <span className="text-accent-cyan">Pro</span>
          </span>
        </div>

        <div className="card p-8">
          <div className="mb-6">
            <h1 className="font-display font-bold text-2xl text-text-primary">Welcome back</h1>
            <p className="text-text-secondary text-sm mt-1">Sign in to your trading dashboard</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Email or Username</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input
                  {...register('username')}
                  className="input pl-9"
                  placeholder="trader@example.com"
                />
              </div>
              {errors.username && <p className="text-accent-red text-xs mt-1">{errors.username.message}</p>}
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  className="input pl-9 pr-10"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-accent-red text-xs mt-1">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full mt-6 flex items-center justify-center gap-2 h-11"
            >
              {isSubmitting ? (
                <span className="w-4 h-4 border-2 border-bg-primary/30 border-t-bg-primary rounded-full animate-spin" />
              ) : 'Sign In'}
            </button>
          </form>

          <p className="text-center text-text-muted text-sm mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-accent-cyan hover:underline">Create one</Link>
          </p>
        </div>

        {/* Demo hint */}
        <div className="mt-4 p-3 rounded-lg border border-accent-yellow/20 bg-accent-yellow/5 text-center">
          <p className="text-accent-yellow text-xs">
            Demo: <span className="font-mono">admin@cryptobot.pro</span> / <span className="font-mono">changeme123!</span>
          </p>
        </div>
      </div>
    </div>
  );
}
