import styles from "./SidebarTabs.module.css";

export type TabId =
	| "chat"
	| "flashcards"
	| "studyGuides"
	| "summaries"
	| "formulas";

interface Tab {
	id: TabId;
	label: string;
	badge?: number;
}

interface Props {
	active: TabId;
	tabs: Tab[];
	onChange: (id: TabId) => void;
}

export default function SidebarTabs({ active, tabs, onChange }: Props) {
	return (
		<div className={styles.tabBar}>
			{tabs.map((tab) => (
				<button
					key={tab.id}
					className={`${styles.tab} ${active === tab.id ? styles.active : ""}`}
					onClick={() => onChange(tab.id)}
				>
					{tab.label}
					{tab.badge != null && tab.badge > 0 && (
						<span className={styles.badge}>{tab.badge}</span>
					)}
				</button>
			))}
		</div>
	);
}
