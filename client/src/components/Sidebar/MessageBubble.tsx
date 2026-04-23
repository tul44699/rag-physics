import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import type { Message, Source } from '../../api/types';
import { useTextbook } from '../../context/TextbookContext';
import { Flashcard, parseFlashcards } from '../../context/GeneratedContentContext';
import rehypeCitationLinks from './rehypeCitationLinks';
import styles from './MessageBubble.module.css';


export default function MessageBubble({ message }: { message: Message }) {
  const { currentTextbookId, setPage, setTextbook } = useTextbook();
  const navigate = useNavigate();

  const sources = message.sources ?? [];

  const handleCitation = useCallback(
    (source: Source) => {
      const page = source.page_start ?? 1;
      setPage(page);
      if (source.textbook_id != null && source.textbook_id !== currentTextbookId) {
        setTextbook(source.textbook_id);
        navigate(`/textbooks/${source.textbook_id}?page=${page}`);
      }
    },
    [currentTextbookId, setPage, setTextbook, navigate],
  );

  const handleCiteN = useCallback(
    (n: number) => {
      const source = sources[n - 1];
      if (source) handleCitation(source);
    },
    [sources, handleCitation],
  );

  const citeLink = useMemo(() => {
    return function CiteLink({ n }: { n?: string }) {
      const num = n ? parseInt(n, 10) : 0;
      return (
        <button
          className={styles.inlineCite}
          onClick={(e) => {
            e.stopPropagation();
            handleCiteN(num);
          }}
        >
          [{num}]
        </button>
      );
    };
  }, [handleCiteN]);

  const isFlashcards = message.task === 'flashcards' && message.role === 'assistant';
  const flashcardData = useMemo(
    () => (isFlashcards ? parseFlashcards(message.parsed) : null),
    [isFlashcards, message.parsed],
  );

  const renderContent = useMemo(() => {
    return flashcardData ? flashcardData.rest : message.content;
  }, [flashcardData, message.content]);

  return (
    <div className={`${styles.bubble} ${message.role === 'user' ? styles.user : styles.assistant}`}>
      {message.task && message.role === 'assistant' && (
        <div className={styles.taskBadge}>{message.task}</div>
      )}

      {flashcardData ? (
        <FlashcardDeck cards={flashcardData.cards} sources={sources} handleCiteN={handleCiteN} />
      ) : null}

      {renderContent && (
        <div className={styles.content}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex, rehypeCitationLinks]}
            components={{ 'cite-link': citeLink } as Components}
          >
            {renderContent}
          </ReactMarkdown>
        </div>
      )}

      {sources.length > 0 && (
        <div className={styles.citations}>
          {sources.map((s, i) => (
            <button
              key={i}
              className={styles.cite}
              onClick={() => handleCitation(s)}
              title={s.snippet}
            >
              [{i + 1}] {s.textbook} p.{s.page_start ?? '?'}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function FlashcardDeck({
  cards,
  sources,
  handleCiteN,
}: {
  cards: Flashcard[];
  sources: Source[];
  handleCiteN: (n: number) => void;
}) {
  const [flipped, setFlipped] = useState<Set<number>>(new Set());

  const toggle = (idx: number) => {
    setFlipped((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const CiteLink = ({ n }: { n?: string }) => {
    const num = n ? parseInt(n, 10) : 0;
    return (
      <button
        className={styles.inlineCite}
        onClick={(e) => {
          e.stopPropagation();
          handleCiteN(num);
        }}
      >
        [{num}]
      </button>
    );
  };

  return (
    <div className={styles.deck}>
      {cards.map((card, i) => (
        <div
          key={i}
          className={`${styles.card} ${flipped.has(i) ? styles.flipped : ''}`}
          onClick={() => toggle(i)}
        >
          <div className={styles.cardInner}>
            <div className={styles.cardFront}>
              <span className={styles.cardLabel}>Q{i + 1}</span>
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeCitationLinks]}
                components={{ 'cite-link': CiteLink } as Components}
              >
                {card.front}
              </ReactMarkdown>
            </div>
            <div className={styles.cardBack}>
              <span className={styles.cardLabel}>A{i + 1}</span>
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeCitationLinks]}
                components={{ 'cite-link': CiteLink } as Components}
              >
                {card.back}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
