import { useState, useRef, useEffect } from "react";
import styles from "./TextbookSearch.module.css";

interface SearchResult {
	id: string;
	chapter: string | null;
	section: string | null;
	chunk_type: string | null;
	page_start: number | null;
	snippet: string;
}

interface Props {
	textbookId: number;
	onNavigate: (page: number) => void;
}

const TYPE_ICONS: Record<string, string> = {
	equation: "#",
	definition: "D",
	derivation: "»",
	example: "Ex",
	text: "¶",
};

export default function TextbookSearch({ textbookId, onNavigate }: Props) {
	const [q, setQ] = useState("");
	const [results, setResults] = useState<SearchResult[]>([]);
	const [open, setOpen] = useState(false);
	const containerRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (!q.trim() || q.length < 2) {
			setResults([]);
			setOpen(false);
			return;
		}
		const timer = setTimeout(async () => {
			const res = await fetch(
				`/api/textbooks/${textbookId}/search?q=${encodeURIComponent(q)}&limit=8`,
				{
					headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
				},
			);
			if (res.ok) {
				const data = await res.json();
				setResults(data);
				setOpen(data.length > 0);
			}
		}, 250);
		return () => clearTimeout(timer);
	}, [q, textbookId]);

	useEffect(() => {
		const handleClick = (e: MouseEvent) => {
			if (
				containerRef.current &&
				!containerRef.current.contains(e.target as Node)
			) {
				setOpen(false);
			}
		};
		document.addEventListener("mousedown", handleClick);
		return () => document.removeEventListener("mousedown", handleClick);
	}, []);

	return (
		<div className={styles.container} ref={containerRef}>
			<input
				className={styles.input}
				type="text"
				placeholder="Search in textbook..."
				value={q}
				onChange={(e) => setQ(e.target.value)}
			/>
			{open && results.length > 0 && (
				<div className={styles.dropdown}>
					{results.map((r, i) => (
						<button
							key={i}
							className={styles.item}
							onClick={() => {
								if (r.page_start != null) onNavigate(r.page_start);
								setOpen(false);
								setQ("");
							}}
						>
							<span className={styles.icon}>
								{TYPE_ICONS[r.chunk_type || "text"] || "¶"}
							</span>
							<span className={styles.snippet}>
								{r.section ? `§${r.section} ` : ""}p.{r.page_start}:{" "}
								{r.snippet.slice(0, 100)}
							</span>
						</button>
					))}
				</div>
			)}
		</div>
	);
}
