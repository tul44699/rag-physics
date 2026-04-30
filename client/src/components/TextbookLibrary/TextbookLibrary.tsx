import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Textbook } from "../../api/types";
import styles from "./TextbookLibrary.module.css";

export default function TextbookLibrary() {
	const [textbooks, setTextbooks] = useState<Textbook[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchBooks = () => {
		setLoading(true);
		setError(null);
		fetch("/api/textbooks", {
			headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
		})
			.then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
			.then(setTextbooks)
			.catch(() => setError("Failed to load textbooks"))
			.finally(() => setLoading(false));
	};

	useEffect(() => {
		fetchBooks();
	}, []);

	return (
		<div className={styles.page}>
			<div className={styles.header}>
				<h1 className={styles.title}>Physics Textbooks</h1>
				<p className={styles.subtitle}>
					Upload textbooks via the ingest API, then open one to read and ask the
					AI assistant questions.
				</p>
				<Link to="/formulasheet" className={styles.formulaLink}>
					Formula Sheet Generator
				</Link>
			</div>

			{loading && (
				<div className={styles.grid}>
					{Array.from({ length: 6 }).map((_, i) => (
						<div key={i} className={styles.skeleton} />
					))}
				</div>
			)}

			{error && (
				<div className={styles.error}>
					<span>{error}</span>
					<button onClick={fetchBooks} className={styles.retry}>
						Retry
					</button>
				</div>
			)}

			{!loading && !error && textbooks.length === 0 && (
				<div className={styles.empty}>
					<p>No textbooks found.</p>
					<p className={styles.emptyHint}>
						Use the CLI or POST /api/ingest/textbook to add a textbook PDF.
					</p>
				</div>
			)}

			{!loading && !error && textbooks.length > 0 && (
				<div className={styles.grid}>
					{textbooks.map((tb) => (
						<Link
							key={tb.id}
							to={`/textbooks/${tb.id}`}
							className={styles.card}
						>
							<h2 className={styles.cardTitle}>{tb.title}</h2>
							{tb.group_name && (
								<span className={styles.badge}>{tb.group_name}</span>
							)}
							<div className={styles.meta}>
								{tb.page_count != null && <span>{tb.page_count} pages</span>}
								{tb.chapter_count != null && (
									<span>{tb.chapter_count} chapters</span>
								)}
							</div>
							<div className={styles.date}>
								Added {new Date(tb.created_at).toLocaleDateString()}
							</div>
						</Link>
					))}
				</div>
			)}
		</div>
	);
}
