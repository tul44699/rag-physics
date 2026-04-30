import {
	createContext,
	useCallback,
	useContext,
	useRef,
	useState,
	type ReactNode,
} from "react";
import type { AskResponse, Message, Task } from "../api/types";

interface ConversationState {
	conversationId: string;
	messages: Message[];
	isLoading: boolean;
	error: string | null;
	sendMessage: (
		prompt: string,
		task: Task,
		textbookIds: number[],
		understandingLevel: string | null,
		pageStart?: number | null,
		pageEnd?: number | null,
	) => Promise<AskResponse | null>;
	clearError: () => void;
}

const ConversationContext = createContext<ConversationState | null>(null);

function makeId() {
	return crypto.randomUUID();
}

export function ConversationProvider({ children }: { children: ReactNode }) {
	const [messages, setMessages] = useState<Message[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const conversationIdRef = useRef(makeId());

	const sendMessage = useCallback(
		async (
			prompt: string,
			task: Task,
			textbookIds: number[],
			understandingLevel: string | null,
			pageStart?: number | null,
			pageEnd?: number | null,
		): Promise<AskResponse | null> => {
			const userMsg: Message = {
				id: crypto.randomUUID(),
				role: "user",
				content: prompt,
				task,
			};
			setMessages((prev) => [...prev, userMsg]);
			setIsLoading(true);
			setError(null);

			try {
				const token = localStorage.getItem("token");
				const res = await fetch("/api/ask", {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...(token ? { Authorization: `Bearer ${token}` } : {}),
					},
					body: JSON.stringify({
						conversation_id: conversationIdRef.current,
						prompt,
						task,
						textbook_ids: textbookIds,
						understanding_level: understandingLevel,
						page_start: pageStart ?? null,
						page_end: pageEnd ?? null,
					}),
				});
				if (res.status === 401) {
					localStorage.removeItem("token");
					window.location.href = "/login";
					throw new Error("Unauthorized");
				}
				if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
				const response: AskResponse = await res.json();
				const assistantMsg: Message = {
					id: crypto.randomUUID(),
					role: "assistant",
					content: response.answer,
					sources: response.sources,
					task,
					parsed: response.parsed,
				};
				setMessages((prev) => [...prev, assistantMsg]);
				setIsLoading(false);
				return response;
			} catch (e) {
				setError(e instanceof Error ? e.message : "Unknown error");
				setIsLoading(false);
				return null;
			}
		},
		[],
	);

	const clearError = useCallback(() => setError(null), []);

	return (
		<ConversationContext.Provider
			value={{
				conversationId: conversationIdRef.current,
				messages,
				isLoading,
				error,
				sendMessage,
				clearError,
			}}
		>
			{children}
		</ConversationContext.Provider>
	);
}

export function useConversation() {
	const ctx = useContext(ConversationContext);
	if (!ctx)
		throw new Error("useConversation must be inside ConversationProvider");
	return ctx;
}
