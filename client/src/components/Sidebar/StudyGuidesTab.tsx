import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {
	useGeneratedContent,
	type GeneratedItem,
} from "../../context/GeneratedContentContext";
import { useTextbook } from "../../context/TextbookContext";
import styles from "./FlashcardsTab.module.css";

export default function StudyGuidesTab() {
	const { currentTextbookId } = useTextbook();
	const { getForTextbook } = useGeneratedContent();
	if (!currentTextbookId)
		return (
			<p className={styles.empty}>Open a textbook to view study guides.</p>
		);
	const guides = getForTextbook(currentTextbookId).studyGuides;
	if (guides.length === 0)
		return (
			<p className={styles.empty}>
				No study guides yet. Use the <strong>Chat</strong> tab and select "Study
				Guide" to generate one.
			</p>
		);
	return <GeneratedList items={guides} />;
}

export function GeneratedList({ items }: { items: GeneratedItem[] }) {
	const [expanded, setExpanded] = useState<Set<string>>(new Set());
	const toggle = (id: string) =>
		setExpanded((prev) => {
			const n = new Set(prev);
			n.has(id) ? n.delete(id) : n.add(id);
			return n;
		});
	return (
		<div className={styles.list}>
			{items.map((item) => (
				<div key={item.id} className={styles.deckItem}>
					<button className={styles.deckHeader} onClick={() => toggle(item.id)}>
						<span className={styles.chevron}>
							{expanded.has(item.id) ? "▾" : "▸"}
						</span>
						<span>{new Date(item.timestamp).toLocaleTimeString()}</span>
					</button>
					{expanded.has(item.id) && (
						<div className={styles.markdownBody}>
							<ReactMarkdown
								remarkPlugins={[remarkGfm, remarkMath]}
								rehypePlugins={[rehypeKatex]}
							>
								{item.content}
							</ReactMarkdown>
						</div>
					)}
				</div>
			))}
		</div>
	);
}
