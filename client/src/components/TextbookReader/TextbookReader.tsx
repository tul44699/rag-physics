import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import type { TextbookDetail } from '../../api/types';
import { useTextbook } from '../../context/TextbookContext';
import { useProfile } from '../../context/ProfileContext';
import PDFViewer from './PDFViewer';
import PageControls from './PageControls';
import TextbookSearch from './TextbookSearch';
import styles from './TextbookReader.module.css';

export default function TextbookReader() {
  const { textbookId } = useParams<{ textbookId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const id = Number(textbookId);

  const [textbook, setTextbookDetail] = useState<TextbookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalPages, setTotalPages] = useState(0);

  const { setTextbook, setPage, setChapter, currentPage, currentChapter } = useTextbook();
  const { logEvent } = useProfile();
  const pageTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loggedPagesRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    setTextbook(id);
    setLoading(true);
    setError(null);
    fetch(`/api/textbooks/${id}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: TextbookDetail) => {
        setTextbookDetail(data);
        const pageParam = searchParams.get('page');
        const startPage = pageParam ? Number(pageParam) : 1;
        setPage(startPage);
        if (data.chapters.length > 0) setChapter(data.chapters[0].title);
      })
      .catch(() => setError('Textbook not found'))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id || loading) return;
    if (loggedPagesRef.current.has(currentPage)) return;
    pageTimerRef.current = setTimeout(() => {
      logEvent({
        event_type: 'page_read',
        textbook_id: id,
        chapter: currentChapter,
        minutes_spent: 1,
      });
      loggedPagesRef.current.add(currentPage);
    }, 30_000);
    return () => {
      if (pageTimerRef.current) clearTimeout(pageTimerRef.current);
    };
  }, [currentPage, id, currentChapter, loading, logEvent]);

  const handlePageChange = useCallback(
    (page: number) => {
      setPage(page);
      const params = new URLSearchParams(searchParams);
      params.set('page', String(page));
      setSearchParams(params, { replace: true });
    },
    [setPage, searchParams, setSearchParams],
  );

  const handleChapterChange = useCallback(
    (title: string, pageStart: number) => {
      setChapter(title);
      handlePageChange(pageStart);
    },
    [setChapter, handlePageChange],
  );

  if (loading) {
    return (
      <div className={styles.centered}>
        <div className={styles.spinner} />
        <p className={styles.statusText}>Loading textbook...</p>
      </div>
    );
  }

  if (error || !textbook) {
    return (
      <div className={styles.centered}>
        <p className={styles.statusText}>{error || 'Textbook not found'}</p>
        <Link to="/" className={styles.backLink}>Back to library</Link>
      </div>
    );
  }

  return (
    <div className={styles.reader}>
      <div className={styles.toolbar}>
        <Link to="/" className={styles.backLink}>Library</Link>
        <h2 className={styles.bookTitle}>{textbook.title}</h2>
        <TextbookSearch textbookId={id} onNavigate={handlePageChange} />
        <PageControls
          currentPage={currentPage}
          totalPages={totalPages}
          chapters={textbook.chapters}
          onPageChange={handlePageChange}
          onChapterChange={handleChapterChange}
        />
      </div>
      <div className={styles.viewer}>
        <PDFViewer
          file={`/api/textbooks/${id}/pdf`}
          page={currentPage}
          onPageLoadSuccess={(pdf) => setTotalPages(pdf.numPages || 0)}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  );
}
