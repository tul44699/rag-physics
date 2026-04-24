import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { renderLatex } from '../utils/katex';
import type { Textbook, FormulaSheetItem, Chapter } from '../api/types';
import styles from './FormulaSheet.module.css';

export default function FormulaSheet() {
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [loadingTextbooks, setLoadingTextbooks] = useState(true);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [chapterFromIdx, setChapterFromIdx] = useState<number>(-1);
  const [chapterToIdx, setChapterToIdx] = useState<number>(-1);
  const [sections, setSections] = useState<Record<string, Record<string, FormulaSheetItem[]>> | null>(null);
  const [chapterOrder, setChapterOrder] = useState<string[] | null>(null);
  const [sectionOrder, setSectionOrder] = useState<Record<string, string[]> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTextbooks()
      .then(setTextbooks)
      .catch((e) => setError(`Failed to load textbooks: ${e.message}`))
      .finally(() => setLoadingTextbooks(false));
  }, []);

  useEffect(() => {
    let isActive = true;

    if (selectedIds.length === 0) { 
      setChapters([]); 
      setChapterFromIdx(-1);
      setChapterToIdx(-1);
      return; 
    }

    Promise.all(selectedIds.map((id) => api.getTextbook(id)))
      .then((details) => {
        if (!isActive) return;
        const all: Chapter[] = [];
        details.forEach((d) => all.push(...(d.chapters ?? [])));
        setChapters(all);
        
        setChapterFromIdx(-1);
        setChapterToIdx(-1);
      })
      .catch(() => {
        if (!isActive) return;
        setChapters([]);
      });

    return () => { isActive = false; };
  }, [selectedIds]);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fromCh = chapterFromIdx >= 0 && chapterFromIdx < chapters.length ? chapters[chapterFromIdx] : null;
      const toCh = chapterToIdx >= 0 && chapterToIdx < chapters.length ? chapters[chapterToIdx] : null;
      
      const data = await api.generateFormulaSheet({
        textbookIds: selectedIds,
        pageStart: fromCh ? fromCh.page_start : null,
        pageEnd: toCh ? (toCh.page_end ?? toCh.page_start) : null,
      });
      
      setSections(data.sections ?? null);
      setChapterOrder(data.chapter_order ?? null);
      setSectionOrder(data.section_order ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setLoading(false);
    }
  }, [selectedIds, chapters, chapterFromIdx, chapterToIdx]);

  const orderedChapters = chapterOrder && sections
    ? chapterOrder.filter((ch) => sections[ch])
    : sections
    ? Object.keys(sections)
    : [];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/" className={styles.back}>← Library</Link>
        <h1 className={styles.title}>Formula Sheet</h1>
      </div>

      <div className={styles.controls}>
        <div className={styles.textbookList}>
          <span className={styles.label}>Textbooks</span>
          {loadingTextbooks && <p className={styles.hint}>Loading textbooks...</p>}
          {textbooks.map((tb) => (
            <label key={tb.id} className={styles.check}>
              <input
                type="checkbox"
                checked={selectedIds.includes(tb.id)}
                onChange={() =>
                  setSelectedIds((prev) =>
                    prev.includes(tb.id) ? prev.filter((x) => x !== tb.id) : [...prev, tb.id],
                  )
                }
              />
              {tb.title}
            </label>
          ))}
        </div>
        <div className={styles.label}>
          Chapter range (optional)
          <div style={{ display: 'flex', gap: '0.35rem' }}>
            <select
              className={styles.input}
              value={chapterFromIdx}
              onChange={(e) => setChapterFromIdx(Number(e.target.value))}
            >
              <option value={-1}>From...</option>
              {chapters.map((ch, i) => (
                <option key={`from-${ch.id}-${i}`} value={i}>{ch.title}</option>
              ))}
            </select>
            <select
              className={styles.input}
              value={chapterToIdx}
              onChange={(e) => setChapterToIdx(Number(e.target.value))}
            >
              <option value={-1}>To...</option>
              {chapters.map((ch, i) => (
                <option key={`to-${ch.id}-${i}`} value={i}>{ch.title}</option>
              ))}
            </select>
          </div>
        </div>
        <button className={styles.btn} onClick={generate} disabled={loading || selectedIds.length === 0}>
          {loading ? 'Generating...' : 'Generate'}
        </button>
        {error && <p className={styles.error}>{error}</p>}
      </div>

      {sections && (
        <div className={styles.result}>
          {orderedChapters.length === 0 ? (
            <p className={styles.empty}>No formulas found for the selected filters.</p>
          ) : (
            orderedChapters.map((ch) => {
              const secMap = sections?.[ch];
              if (!secMap || typeof secMap !== 'object' || Object.keys(secMap).length === 0) return null;
              const secs = sectionOrder?.[ch] ?? Object.keys(secMap);
              return (
                <div key={ch} className={styles.sectionBlock}>
                  <h2 className={styles.sectionTitle}>{ch}</h2>
                  {secs.map((sec) => {
                    const eqs = secMap[sec];
                    if (!Array.isArray(eqs) || !eqs.length) return null;
                    return (
                      <div key={sec} style={{ marginBottom: '0.35rem' }}>
                        {sec !== 'General' && (
                          <h3 style={{ fontSize: '0.82rem', margin: '0.3rem 0 0.15rem', color: '#4b5563' }}>{sec}</h3>
                        )}
                        <ul className={styles.eqList}>
                          {eqs.map((eq, i) => (
                            <FormulaItem key={i} eq={eq} />
                          ))}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

function FormulaItem({ eq }: { eq: FormulaSheetItem }) {
  const html = eq.latex ? renderLatex(eq.latex) : null;

  return (
    <li className={styles.eqItem}>
      <div className={styles.eqMain}>
        {html ? (
          <span className={styles.eqLatex} dangerouslySetInnerHTML={{ __html: html }} />
        ) : (
          <code className={styles.eqPlain}>{eq.plain_text}</code>
        )}
      </div>
      <div className={styles.eqMeta}>
        {eq.variables && eq.variables.length > 0 && (
          <span className={styles.vars}>{eq.variables.join(', ')}</span>
        )}
        {eq.page_start != null && (
          <span className={styles.pageNum}>p.{eq.page_start}</span>
        )}
      </div>
    </li>
  );
}
