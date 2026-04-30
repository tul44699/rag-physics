import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {
	useGeneratedContent,
	type FlashcardDeck,
	type Flashcard,
} from "../../context/GeneratedContentContext";
import { useTextbook } from "../../context/TextbookContext";
import styles from "./FlashcardsTab.module.css";

export default function FlashcardsTab() {
	const { currentTextbookId } = useTextbook();
	const { getForTextbook } = useGeneratedContent();
	const [expanded, setExpanded] = useState<Set<string>>(new Set());

	if (!currentTextbookId) {
		return <p className={styles.empty}>Open a textbook to view flashcards.</p>;
	}

	const decks = getForTextbook(currentTextbookId).flashcards;

	if (decks.length === 0) {
		return (
			<p className={styles.empty}>
				No flashcards yet. Use the <strong>Chat</strong> tab and select
				"Flashcards" as the task type to generate some.
			</p>
		);
	}

	const toggle = (id: string) => {
		setExpanded((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	};

	return (
		<div className={styles.list}>
			{decks.map((deck) => (
				<div key={deck.id} className={styles.deckItem}>
					<button className={styles.deckHeader} onClick={() => toggle(deck.id)}>
						<span className={styles.chevron}>
							{expanded.has(deck.id) ? "▾" : "▸"}
						</span>
						<span>{deck.cards.length} cards</span>
						<span className={styles.time}>
							{new Date(deck.timestamp).toLocaleTimeString()}
						</span>
					</button>
					{expanded.has(deck.id) && (
						<div className={styles.cards}>
							{deck.cards.map((card, i) => (
								<FlashcardItem key={i} index={i} card={card} />
							))}
						</div>
					)}
				</div>
			))}
		</div>
	);
}

function FlashcardItem({ index, card }: { index: number; card: Flashcard }) {
	const [flipped, setFlipped] = useState(false);

	return (
		<div
			className={`${styles.card} ${flipped ? styles.flipped : ""}`}
			onClick={() => setFlipped((f) => !f)}
		>
			<div className={styles.cardInner}>
				<div className={styles.cardFront}>
					<span className={styles.cardLabel}>Q{index + 1}</span>
					<div className={styles.cardContent}>
						<ReactMarkdown
							remarkPlugins={[remarkMath]}
							rehypePlugins={[rehypeKatex]}
						>
							{card.front}
						</ReactMarkdown>
					</div>
				</div>
				<div className={styles.cardBack}>
					<span className={styles.cardLabel}>A{index + 1}</span>
					<div className={styles.cardContent}>
						<ReactMarkdown
							remarkPlugins={[remarkMath]}
							rehypePlugins={[rehypeKatex]}
						>
							{card.back}
						</ReactMarkdown>
					</div>
				</div>
			</div>
		</div>
	);
}
