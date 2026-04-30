import type { Task } from "../../api/types";
import styles from "./TaskButtons.module.css";

const TASKS: { key: Task; label: string }[] = [
	{ key: "qa", label: "Explain" },
	{ key: "lookup", label: "Lookup" },
	{ key: "flashcards", label: "Flashcards" },
	{ key: "study_guide", label: "Study Guide" },
	{ key: "chapter_summary", label: "Chapter Summary" },
];

interface Props {
	active: Task;
	onChange: (task: Task) => void;
}

export default function TaskButtons({ active, onChange }: Props) {
	return (
		<div className={styles.row}>
			{TASKS.map((t) => (
				<button
					key={t.key}
					className={`${styles.btn} ${active === t.key ? styles.active : ""}`}
					onClick={() => onChange(t.key)}
				>
					{t.label}
				</button>
			))}
		</div>
	);
}
