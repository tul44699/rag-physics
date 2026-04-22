import { useCallback, useState } from 'react';
import type { Chapter } from '../../api/types';
import styles from './PageControls.module.css';

interface Props {
  currentPage: number;
  totalPages: number;
  chapters: Chapter[];
  onPageChange: (page: number) => void;
  onChapterChange: (title: string, pageStart: number) => void;
}

export default function PageControls({ currentPage, totalPages, chapters, onPageChange, onChapterChange }: Props) {
  const [inputVal, setInputVal] = useState(String(currentPage));

  const goTo = useCallback(() => {
    const n = Number(inputVal);
    if (n >= 1 && n <= totalPages) onPageChange(n);
    else setInputVal(String(currentPage));
  }, [inputVal, totalPages, currentPage, onPageChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') goTo();
    },
    [goTo],
  );

  return (
    <div className={styles.controls}>
      <button
        className={styles.btn}
        disabled={currentPage <= 1}
        onClick={() => onPageChange(currentPage - 1)}
      >
        Prev
      </button>
      <input
        className={styles.pageInput}
        value={inputVal}
        onChange={(e) => setInputVal(e.target.value)}
        onBlur={goTo}
        onKeyDown={handleKeyDown}
        aria-label="Page number"
      />
      <span className={styles.total}>of {totalPages || '?'}</span>
      <button
        className={styles.btn}
        disabled={currentPage >= totalPages}
        onClick={() => onPageChange(currentPage + 1)}
      >
        Next
      </button>
      {chapters.length > 0 && (
        <select
          className={styles.chapterSelect}
          onChange={(e) => {
            const idx = Number(e.target.value);
            if (chapters[idx]) onChapterChange(chapters[idx].title, chapters[idx].page_start);
          }}
        >
          {chapters.map((ch, i) => (
            <option key={ch.id} value={i}>
              {ch.title} (p.{ch.page_start})
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
