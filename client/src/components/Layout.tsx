import type { ReactNode } from "react";
import Sidebar from "./Sidebar/Sidebar";
import styles from "./Layout.module.css";

export default function Layout({ children }: { children: ReactNode }) {
	return (
		<div className={styles.layout}>
			<main className={styles.main}>{children}</main>
			<aside className={styles.sidebar}>
				<Sidebar />
			</aside>
		</div>
	);
}
