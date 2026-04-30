import {
	createContext,
	useCallback,
	useContext,
	useState,
	type ReactNode,
} from "react";

interface TextbookState {
	currentTextbookId: number | null;
	currentPage: number;
	currentChapter: string | null;
	setTextbook: (id: number | null) => void;
	setPage: (page: number) => void;
	setChapter: (chapter: string | null) => void;
}

const TextbookContext = createContext<TextbookState | null>(null);

export function TextbookProvider({ children }: { children: ReactNode }) {
	const [currentTextbookId, setCurrentTextbookId] = useState<number | null>(
		null,
	);
	const [currentPage, setCurrentPage] = useState(1);
	const [currentChapter, setCurrentChapter] = useState<string | null>(null);

	const setTextbook = useCallback((id: number | null) => {
		setCurrentTextbookId(id);
		setCurrentPage(1);
		setCurrentChapter(null);
	}, []);

	const setPage = useCallback((page: number) => setCurrentPage(page), []);
	const setChapter = useCallback(
		(chapter: string | null) => setCurrentChapter(chapter),
		[],
	);

	return (
		<TextbookContext.Provider
			value={{
				currentTextbookId,
				currentPage,
				currentChapter,
				setTextbook,
				setPage,
				setChapter,
			}}
		>
			{children}
		</TextbookContext.Provider>
	);
}

export function useTextbook() {
	const ctx = useContext(TextbookContext);
	if (!ctx) throw new Error("useTextbook must be inside TextbookProvider");
	return ctx;
}
