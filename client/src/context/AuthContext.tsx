import {
	createContext,
	useCallback,
	useContext,
	useEffect,
	useState,
	type ReactNode,
} from "react";

interface AuthUser {
	user_id: number;
	email: string | null;
	display_name: string | null;
}

interface AuthState {
	token: string | null;
	user: AuthUser | null;
	isLoading: boolean;
	login: (email: string, password: string) => Promise<void>;
	register: (
		email: string,
		password: string,
		displayName?: string,
	) => Promise<void>;
	logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function parseToken(token: string): AuthUser | null {
	try {
		const payload = JSON.parse(atob(token.split(".")[1]));
		if (payload.sub) {
			return {
				user_id: Number(payload.sub),
				email: payload.email || null,
				display_name: payload.display_name || null,
			};
		}
		return null;
	} catch {
		return null;
	}
}

export function AuthProvider({ children }: { children: ReactNode }) {
	const [token, setToken] = useState<string | null>(() =>
		localStorage.getItem("token"),
	);
	const [user, setUser] = useState<AuthUser | null>(() => {
		const t = localStorage.getItem("token");
		return t ? parseToken(t) : null;
	});
	const [isLoading, setIsLoading] = useState(true);

	useEffect(() => {
		setIsLoading(false);
	}, []);

	const login = useCallback(async (email: string, password: string) => {
		const res = await fetch("/api/auth/login", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email, password }),
		});
		if (!res.ok) {
			const data = await res.json().catch(() => ({}));
			throw new Error(data.detail || "Invalid email or password");
		}
		const data = await res.json();
		localStorage.setItem("token", data.token);
		setToken(data.token);
		setUser({
			user_id: data.user_id,
			email: data.email,
			display_name: data.display_name,
		});
	}, []);

	const register = useCallback(
		async (email: string, password: string, displayName?: string) => {
			const res = await fetch("/api/auth/register", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ email, password, display_name: displayName }),
			});
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail || "Registration failed");
			}
			const data = await res.json();
			localStorage.setItem("token", data.token);
			setToken(data.token);
			setUser({
				user_id: data.user_id,
				email: data.email,
				display_name: data.display_name,
			});
		},
		[],
	);

	const logout = useCallback(() => {
		localStorage.removeItem("token");
		setToken(null);
		setUser(null);
	}, []);

	return (
		<AuthContext.Provider
			value={{ token, user, isLoading, login, register, logout }}
		>
			{children}
		</AuthContext.Provider>
	);
}

export function useAuth() {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error("useAuth must be inside AuthProvider");
	return ctx;
}
