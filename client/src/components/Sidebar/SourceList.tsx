import { useNavigate } from 'react-router-dom';
import { useConversation } from '../../context/ConversationContext';
import { useTextbook } from '../../context/TextbookContext';
import styles from './SourceList.module.css';

export default function SourceList() {
  const { messages } = useConversation();
  const { currentTextbookId, setPage, setTextbook } = useTextbook();
  const navigate = useNavigate();

  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
  const sources = lastAssistant?.sources;

  if (!sources || sources.length === 0) return null;

  return (
    <div className={styles.panel}>
      <div className={styles.heading}>Sources</div>
      <ul className={styles.list}>
        {sources.map((s, i) => (
          <li key={i}>
            <button
              className={styles.item}
              onClick={() => {
                const page = s.page_start ?? 1;
                setPage(page);
                if (s.textbook_id != null && s.textbook_id !== currentTextbookId) {
                  setTextbook(s.textbook_id);
                  navigate(`/textbooks/${s.textbook_id}?page=${page}`);
                }
              }}
            >
              <span className={styles.idx}>[{i + 1}]</span>
              <div>
                <div className={styles.src}>
                  {s.textbook}
                  {s.chapter ? `, ${s.chapter}` : ''}
                  {s.page_start != null ? ` p.${s.page_start}` : ''}
                </div>
                <div className={styles.snippet}>{s.snippet}</div>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
