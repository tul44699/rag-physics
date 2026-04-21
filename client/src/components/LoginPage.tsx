import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './LoginPage.module.css';

export default function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (isRegister) {
        await register(email, password, displayName || undefined);
      } else {
        await login(email, password);
      }
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <form className={styles.form} onSubmit={handleSubmit}>
        <h1 className={styles.title}>Physics RAG</h1>
        <p className={styles.subtitle}>
          {isRegister ? 'Create an account' : 'Sign in to continue'}
        </p>

        {error && <div className={styles.error}>{error}</div>}

        <label className={styles.field}>
          Email
          <input
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </label>

        <label className={styles.field}>
          Password
          <input
            type="password"
            className={styles.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </label>

        {isRegister && (
          <label className={styles.field}>
            Display Name
            <input
              type="text"
              className={styles.input}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Optional"
            />
          </label>
        )}

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? 'Please wait...' : isRegister ? 'Create Account' : 'Sign In'}
        </button>

        <button
          type="button"
          className={styles.toggle}
          onClick={() => { setIsRegister(!isRegister); setError(null); }}
        >
          {isRegister ? 'Already have an account? Sign in' : 'Need an account? Create one'}
        </button>
      </form>
    </div>
  );
}
