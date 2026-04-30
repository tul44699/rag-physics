import {
	useCallback,
	useEffect,
	useState,
	type FormEvent,
	type KeyboardEvent,
	type MutableRefObject,
} from "react";
import { useConversation } from "../../context/ConversationContext";
import {
	useGeneratedContent,
	parseFlashcards,
	type FlashcardDeck,
	type GeneratedItem,
} from "../../context/GeneratedContentContext";
import { useProfile } from "../../context/ProfileContext";
import { useTextbook } from "../../context/TextbookContext";
import type { Task } from "../../api/types";
import styles from "./ChatInput.module.css";

interface Props {
	task: Task;
	autoPrompt?: string;
	autoSend?: boolean;
	hasAutoSentRef: MutableRefObject<boolean>;
	onAutoSent: () => void;
	pageStart?: number | null;
	pageEnd?: number | null;
}

export default function ChatInput({
	task,
	autoPrompt,
	autoSend,
	hasAutoSentRef,
	onAutoSent,
	pageStart,
	pageEnd,
}: Props) {
	const [text, setText] = useState("");
	const { isLoading, sendMessage } = useConversation();
	const { addFlashcards, addStudyGuide, addChapterSummary } =
		useGeneratedContent();
	const { profile, logEvent } = useProfile();
	const { currentTextbookId, currentPage, currentChapter } = useTextbook();

	const doSend = useCallback(
		async (prompt: string) => {
			if (!prompt || isLoading) return;
			const ids = currentTextbookId ? [currentTextbookId] : [];
			const level = (profile?.understanding_level as string) || null;
			const fullPrompt = currentTextbookId
				? `[Reading textbook #${currentTextbookId}, page ${currentPage}] ${prompt}`
				: prompt;
			setText("");
			const result = await sendMessage(
				fullPrompt,
				task,
				ids,
				level,
				pageStart,
				pageEnd,
			);
			if (result && currentTextbookId) {
				const now = Date.now();
				const itemId = crypto.randomUUID();
				if (task === "flashcards") {
					const parsed = parseFlashcards(result.parsed);
					if (parsed)
						addFlashcards(currentTextbookId, {
							id: itemId,
							cards: parsed.cards,
							timestamp: now,
						});
				} else if (task === "study_guide") {
					addStudyGuide(currentTextbookId, {
						id: itemId,
						content: result.answer,
						timestamp: now,
					});
				} else if (task === "chapter_summary") {
					addChapterSummary(currentTextbookId, {
						id: itemId,
						content: result.answer,
						timestamp: now,
					});
				}
				const eventMap: Record<string, string> = {
					flashcards: "flashcard_generated",
					study_guide: "study_guide_generated",
					chapter_summary: "chapter_summary_generated",
				};
				logEvent({
					event_type: eventMap[task] || "question_asked",
					textbook_id: currentTextbookId,
					chapter: currentChapter,
					minutes_spent: 0,
				});
			}
		},
		[
			task,
			isLoading,
			profile,
			currentTextbookId,
			currentPage,
			currentChapter,
			sendMessage,
			addFlashcards,
			addStudyGuide,
			addChapterSummary,
			logEvent,
			pageStart,
			pageEnd,
		],
	);

	useEffect(() => {
		if (autoSend && autoPrompt && !hasAutoSentRef.current) {
			hasAutoSentRef.current = true;
			doSend(autoPrompt).then(() => onAutoSent());
		}
	}, [autoSend, autoPrompt, doSend, onAutoSent, hasAutoSentRef]);

	const isAuto = !!autoPrompt;

	const handleSend = useCallback(async () => {
		if (isAuto) return;
		await doSend(text.trim());
	}, [isAuto, text, doSend]);

	const handleKeyDown = useCallback(
		(e: KeyboardEvent<HTMLTextAreaElement>) => {
			if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
				e.preventDefault();
				handleSend();
			}
		},
		[handleSend],
	);

	return (
		<form
			className={styles.form}
			onSubmit={(e: FormEvent) => {
				e.preventDefault();
				handleSend();
			}}
		>
			{isAuto ? (
				<div className={styles.autoPrompt}>
					{isLoading ? "Generating..." : autoPrompt}
				</div>
			) : (
				<textarea
					className={styles.textarea}
					rows={2}
					placeholder={
						task === "qa"
							? "Ask a physics question..."
							: "Or type a custom prompt..."
					}
					value={text}
					onChange={(e) => setText(e.target.value)}
					onKeyDown={handleKeyDown}
					disabled={isLoading}
				/>
			)}
			{!isAuto && (
				<button
					type="submit"
					className={styles.sendBtn}
					disabled={!text.trim() || isLoading}
				>
					{isLoading ? "..." : "Send"}
				</button>
			)}
		</form>
	);
}
