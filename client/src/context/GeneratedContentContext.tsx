import {
	createContext,
	useCallback,
	useContext,
	useState,
	type ReactNode,
} from "react";
import type { FormulaSheetItem } from "../api/types";

export interface Flashcard {
	front: string;
	back: string;
}

export function parseFlashcards(
	parsed: unknown,
): { cards: Flashcard[]; rest: string } | null {
	if (!parsed || !Array.isArray(parsed) || parsed.length === 0) return null;
	const cards = parsed as Flashcard[];
	if (!cards[0].front || !cards[0].back) return null;
	return { cards, rest: "" };
}

export interface FlashcardDeck {
	id: string;
	cards: Flashcard[];
	timestamp: number;
}

export interface GeneratedItem {
	id: string;
	content: string; // full markdown
	timestamp: number;
}

interface TextbookContent {
	flashcards: FlashcardDeck[];
	studyGuides: GeneratedItem[];
	chapterSummaries: GeneratedItem[];
	formulaSheet: {
		sections: Record<string, Record<string, FormulaSheetItem[]>>;
		chapterOrder: string[];
		section_order: Record<string, string[]>;
	} | null;
}

interface GeneratedContentState {
	contentByTextbook: Record<number, TextbookContent>;
	addFlashcards: (textbookId: number, deck: FlashcardDeck) => void;
	addStudyGuide: (textbookId: number, item: GeneratedItem) => void;
	addChapterSummary: (textbookId: number, item: GeneratedItem) => void;
	setFormulaSheet: (
		textbookId: number,
		sheet: TextbookContent["formulaSheet"],
	) => void;
	getForTextbook: (textbookId: number) => TextbookContent;
}

const GeneratedContentContext = createContext<GeneratedContentState | null>(
	null,
);

function emptyContent(): TextbookContent {
	return {
		flashcards: [],
		studyGuides: [],
		chapterSummaries: [],
		formulaSheet: null,
	};
}

export function GeneratedContentProvider({
	children,
}: {
	children: ReactNode;
}) {
	const [contentByTextbook, setContentByTextbook] = useState<
		Record<number, TextbookContent>
	>({});

	const getForTextbook = useCallback(
		(textbookId: number): TextbookContent =>
			contentByTextbook[textbookId] ?? emptyContent(),
		[contentByTextbook],
	);

	const addFlashcards = useCallback(
		(textbookId: number, deck: FlashcardDeck) => {
			setContentByTextbook((prev) => {
				const existing = prev[textbookId] ?? emptyContent();
				return {
					...prev,
					[textbookId]: {
						...existing,
						flashcards: [deck, ...existing.flashcards],
					},
				};
			});
		},
		[],
	);

	const addStudyGuide = useCallback(
		(textbookId: number, item: GeneratedItem) => {
			setContentByTextbook((prev) => {
				const existing = prev[textbookId] ?? emptyContent();
				return {
					...prev,
					[textbookId]: {
						...existing,
						studyGuides: [item, ...existing.studyGuides],
					},
				};
			});
		},
		[],
	);

	const addChapterSummary = useCallback(
		(textbookId: number, item: GeneratedItem) => {
			setContentByTextbook((prev) => {
				const existing = prev[textbookId] ?? emptyContent();
				return {
					...prev,
					[textbookId]: {
						...existing,
						chapterSummaries: [item, ...existing.chapterSummaries],
					},
				};
			});
		},
		[],
	);

	const setFormulaSheet = useCallback(
		(textbookId: number, sheet: TextbookContent["formulaSheet"]) => {
			setContentByTextbook((prev) => {
				const existing = prev[textbookId] ?? emptyContent();
				return { ...prev, [textbookId]: { ...existing, formulaSheet: sheet } };
			});
		},
		[],
	);

	return (
		<GeneratedContentContext.Provider
			value={{
				contentByTextbook,
				addFlashcards,
				addStudyGuide,
				addChapterSummary,
				setFormulaSheet,
				getForTextbook,
			}}
		>
			{children}
		</GeneratedContentContext.Provider>
	);
}

export function useGeneratedContent() {
	const ctx = useContext(GeneratedContentContext);
	if (!ctx)
		throw new Error(
			"useGeneratedContent must be inside GeneratedContentProvider",
		);
	return ctx;
}
