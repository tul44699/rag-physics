import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useGeneratedContent } from "../../context/GeneratedContentContext";
import { useTextbook } from "../../context/TextbookContext";
import { renderLatex } from "../../utils/katex";
import type { FormulaSheetItem, Chapter } from "../../api/types";
import styles from "./FormulasTab.module.css";

export default function FormulasTab() {
	const { currentTextbookId } = useTextbook();
	const { getForTextbook, setFormulaSheet } = useGeneratedContent();
	const [chapters, setChapters] = useState<Chapter[]>([]);
	const [chapterFromIdx, setChapterFromIdx] = useState<number>(-1);
	const [chapterToIdx, setChapterToIdx] = useState<number>(-1);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!currentTextbookId) return;
		api
			.getTextbook(currentTextbookId)
			.then((tb) => setChapters(tb.chapters ?? []))
			.catch(() => setChapters([]));
	}, [currentTextbookId]);

	if (!currentTextbookId)
		return <p className={styles.empty}>Open a textbook to view formulas.</p>;

	const sheet = getForTextbook(currentTextbookId).formulaSheet;

	const generate = async () => {
		setLoading(true);
		setError(null);
		try {
			const fromCh = chapterFromIdx >= 0 ? chapters[chapterFromIdx] : null;
			const toCh = chapterToIdx >= 0 ? chapters[chapterToIdx] : null;
			const data = await api.generateFormulaSheet({
				textbookIds: [currentTextbookId],
				pageStart: fromCh?.page_start ?? null,
				pageEnd: toCh ? (toCh.page_end ?? toCh.page_start) : null,
			});
			setFormulaSheet(currentTextbookId, {
				sections: data.sections ?? {},
				chapterOrder: data.chapter_order ?? [],
				section_order: data.section_order ?? {},
			});
		} catch (e) {
			setError(e instanceof Error ? e.message : "Failed");
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className={styles.container}>
			<div className={styles.controls}>
				<select
					value={chapterFromIdx}
					onChange={(e) => setChapterFromIdx(Number(e.target.value))}
				>
					<option value={-1}>From...</option>
					{chapters.map((ch, i) => (
						<option key={ch.id} value={i}>
							{ch.title}
						</option>
					))}
				</select>
				<select
					value={chapterToIdx}
					onChange={(e) => setChapterToIdx(Number(e.target.value))}
				>
					<option value={-1}>To...</option>
					{chapters.map((ch, i) => (
						<option key={ch.id} value={i}>
							{ch.title}
						</option>
					))}
				</select>
				<button className={styles.btn} onClick={generate} disabled={loading}>
					{loading ? "..." : "Generate"}
				</button>
			</div>
			{error && <p className={styles.error}>{error}</p>}
			{sheet ? (
				sheet.chapterOrder.length === 0 ? (
					<p className={styles.empty}>No formulas found.</p>
				) : (
					sheet.chapterOrder.map((ch) => {
						const secMap = sheet.sections[ch];
						if (!secMap || Object.keys(secMap).length === 0) return null;
						const secOrder = sheet.section_order?.[ch] ?? Object.keys(secMap);
						return (
							<div key={ch} className={styles.chapter}>
								<h3 className={styles.chapterTitle}>{ch}</h3>
								{secOrder.map((sec) => {
									const eqs = secMap[sec];
									if (!eqs?.length) return null;
									return (
										<div key={sec} className={styles.section}>
											{sec !== "General" && (
												<h4 className={styles.sectionTitle}>{sec}</h4>
											)}
											{eqs.map((eq, i) => (
												<FormulaItem key={i} eq={eq} />
											))}
										</div>
									);
								})}
							</div>
						);
					})
				)
			) : (
				<p className={styles.empty}>
					Select a chapter range and click Generate.
				</p>
			)}
		</div>
	);
}

function FormulaItem({ eq }: { eq: FormulaSheetItem }) {
	const html = eq.latex ? renderLatex(eq.latex) : null;
	return (
		<div className={styles.item}>
			<span className={styles.itemText}>
				{html ? (
					<span dangerouslySetInnerHTML={{ __html: html }} />
				) : (
					<code>{eq.plain_text}</code>
				)}
			</span>
			{eq.page_start != null && (
				<span className={styles.pageNum}>p.{eq.page_start}</span>
			)}
		</div>
	);
}
