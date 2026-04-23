import { useEffect, useRef, useState } from 'react';
import type { Task, Chapter } from '../../api/types';
import { api } from '../../api/client';
import { useTextbook } from '../../context/TextbookContext';
import { useConversation } from '../../context/ConversationContext';
import ChatInput from './ChatInput';
import ConversationThread from './ConversationThread';
import SourceList from './SourceList';
import styles from './ChatTab.module.css';

const TASKS: { key: Task; label: string }[] = [
  { key: 'qa', label: 'Explain' },
  { key: 'lookup', label: 'Lookup' },
  { key: 'flashcards', label: 'Flashcards' },
  { key: 'study_guide', label: 'Study Guide' },
  { key: 'chapter_summary', label: 'Summary' },
];

const CHAPTER_TASKS: Task[] = ['flashcards', 'study_guide', 'chapter_summary'];

export default function ChatTab() {
  const [task, setTask] = useState<Task>('qa');
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [chFromIdx, setChFromIdx] = useState<number>(-1);
  const [chToIdx, setChToIdx] = useState<number>(-1);
  const { currentTextbookId } = useTextbook();
  const { isLoading } = useConversation();
  const autoSentRef = useRef(false);

  useEffect(() => {
    if (!currentTextbookId) return;
    api.getTextbook(currentTextbookId)
      .then((tb) => setChapters(tb.chapters ?? []))
      .catch(() => setChapters([]));
  }, [currentTextbookId]);

  const resetChapterRange = () => { setChFromIdx(-1); setChToIdx(-1); autoSentRef.current = false; };

  if (!currentTextbookId) {
    return <p className={styles.empty}>Open a textbook to start.</p>;
  }

  const showChapterSelect = CHAPTER_TASKS.includes(task);
  const fromCh = chFromIdx >= 0 ? chapters[chFromIdx] : null;
  const toCh = chToIdx >= 0 ? chapters[chToIdx] : null;
  const hasAutoRange = fromCh && toCh;

  const autoPrompt = hasAutoRange
    ? (() => {
        const range = chapters.slice(chFromIdx, chToIdx + 1);
        const list = range.map(ch => ch.title).join(', ');
        const prefix = task === 'flashcards'
          ? 'Create flashcards for these chapters:'
          : task === 'study_guide'
          ? 'Create a study guide covering each of these chapters:'
          : 'Summarize these chapters:';
        return `${prefix}\n${list}`;
      })()
    : undefined;

  return (
    <>
      <div className={styles.taskRow}>
        {TASKS.map((t) => (
          <button
            key={t.key}
            className={`${styles.taskBtn} ${task === t.key ? styles.taskBtnActive : ''}`}
            onClick={() => { setTask(t.key); resetChapterRange(); }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {showChapterSelect && (
        <div className={styles.chapterRange}>
          <select value={chFromIdx} onChange={(e) => { setChFromIdx(Number(e.target.value)); autoSentRef.current = false; }}>
            <option value={-1}>From chapter...</option>
            {chapters.map((ch, i) => (<option key={ch.id} value={i}>{ch.title}</option>))}
          </select>
          <span className={styles.chapterSep}>to</span>
          <select value={chToIdx} onChange={(e) => { setChToIdx(Number(e.target.value)); autoSentRef.current = false; }}>
            <option value={-1}>To chapter...</option>
            {chapters.map((ch, i) => (<option key={ch.id} value={i}>{ch.title}</option>))}
          </select>
        </div>
      )}

      <ChatInput
        task={task}
        autoPrompt={autoPrompt}
        autoSend={!!hasAutoRange}
        hasAutoSentRef={autoSentRef}
        onAutoSent={() => resetChapterRange()}
        pageStart={fromCh?.page_start ?? null}
        pageEnd={toCh?.page_end ?? toCh?.page_start ?? null}
      />
      <ConversationThread />
      <SourceList />
    </>
  );
}
