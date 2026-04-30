import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useProfile } from "../../context/ProfileContext";
import styles from "./ProfilePanel.module.css";

export default function ProfilePanel() {
	const { user, logout } = useAuth();
	const { profile, isLoading, loadProfile, saveProfile } = useProfile();
	const [open, setOpen] = useState(false);
	const [level, setLevel] = useState("intermediate");
	const [learningStyle, setLearningStyle] = useState("");
	const [course, setCourse] = useState("");

	// Auto-load profile on mount
	useEffect(() => {
		loadProfile();
	}, [loadProfile]);

	useEffect(() => {
		if (profile) {
			setLevel((profile.understanding_level as string) || "intermediate");
			setLearningStyle((profile.learning_style as string) || "");
			setCourse((profile.course as string) || "");
		}
	}, [profile]);

	const handleSave = useCallback(async () => {
		await saveProfile({
			understanding_level: level,
			learning_style: learningStyle,
			course,
		});
		setOpen(false);
	}, [level, learningStyle, course, saveProfile]);

	return (
		<div className={styles.panel}>
			<div className={styles.header}>
				<span className={styles.user}>{user?.email}</span>
				<span className={styles.levelBadge}>{level}</span>
				<button className={styles.editBtn} onClick={() => setOpen((v) => !v)}>
					{open ? "✕" : "Edit"}
				</button>
			</div>
			{open && (
				<div className={styles.body}>
					<label className={styles.field}>
						Level
						<select
							value={level}
							onChange={(e) => setLevel(e.target.value)}
							className={styles.input}
						>
							<option value="beginner">Beginner</option>
							<option value="intermediate">Intermediate</option>
							<option value="advanced">Advanced</option>
						</select>
					</label>
					<label className={styles.field}>
						Style
						<select
							value={learningStyle}
							onChange={(e) => setLearningStyle(e.target.value)}
							className={styles.input}
						>
							<option value="">Default</option>
							<option value="worked examples">Worked examples</option>
							<option value="visual">Visual descriptions</option>
							<option value="concise">Brief & direct</option>
						</select>
					</label>
					<label className={styles.field}>
						Course
						<input
							value={course}
							onChange={(e) => setCourse(e.target.value)}
							className={styles.input}
							placeholder="e.g. Physics II"
						/>
					</label>
					<div className={styles.actions}>
						<button
							className={styles.saveBtn}
							onClick={handleSave}
							disabled={isLoading}
						>
							{isLoading ? "Saving..." : "Save"}
						</button>
						<button className={styles.logoutBtn} onClick={logout}>
							Sign Out
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
