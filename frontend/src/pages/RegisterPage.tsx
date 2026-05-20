import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { TrendingUp, Eye, EyeOff, User, Mail, Lock } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { api } from '../store';

const schema = z.object({
  email:     z.string().email('Valid email required'),
  username:  z.string().min(3, 'At least 3 chars').max(50).regex(/^[a-zA-Z0-9_]+$/, 'Letters, numbers, _ only'),
  full_name: z.string().optional(),
  password:  z.string().min(8, 'At least 8 characters'),
  confirm:   z.string(),
}).refine(d => d.password === d.confirm, { message: "Passwords don't match", path: ['confirm'] });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const [showPw, setShowPw] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      await api.post('/auth/register', {
        email: data.email, username: data.username,
        password: data.password, full_name: data.full_name,
      });
      toast.success('Account created — please sign in');
      navigate('/login');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Registration failed');
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary bg-grid-pattern bg-grid flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-accent-cyan/20 border border-accent-cyan/40 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-accent-cyan" />
          </div>
          <span className="font-display font-bold text-xl">CryptoBot <span className="text-accent-cyan">Pro</span></span>
        </div>

        <div className="card p-8">
          <div className="mb-6">
            <h1 className="font-display font-bold text-2xl text-text-primary">Create account</h1>
            <p className="text-text-secondary text-sm mt-1">Start trading smarter today</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Full Name <span className="text-text-muted normal-case">(optional)</span></label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input {...register('full_name')} className="input pl-9" placeholder="Jane Doe" />
              </div>
            </div>
            <div>
              <label className="label">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input {...register('email')} type="email" className="input pl-9" placeholder="you@example.com" />
              </div>
              {errors.email && <p className="text-accent-red text-xs mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <label className="label">Username</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">@</span>
                <input {...register('username')} className="input pl-7" placeholder="trader_pro" />
              </div>
              {errors.username && <p className="text-accent-red text-xs mt-1">{errors.username.message}</p>}
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input {...register('password')} type={showPw ? 'text' : 'password'} className="input pl-9 pr-10" placeholder="Min. 8 characters" />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-accent-red text-xs mt-1">{errors.password.message}</p>}
            </div>
            <div>
              <label className="label">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input {...register('confirm')} type="password" className="input pl-9" placeholder="Repeat password" />
              </div>
              {errors.confirm && <p className="text-accent-red text-xs mt-1">{errors.confirm.message}</p>}
            </div>

            <button type="submit" disabled={isSubmitting} className="btn-primary w-full mt-6 flex items-center justify-center gap-2 h-11">
              {isSubmitting ? <span className="w-4 h-4 border-2 border-bg-primary/30 border-t-bg-primary rounded-full animate-spin" /> : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-text-muted text-sm mt-6">
            Already have an account? <Link to="/login" className="text-accent-cyan hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
