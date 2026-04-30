import { useEffect, useRef } from "react";
import { useConversation } from "../../context/ConversationContext";
import MessageBubble from "./MessageBubble";
import styles from "./ConversationThread.module.css";

export default function ConversationThread() {
	const { messages, isLoading, error, clearError } = useConversation();
	const bottomRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [messages, isLoading]);

	return (
		<div className={styles.thread}>
			{messages.length === 0 && !isLoading && (
				<p className={styles.empty}>
					Ask a question about your physics textbook to get started.
				</p>
			)}
			{messages.map((msg) => (
				<MessageBubble key={msg.id} message={msg} />
			))}
			{isLoading && (
				<div className={styles.loading}>
					<span className={styles.dot} />
				</div>
			)}
			{error && (
				<div className={styles.error}>
					<span>Failed: {error}</span>
					<button onClick={clearError} className={styles.retry}>
						Dismiss
					</button>
				</div>
			)}
			<div ref={bottomRef} />
		</div>
	);
}
