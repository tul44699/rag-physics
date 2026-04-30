import { useGeneratedContent } from "../../context/GeneratedContentContext";
import { useTextbook } from "../../context/TextbookContext";
import { GeneratedList } from "./StudyGuidesTab";
import styles from "./FlashcardsTab.module.css";

export default function SummariesTab() {
	const { currentTextbookId } = useTextbook();
	const { getForTextbook } = useGeneratedContent();
	if (!currentTextbookId)
		return (
			<p className={styles.empty}>Open a textbook to view chapter summaries.</p>
		);
	const summaries = getForTextbook(currentTextbookId).chapterSummaries;
	if (summaries.length === 0)
		return (
			<p className={styles.empty}>
				No summaries yet. Use the <strong>Chat</strong> tab and select "Chapter
				Summary" to generate one.
			</p>
		);
	return <GeneratedList items={summaries} />;
}
