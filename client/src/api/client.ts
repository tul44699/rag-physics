import type {
	Textbook,
	TextbookDetail,
	TextChunk,
	AskRequest,
	AskResponse,
	FormulaSheetResponse,
} from "./types";

const BASE = "";

function getToken(): string | null {
	return localStorage.getItem("token");
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const token = getToken();
	const headers: Record<string, string> = {
		"Content-Type": "application/json",
		...(options?.headers as Record<string, string>),
	};
	if (token) {
		headers["Authorization"] = `Bearer ${token}`;
	}
	const res = await fetch(`${BASE}${path}`, { ...options, headers });
	if (res.status === 401) {
		localStorage.removeItem("token");
		window.location.href = "/login";
		throw new Error("Unauthorized");
	}
	if (!res.ok) {
		const body = await res.text();
		throw new Error(`API ${res.status}: ${body}`);
	}
	return res.json();
}

export const api = {
	getTextbooks: () => request<Textbook[]>("/api/textbooks"),

	getTextbook: (id: number) => request<TextbookDetail>(`/api/textbooks/${id}`),

	getTextbookPdfUrl: (id: number) => `${BASE}/api/textbooks/${id}/pdf`,

	getTextbookChunks: (
		id: number,
		params?: { chapter?: string; page?: number },
	) => {
		const qs = new URLSearchParams();
		if (params?.chapter) qs.set("chapter", params.chapter);
		if (params?.page != null) qs.set("page", String(params.page));
		return request<TextChunk[]>(`/api/textbooks/${id}/chunks?${qs}`);
	},

	getProfile: () =>
		request<{ profile: Record<string, unknown> }>("/api/profile"),

	updateProfile: (profile: Record<string, unknown>) =>
		request("/api/profile", {
			method: "PUT",
			body: JSON.stringify({ profile }),
		}),

	createEvent: (event: {
		event_type: string;
		chapter?: string | null;
		textbook_id?: number | null;
		minutes_spent?: number;
		score?: number | null;
	}) =>
		request("/api/events", {
			method: "POST",
			body: JSON.stringify(event),
		}),

	ask: (req: AskRequest) =>
		request<AskResponse>("/api/ask", {
			method: "POST",
			body: JSON.stringify(req),
		}),

	deleteTextbook: (id: number) =>
		request(`/api/textbooks/${id}`, { method: "DELETE" }),

	generateFormulaSheet: (params: {
		textbookIds: number[];
		chapter?: string | null;
		pageStart?: number | null;
		pageEnd?: number | null;
	}) =>
		request<FormulaSheetResponse>("/api/formulasheet", {
			method: "POST",
			body: JSON.stringify({
				textbook_ids: params.textbookIds,
				chapter: params.chapter ?? null,
				page_start: params.pageStart ?? null,
				page_end: params.pageEnd ?? null,
			}),
		}),
};
